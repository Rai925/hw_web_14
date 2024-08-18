from datetime import datetime, timedelta
from typing import List, Optional
import redis
from cloudinary import uploader
from fastapi import Request, APIRouter, File, Path, HTTPException, Depends, status, BackgroundTasks, UploadFile
import jwt
from fastapi_mail import MessageSchema, FastMail
from passlib.context import CryptContext
import bcrypt
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.database.models import User
from src.database.db import get_db
from src.auths.auth import get_current_user, SECRET_KEY, create_verification_token, send_verification_email, \
    create_access_token
from src.repository.repository import (
    create_contact,
    get_contacts,
    get_contact,
    update_contact,
    delete_contact,
    search_contacts,
    get_contacts_birthday_soon
)
from src.schemas import ContactCreate, ContactUpdate, ContactResponse, UserResponse, UserModel

limiter = Limiter(key_func=get_remote_address)
from slowapi.errors import RateLimitExceeded

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
redis_client = redis.Redis(host='localhost', port=6379, db=0)


def update_avatar(request: Request, user_id: int = Path(..., description="The ID of the user"),
                  file: UploadFile = File(...),
                  db: Session = Depends(get_db)):
    """
    Uploads a user's avatar to Cloudinary and updates the user's profile with the new avatar URL.

    :param request: The HTTP request object.
    :type request: Request
    :param user_id: The ID of the user whose avatar is being updated.
    :type user_id: int
    :param file: The avatar file uploaded by the user.
    :type file: UploadFile
    :param db: The database session.
    :type db: Session
    :return: A dictionary containing the URL of the uploaded avatar.
    :rtype: dict
    :raises HTTPException: If the Cloudinary upload fails or if the user is not found.

    """
    try:
        upload_result = uploader.upload(file.file, folder='user_avatars')
        avatar_url = upload_result['secure_url']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary upload error: {str(e)}")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)

    return {"avatar_url": avatar_url}


@router.get("/verify-email/")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verifies a user's email using a JWT token.

    :param token: The JWT token containing the user's email information.
    :type token: str
    :param db: The database session.
    :type db: Session
    :return: A message indicating that the email has been successfully verified.
    :rtype: dict
    :raises HTTPException: If the token is invalid, expired, or if the user is not found.

    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.is_verified = True
        db.commit()

        return {"msg": "Email verified successfully"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")


class HashHandler:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)


hash_handler = HashHandler()


@router.post("/signup/", response_model=UserResponse)
def register_user(user: UserModel, db: Session = Depends(get_db)):
    """
    Registers a new user, hashes their password, and sends an email verification link.

    :param user: The user details to be registered.
    :type user: UserModel
    :param db: The database session.
    :type db: Session
    :return: The newly registered user.
    :rtype: User
    :raises HTTPException: If the email is already registered.

    """
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    hash_handler = HashHandler()
    hashed_password = hash_handler.get_password_hash(user.password)

    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    verification_token = create_access_token(data={"sub": db_user.email}, expires_delta=timedelta(hours=24))
    verification_link = f"http://127.0.0.1:8000/verify-email?token={verification_token}"

    message = MessageSchema(
        subject="Email Verification",
        recipients=[user.email],
        body=f"Click on the link to verify your email: {verification_link}",
        subtype="plain"
    )

    return db_user


@router.post("/reset-password/")
async def reset_password(email: str, db: Session = Depends(get_db)):
    """
    Registers a new user, hashes their password, and sends an email verification link.

    :param user: The user details to be registered.
    :type user: UserModel
    :param db: The database session.
    :type db: Session
    :return: The newly registered user.
    :rtype: User
    :raises HTTPException: If the email is already registered.

    """
    user = db.query(User).filter(User.email == email).first()
    if user:
        reset_token = create_access_token(data={"sub": email}, expires_delta=timedelta(minutes=15))
        reset_link = f"http://127.0.0.1:8000/reset-password/{reset_token}/"

        message = MessageSchema(
            subject="Password Reset",
            recipients=[email],
            body=f"Click on the link to reset your password: {reset_link}",
            subtype="plain"
        )

        return {"message": "Password reset link sent"}
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/contacts/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_new_contact(contact: ContactCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """
    Creates a new contact for the current user.

    :param contact: The details of the contact to be created.
    :type contact: ContactCreate
    :param db: The database session.
    :type db: Session
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The newly created contact.
    :rtype: ContactResponse
    :raises HTTPException: If there is an internal server error.

    """
    try:
        db_contact = create_contact(contact, db)
        return db_contact
    except HTTPException as e:
        print(f"Error in create_new_contact: {e.detail}")
        raise
    except Exception as e:
        print(f"Error in create_new_contact: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/contacts/", response_model=List[ContactResponse])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """
    Retrieves a list of contacts for the current user with pagination.

    :param skip: The number of contacts to skip (for pagination).
    :type skip: int, optional
    :param limit: The maximum number of contacts to retrieve.
    :type limit: int, optional
    :param db: The database session.
    :type db: Session
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: A list of contacts.
    :rtype: List[ContactResponse]

    """
    contacts = get_contacts(db, current_user, skip=skip, limit=limit)
    return contacts


@router.get("/contacts/search/", response_model=list[ContactResponse])
def search_contacts_route(name: Optional[str] = None, email: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Searches for contacts by name or email.

    :param name: The name of the contact to search for.
    :type name: str, optional
    :param email: The email of the contact to search for.
    :type email: str, optional
    :param db: The database session.
    :type db: Session
    :return: A list of contacts matching the search criteria.
    :rtype: list[ContactResponse]
    :raises HTTPException: If no contacts are found.

    """
    contacts = search_contacts(db, name, email)
    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")
    return contacts


@router.get("/contacts/birthday/", response_model=List[ContactResponse])
def contacts_birthday_soon(days: int = 7, db: Session = Depends(get_db)):
    """
    Retrieves contacts with birthdays within a specified number of days.

    :param days: The number of days within which to search for upcoming birthdays.
    :type days: int, optional
    :param db: The database session.
    :type db: Session
    :return: A list of contacts with upcoming birthdays.
    :rtype: List[ContactResponse]

    """
    return get_contacts_birthday_soon(db, days)


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
def read_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieves a specific contact by ID for the current user.

    :param contact_id: The ID of the contact to retrieve.
    :type contact_id: int
    :param db: The database session.
    :type db: Session
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The contact with the specified ID.
    :rtype: ContactResponse
    :raises HTTPException: If the contact is not found.

    """
    db_contact = get_contact(db, contact_id, current_user)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact


@router.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """
    Updates a contact's details for the current user.

    :param contact_id: The ID of the contact to update.
    :type contact_id: int
    :param contact: The new details of the contact.
    :type contact: ContactUpdate
    :param db: The database session.
    :type db: Session
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The updated contact.
    :rtype: ContactResponse
    :raises HTTPException: If the contact is not found.

    """
    db_contact = update_contact(db, contact_id, contact.dict(), current_user)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact


@router.delete("/contacts/{contact_id}", response_model=ContactResponse)
def delete_contact_route(contact_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """
    Deletes a contact for the current user.

    :param contact_id: The ID of the contact to delete.
    :type contact_id: int
    :param db: The database session.
    :type db: Session
    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: The deleted contact.
    :rtype: ContactResponse

    """
    return delete_contact(db, contact_id, current_user)
