import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your_secret_key"

def create_verification_token(email: str):
    """
    This function generates a JWT (JSON Web Token) for email verification.
    The token is valid for 24 hours and contains the email address as a subject.

    Parameters:
    email (str): The email address for which the verification token is being created.

    Returns:
    str: The generated JWT verification token.
    """
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=24)  # Термін дії токена 24 години
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token
