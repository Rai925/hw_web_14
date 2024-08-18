from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from starlette import status

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.database.db import get_db
from src.database.models import User


class TokenData(BaseModel):
    """
    Data model for storing information about the token.

    :param email: The email associated with the token.
    :type email: Optional[str]
    """
    email: Optional[str] = None


def get_email_from_access_token(token: str) -> Optional[str]:
    """
    Retrieves the user's email from the access token.

    :param token: The JWT access token.
    :type token: str
    :return: The user's email if it exists in the token, otherwise None.
    :rtype: Optional[str]
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        token_data = TokenData(email=email)
        return token_data.email
    except JWTError:
        return None


class Hash:
    """
    Class for handling password hashing using Passlib.

    Methods:
        verify_password(plain_password, hashed_password): Verifies if the plain and hashed passwords match.
        get_password_hash(password: str): Generates a hash for the given password.
    """
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        """
        Verifies if the plain and hashed passwords match.

        :param plain_password: The plain password to check.
        :type plain_password: str
        :param hashed_password: The hashed password to compare against.
        :type hashed_password: str
        :return: True if passwords match, otherwise False.
        :rtype: bool
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """
        Generates a hash for the given password.

        :param password: The plain password to hash.
        :type password: str
        :return: The hashed password.
        :rtype: str
        """
        return self.pwd_context.hash(password)


SECRET_KEY = "secret_key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def create_verification_token(email: str):
    """
    Creates a token for email verification.

    :param email: The email address to include in the token.
    :type email: str
    :return: The generated email verification token.
    :rtype: str
    """
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def send_verification_email(email: str, token: str):
    """
    Sends a verification email with a verification link.

    :param email: The recipient's email address.
    :type email: str
    :param token: The verification token to include in the email.
    :type token: str
    """
    sender_email = "your_email@example.com"
    receiver_email = email
    password = "your_email_password"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Email Verification"
    message["From"] = sender_email
    message["To"] = receiver_email

    verification_link = f"http://your-domain.com/verify-email/?token={token}"
    html = f"""
    <html>
    <body>
        <p>Thank you for registering! Please verify your email by clicking the link below:</p>
        <a href="{verification_link}">Verify Email</a>
    </body>
    </html>
    """

    part = MIMEText(html, "html")
    message.attach(part)

    with smtplib.SMTP_SSL("smtp.example.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates an access token with the given data and expiration time.

    :param data: The data to include in the token payload.
    :type data: dict
    :param expires_delta: The expiration time for the token. If None, the default expiration is 1 hour.
    :type expires_delta: Optional[timedelta]
    :return: The generated access token.
    :rtype: str
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[float] = None):
    """
    Creates a refresh token with the given data and expiration time.

    :param data: The data to include in the token payload.
    :type data: dict
    :param expires_delta: The expiration time for the token in seconds. If None, the default expiration is 7 days.
    :type expires_delta: Optional[float]
    :return: The generated refresh token.
    :rtype: str
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + timedelta(seconds=expires_delta)
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": "refresh_token"})
    encoded_refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_refresh_token


def get_email_from_refresh_token(refresh_token: str):
    """
    Retrieves the email from the refresh token.

    :param refresh_token: The JWT refresh token.
    :type refresh_token: str
    :return: The email if the token has a valid scope, otherwise raises an HTTPException.
    :rtype: str
    :raises HTTPException: If the token has an invalid scope or cannot be validated.
    """
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload['scope'] == 'refresh_token':
            email = payload['sub']
            return email
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid scope for token')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Retrieves the current user from the access token.

    :param token: The JWT access token.
    :type token: str
    :param db: The database session.
    :type db: Session
    :return: The user if the token is valid and the user exists in the database.
    :rtype: User
    :raises HTTPException: If the credentials are invalid or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload['scope'] == 'access_token':
            email = payload["sub"]
            if email is None:
                raise credentials_exception
        else:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception

    user: User = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
