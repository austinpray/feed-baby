"""Unit tests for User model."""

from feed_baby.user import User, hash_password, verify_password


def test_hash_password():
    """Test password hashing generates hash and salt."""
    password = "testpassword123"
    hashed, salt = hash_password(password)

    assert isinstance(hashed, str)
    assert isinstance(salt, str)
    assert len(hashed) == 64  # SHA256 produces 32 bytes = 64 hex chars
    assert len(salt) == 64  # 32 bytes = 64 hex chars


def test_hash_password_with_salt():
    """Test password hashing with provided salt."""
    password = "testpassword123"
    salt = "fixedsalt"
    hashed1, salt1 = hash_password(password, salt)
    hashed2, salt2 = hash_password(password, salt)

    assert hashed1 == hashed2  # Same password and salt should produce same hash
    assert salt1 == salt2 == salt


def test_hash_password_unique_salts():
    """Test that different salts produce different hashes."""
    password = "testpassword123"
    hashed1, salt1 = hash_password(password)
    hashed2, salt2 = hash_password(password)

    assert salt1 != salt2  # Different salts
    assert hashed1 != hashed2  # Different hashes


def test_verify_password_success():
    """Test password verification with correct password."""
    password = "testpassword123"
    hashed, salt = hash_password(password)
    stored_hash = f"pbkdf2:sha256:600000${salt}${hashed}"

    assert verify_password(password, stored_hash) is True


def test_verify_password_failure():
    """Test password verification with incorrect password."""
    password = "testpassword123"
    wrong_password = "wrongpassword"
    hashed, salt = hash_password(password)
    stored_hash = f"pbkdf2:sha256:600000${salt}${hashed}"

    assert verify_password(wrong_password, stored_hash) is False


def test_verify_password_invalid_format():
    """Test password verification with invalid hash format."""
    password = "testpassword123"
    invalid_hash = "invalid:format:hash"

    assert verify_password(password, invalid_hash) is False


def test_user_create_success(tmp_path):
    """Test creating a new user."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    user = User.create(username="newuser", password="password123", db_path=db_path)

    assert user is not None
    assert user.id is not None
    assert user.username == "newuser"
    assert user.password_hash.startswith("pbkdf2:sha256:600000$")


def test_user_create_duplicate_username(tmp_path):
    """Test creating user with existing username returns None."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create first user
    user1 = User.create(username="duplicateuser", password="password1", db_path=db_path)
    assert user1 is not None

    # Try to create user with same username
    user2 = User.create(username="duplicateuser", password="password2", db_path=db_path)
    assert user2 is None


def test_user_authenticate_success(tmp_path):
    """Test authentication with valid credentials."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create user
    User.create(username="authuser", password="authpass", db_path=db_path)

    # Authenticate
    user = User.authenticate(username="authuser", password="authpass", db_path=db_path)

    assert user is not None
    assert user.username == "authuser"


def test_user_authenticate_invalid_password(tmp_path):
    """Test authentication fails with wrong password."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create user
    User.create(username="authuser", password="correctpass", db_path=db_path)

    # Try to authenticate with wrong password
    user = User.authenticate(username="authuser", password="wrongpass", db_path=db_path)

    assert user is None


def test_user_authenticate_nonexistent_user(tmp_path):
    """Test authentication fails for non-existent user."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    user = User.authenticate(
        username="nonexistent", password="password", db_path=db_path
    )

    assert user is None


def test_user_get_by_id(tmp_path):
    """Test retrieving user by ID."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create user
    created_user = User.create(username="iduser", password="password", db_path=db_path)
    assert created_user is not None
    assert created_user.id is not None

    # Retrieve by ID
    retrieved_user = User.get_by_id(created_user.id, db_path=db_path)

    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.username == "iduser"


def test_user_get_by_id_not_found(tmp_path):
    """Test retrieving non-existent user returns None."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    user = User.get_by_id(9999, db_path=db_path)

    assert user is None


def test_user_check_password(tmp_path):
    """Test User.check_password method."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    user = User.create(username="checkuser", password="mypassword", db_path=db_path)
    assert user is not None

    assert user.check_password("mypassword") is True
    assert user.check_password("wrongpassword") is False


def test_user_set_password(tmp_path):
    """Test User.set_password method."""
    from migrate import migrate

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    user = User.create(username="setuser", password="oldpassword", db_path=db_path)
    assert user is not None

    old_hash = user.password_hash
    user.set_password("newpassword")

    assert user.password_hash != old_hash
    assert user.check_password("newpassword") is True
    assert user.check_password("oldpassword") is False
