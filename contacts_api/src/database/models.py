from sqlalchemy import Column, Integer, String, ForeignKey, Date, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy import Boolean

Base = declarative_base()


class Contact(Base):
    """
    Represents a contact entry in the database.

    Attributes:
        id (int): The primary key for the contact.
        first_name (str): The first name of the contact.
        last_name (str): The last name of the contact.
        email (str): The email address of the contact, must be unique.
        phone_number (str): The phone number of the contact.
        birthday (date, optional): The birthday of the contact.
        additional_info (str, optional): Any additional information about the contact.
        user_id (int): Foreign key referencing the User associated with this contact.
        user (User): Relationship to the User model, linking contacts to a specific user.
    """
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String)
    birthday = Column(Date, nullable=True)
    additional_info = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="contacts")


class User(Base):
    """
    Represents a user in the database.

    Attributes:
        id (int): The primary key for the user.
        email (str): The user's email address, must be unique and not nullable.
        is_verified (bool): Indicates if the user's email is verified, defaults to False.
        username (str): The username of the user.
        password (str): The hashed password for the user, must not be nullable.
        created_at (datetime): The timestamp when the user was created, defaults to current time.
        avatar_url (str, optional): URL to the user's avatar image.
        refresh_token (str, optional): The refresh token associated with the user.
        contacts (list[Contact]): Relationship to the Contact model, linking users to their contacts.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    username = Column(String(50))
    password = Column(String(255), nullable=False)
    created_at = Column('created_at', DateTime, default=func.now())
    avatar_url = Column(String, nullable=True)
    refresh_token = Column(String(255), nullable=True)
    contacts = relationship("Contact", back_populates="user")
