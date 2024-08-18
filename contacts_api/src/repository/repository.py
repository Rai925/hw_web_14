from typing import Optional, List
from datetime import datetime, timedelta, date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.schemas import ContactCreate
from src.database.models import Contact, User


def create_contact(contact_data: ContactCreate, db: Session) -> Contact:
    """
    Creates a new contact entry in the database.

    :param contact_data: Data required to create a new contact.
    :type contact_data: ContactCreate
    :param db: The database session.
    :type db: Session
    :return: The newly created contact.
    :rtype: Contact
    :raises HTTPException: If a contact with the same email already exists or if there is a failure in creating the contact.

    """
    existing_contact = db.query(Contact).filter(Contact.email == contact_data.email).first()
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact with this email already exists.")

    birthday = None
    if contact_data.birthday:
        try:
            birthday = datetime.strptime(contact_data.birthday, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    new_contact = Contact(
        first_name=contact_data.first_name,
        last_name=contact_data.last_name,
        email=contact_data.email,
        phone_number=contact_data.phone_number,
        birthday=birthday,
        additional_info=contact_data.additional_info
    )

    try:
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create contact.")
    if new_contact.birthday:
        new_contact.birthday = new_contact.birthday.strftime('%Y-%m-%d')

    return new_contact


def get_contacts(db: Session, current_user: User, skip: int = 0, limit: int = 100) -> List[Contact]:
    """
    Retrieves a list of contacts for the current user.

    :param db: The database session.
    :type db: Session
    :param current_user: The user whose contacts are to be retrieved.
    :type current_user: User
    :param skip: The number of records to skip (pagination).
    :type skip: int, optional
    :param limit: The maximum number of records to return.
    :type limit: int, optional
    :return: A list of contacts for the current user.
    :rtype: List[Contact]

    """
    contacts = db.query(Contact).filter(Contact.user_id == current_user.id).offset(skip).limit(limit).all()
    return contacts


def get_contact(db: Session, contact_id: int, current_user: User) -> Optional[Contact]:
    """
    Retrieves a specific contact by ID for the current user.

    :param db: The database session.
    :type db: Session
    :param contact_id: The ID of the contact to retrieve.
    :type contact_id: int
    :param current_user: The user whose contact is to be retrieved.
    :type current_user: User
    :return: The contact if found, otherwise None.
    :rtype: Optional[Contact]

    """
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    return contact


def update_contact(db: Session, contact_id: int, contact_data: dict, current_user: User) -> Optional[Contact]:
    """
    Updates the details of an existing contact.

    :param db: The database session.
    :type db: Session
    :param contact_id: The ID of the contact to update.
    :type contact_id: int
    :param contact_data: The updated data for the contact.
    :type contact_data: dict
    :param current_user: The user whose contact is to be updated.
    :type current_user: User
    :return: The updated contact if found, otherwise None.
    :rtype: Optional[Contact]

    """
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == current_user.id).first()
    if contact:
        for key, value in contact_data.items():
            setattr(contact, key, value)
        db.commit()
        db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: int, current_user: User):
    """

    Deletes a specific contact by ID for the current user.

    :param db: The database session.
    :type db: Session
    :param contact_id: The ID of the contact to delete.
    :type contact_id: int
    :param current_user: The user whose contact is to be deleted.
    :type current_user: User
    :return: The deleted contact if found.
    :rtype: Contact
    :raises HTTPException: If the contact is not found or if the user is not authorized to delete the contact.

    """
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if db_contact.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this contact")
    db.delete(db_contact)
    db.commit()
    return db_contact


def format_date(d: date) -> str:
    """
    Formats a date object into a string in the format YYYY-MM-DD.

    :param d: The date to format.
    :type d: date
    :return: The formatted date string.
    :rtype: str

    """
    return d.strftime('%Y-%m-%d') if d else None


def search_contacts(db: Session, name: Optional[str] = None, email: Optional[str] = None) -> List[Contact]:
    """
    Searches for contacts by name or email.

    :param db: The database session.
    :type db: Session
    :param name: The name to search for (first or last).
    :type name: str, optional
    :param email: The email to search for.
    :type email: str, optional
    :return: A list of contacts that match the search criteria.
    :rtype: List[Contact]

    """
    query = db.query(Contact)
    if name:
        query = query.filter(Contact.first_name.ilike(f"%{name}%") | Contact.last_name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Contact.email.ilike(f"%{email}%"))

    contacts = query.all()
    for contact in contacts:
        contact.birthday = format_date(contact.birthday)
    return contacts


def get_contacts_birthday_soon(db: Session, days: int = 7) -> List[Contact]:
    """
    Retrieves contacts with birthdays within a specified number of days.

    :param db: The database session.
    :type db: Session
    :param days: The number of days within which to search for upcoming birthdays.
    :type days: int, optional
    :return: A list of contacts with upcoming birthdays.
    :rtype: List[Contact]

    """
    today = datetime.today().date()
    end_date = today + timedelta(days=days)
    contacts = (
        db.query(Contact)
        .filter(Contact.birthday >= today, Contact.birthday <= end_date)
        .all()
    )
    for contact in contacts:
        if contact.birthday:
            contact.birthday = contact.birthday.strftime('%Y-%m-%d')
    return contacts
