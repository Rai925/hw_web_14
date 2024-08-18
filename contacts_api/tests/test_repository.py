import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from sqlalchemy.orm import Session
from src.repository.repository import create_contact, get_contacts, get_contact, update_contact, delete_contact
from src.schemas import ContactCreate
from src.database.models import Contact, User


class TestRepository(unittest.TestCase):

    def setUp(self):
        self.db = MagicMock(spec=Session)
        self.current_user = User(id=1, email="user@example.com", password="hashedpassword")

    def test_create_contact(self):
        contact_data = ContactCreate(
            first_name="John",
            last_name="Doe",
            email="johndoe@example.com",
            phone_number="1234567890"
        )

        # Тестування створення нового контакту
        contact = create_contact(contact_data, self.db)

        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(contact)
        self.assertEqual(contact.email, "johndoe@example.com")

    def test_get_contacts(self):
        # Мокаємо результат запиту
        self.db.query().filter().offset().limit().all.return_value = [Contact(email="contact1@example.com"),
                                                                      Contact(email="contact2@example.com")]

        contacts = get_contacts(self.db, self.current_user)

        self.assertEqual(len(contacts), 2)
        self.assertEqual(contacts[0].email, "contact1@example.com")
        self.assertEqual(contacts[1].email, "contact2@example.com")

    def test_get_contact(self):
        # Мокаємо результат запиту
        self.db.query().filter().first.return_value = Contact(email="contact@example.com")

        contact = get_contact(self.db, 1, self.current_user)

        self.assertIsNotNone(contact)
        self.assertEqual(contact.email, "contact@example.com")

    def test_update_contact(self):
        contact = Contact(email="old@example.com")
        self.db.query().filter().first.return_value = contact

        updated_data = {"email": "new@example.com"}
        updated_contact = update_contact(self.db, 1, updated_data, self.current_user)

        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(contact)
        self.assertEqual(updated_contact.email, "new@example.com")

    def test_delete_contact(self):
        contact = Contact(email="todelete@example.com", user_id=1)
        self.db.query().filter().first.return_value = contact

        deleted_contact = delete_contact(self.db, 1, self.current_user)

        self.db.delete.assert_called_once_with(contact)
        self.db.commit.assert_called_once()
        self.assertEqual(deleted_contact.email, "todelete@example.com")

    def test_delete_contact_not_authorized(self):
        contact = Contact(email="todelete@example.com", user_id=2)
        self.db.query().filter().first.return_value = contact

        with self.assertRaises(Exception) as context:
            delete_contact(self.db, 1, self.current_user)

        self.assertEqual(context.exception.status_code, 403)
        self.db.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
