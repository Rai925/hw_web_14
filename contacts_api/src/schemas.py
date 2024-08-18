from dataclasses import Field
from datetime import datetime
from typing import Optional

from fastapi_mail import ConnectionConfig
from pydantic import BaseModel, EmailStr, constr, HttpUrl
from dotenv import load_dotenv
import os

load_dotenv()


class ContactCreate(BaseModel):
    """
    Schema for creating a new contact.

    :param first_name: The first name of the contact.
    :type first_name: str
    :param last_name: The last name of the contact.
    :type last_name: str
    :param email: The email address of the contact.
    :type email: EmailStr
    :param phone_number: The phone number of the contact.
    :type phone_number: str
    :param birthday: The birthday of the contact (optional).
    :type birthday: str, optional
    :param additional_info: Any additional information about the contact (optional).
    :type additional_info: str, optional
    """
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: Optional[str] = None
    additional_info: Optional[str] = None


class ContactUpdate(ContactCreate):
    """
    Schema for updating an existing contact.

    Inherits all fields from ContactCreate.
    """
    pass


class ContactResponse(BaseModel):
    """
    Schema for the response after creating or retrieving a contact.

    :param first_name: The first name of the contact.
    :type first_name: str
    :param last_name: The last name of the contact.
    :type last_name: str
    :param email: The email address of the contact.
    :type email: EmailStr
    :param phone_number: The phone number of the contact (optional).
    :type phone_number: str, optional
    :param birthday: The birthday of the contact (optional).
    :type birthday: str, optional
    :param additional_info: Any additional information about the contact (optional).
    :type additional_info: str, optional
    """
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    birthday: Optional[str] = None
    additional_info: Optional[str] = None


class UserModel(BaseModel):
    """
    Schema for creating a new user.

    :param username: The username of the user.
    :type username: str
    :param email: The email address of the user.
    :type email: EmailStr
    :param password: The password of the user.
    :type password: str
    """
    username: constr(min_length=5, max_length=16)
    email: EmailStr
    password: constr(min_length=6, max_length=16)


class UserUpdate(BaseModel):
    """
    Schema for updating an existing user's avatar.

    :param avatar_url: The URL of the user's new avatar.
    :type avatar_url: HttpUrl
    """
    avatar_url: HttpUrl


class UserDb(BaseModel):
    """
    Schema representing a user in the database.

    :param id: The unique identifier of the user.
    :type id: int
    :param username: The username of the user.
    :type username: str
    :param email: The email address of the user.
    :type email: str
    :param created_at: The datetime when the user was created.
    :type created_at: datetime
    :param avatar: The URL of the user's avatar (optional).
    :type avatar: str, optional
    """
    id: int
    username: str
    email: str
    created_at: datetime
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """
    Schema for the response after creating a user.

    :param id: The unique identifier of the user.
    :type id: int
    :param username: The username of the user.
    :type username: str
    :param email: The email address of the user.
    :type email: str
    :param detail: The detail message indicating user creation success.
    :type detail: str
    """
    id: int
    username: str
    email: str
    detail: str = "User successfully created"


class EmailRequest(BaseModel):
    """
    Schema for sending an email request.

    :param recipient_email: The email address of the recipient.
    :type recipient_email: EmailStr
    :param verification_link: The verification link to be sent in the email.
    :type verification_link: str
    """
    recipient_email: EmailStr
    verification_link: str


class TokenModel(BaseModel):
    """
    Schema for the JWT tokens.

    :param access_token: The JWT access token.
    :type access_token: str
    :param refresh_token: The JWT refresh token.
    :type refresh_token: str
    :param token_type: The type of the token, default is 'bearer'.
    :type token_type: str
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class EmailSettings(BaseModel):
    """
    Schema for the email configuration settings.

    :param MAIL_USERNAME: The email username.
    :type MAIL_USERNAME: str
    :param MAIL_PASSWORD: The email password.
    :type MAIL_PASSWORD: str
    :param MAIL_FROM: The email address from which emails are sent.
    :type MAIL_FROM: EmailStr
    :param MAIL_PORT: The port used by the email server.
    :type MAIL_PORT: int
    :param MAIL_SERVER: The email server.
    :type MAIL_SERVER: str
    :param MAIL_TLS: Whether to use TLS (True by default).
    :type MAIL_TLS: bool
    :param MAIL_SSL: Whether to use SSL (False by default).
    :type MAIL_SSL: bool
    :param MAIL_FROM_NAME: The name shown as the sender in the email.
    :type MAIL_FROM_NAME: str
    """
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    MAIL_FROM_NAME: str = "Your App Name"


conf = ConnectionConfig(
    MAIL_USERNAME="your_email@example.com",
    MAIL_PASSWORD="your_password",
    MAIL_FROM="your_email@example.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.example.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_FROM_NAME="Your App Name"
)
