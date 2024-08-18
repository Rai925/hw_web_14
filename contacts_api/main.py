from datetime import timedelta
from fastapi import Request, FastAPI, Depends, HTTPException, status, Security, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from src.schemas import EmailRequest
from src.auths.auth import create_access_token, create_refresh_token, get_email_from_refresh_token, get_current_user, \
    Hash, get_email_from_access_token
from src.database.db import get_db
from src.database.models import User
from src.routes.router import router, hash_handler
from slowapi import Limiter
from slowapi.util import get_remote_address

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

conf = ConnectionConfig(
    MAIL_USERNAME="example@meta.ua",
    MAIL_PASSWORD="secretPassword",
    MAIL_FROM="example@meta.ua",
    MAIL_PORT=465,
    MAIL_SERVER="smtp.meta.ua",
    MAIL_FROM_NAME="Example email",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

app.include_router(router)

class UserModel(BaseModel):
    """
    Schema for user signup.

    :param username: The email of the user.
    :type username: str
    :param password: The password of the user.
    :type password: str
    """
    username: str
    password: str

fm = FastMail(conf)

@app.post("/send-email")
def send_email(request: EmailRequest):
    """
    Sends an email to the specified recipient.

    :param request: The email request data.
    :type request: EmailRequest
    :return: A message indicating the result of the email sending.
    :rtype: dict
    :raises HTTPException: If there is an error in sending the email.
    """
    message = MessageSchema(
        subject="Email Verification",
        recipients=[request.recipient_email],
        body=f"Click on the link to verify your email: {request.verification_link}",
        subtype="plain"
    )
    try:
        fm.send_message(message)
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: UserModel, db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    """
    Registers a new user and sends a verification email.

    :param body: The user's signup data.
    :type body: UserModel
    :param db: The database session.
    :type db: Session
    :param background_tasks: Background tasks for handling async email sending.
    :type background_tasks: BackgroundTasks, optional
    :return: The email of the new user and a message indicating registration success.
    :rtype: dict
    :raises HTTPException: If the user already exists or there is an error in email sending.
    """
    exist_user = db.query(User).filter(User.email == body.username).first()
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")

    new_user = User(email=body.username, password=hash_handler.get_password_hash(body.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verification_token = create_access_token(data={"sub": new_user.email}, expires_delta=timedelta(hours=24))
    verification_link = f"http://localhost/verify-email?token={verification_token}"

    message = MessageSchema(
        subject="Email Verification",
        recipients=[new_user.email],
        body=f"Please verify your email: {verification_link}",
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

    return {"email": new_user.email,
            "message": "User registered successfully. Please check your email to verify your account."}

@app.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verifies the user's email address.

    :param token: The verification token.
    :type token: str
    :param db: The database session.
    :type db: Session
    :return: A message indicating the result of the email verification.
    :rtype: dict
    :raises HTTPException: If the user is not found or the email is already verified.
    """
    email = get_email_from_access_token(token)
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")

    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully"}

@app.post("/login")
def login(body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates a user and returns access and refresh tokens.

    :param body: The login data.
    :type body: OAuth2PasswordRequestForm
    :param db: The database session.
    :type db: Session
    :return: The access token, refresh token, and token type.
    :rtype: dict
    :raises HTTPException: If the email or password is invalid, or the email is not verified.
    """
    user = db.query(User).filter(User.email == body.username).first()
    if not user or not hash_handler.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not verified")

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    user.refresh_token = refresh_token
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.get('/refresh_token')
def refresh_token(credentials: HTTPAuthorizationCredentials = Security(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Generates a new access token using the refresh token.

    :param credentials: The current user's refresh token.
    :type credentials: HTTPAuthorizationCredentials
    :param db: The database session.
    :type db: Session
    :return: A new access token, refresh token, and token type.
    :rtype: dict
    :raises HTTPException: If the refresh token is invalid or does not match.
    """
    token = credentials.credentials
    email = get_email_from_refresh_token(token)
    user = db.query(User).filter(User.email == email).first()

    if user.refresh_token != token:
        user.refresh_token = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})
    user.refresh_token = refresh_token
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.get("/")
def root():
    """
    Root endpoint returning a simple greeting message.

    :return: A greeting message.
    :rtype: dict
    """
    return {"message": "Hello World"}

@app.get("/secret")
def read_item(current_user: User = Depends(get_current_user)):
    """
    Secret route accessible only to authenticated users.

    :param current_user: The currently authenticated user.
    :type current_user: User
    :return: A message and the email of the current user.
    :rtype: dict
    """
    return {"message": "Secret route", "owner": current_user.email}
