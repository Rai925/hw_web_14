from src.auths.auth import create_access_token, create_refresh_token, Hash

hash_instance = Hash()


def test_create_access_token():
    token = create_access_token(data={"sub": "user@example.com"})
    assert token is not None
    assert isinstance(token, str)


def test_verify_password():
    hashed_password = hash_instance.get_password_hash("mypassword")
    assert hash_instance.verify_password("mypassword", hashed_password)
    assert not hash_instance.verify_password("wrongpassword", hashed_password)
