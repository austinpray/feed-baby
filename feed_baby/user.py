"""User model for authentication."""

import hashlib
import secrets
import sqlite3
from typing import Self

import pendulum


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password using PBKDF2-SHA256.

    Args:
        password: Plain text password to hash
        salt: Optional salt (generates new one if not provided)

    Returns:
        Tuple of (password_hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(32)  # 32 bytes = 64 hex characters

    # Use 600,000 iterations as recommended by OWASP 2023 guidelines
    # Reference: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000)
    return hashed.hex(), salt


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash.

    Args:
        password: Plain text password to verify
        stored_hash: Stored hash in format 'pbkdf2:sha256:600000$salt$hash'

    Returns:
        True if password matches, False otherwise
    """
    try:
        # Parse the stored hash format: pbkdf2:sha256:600000$salt$hash
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False

        algorithm_info, salt, expected_hash = parts
        if algorithm_info != "pbkdf2:sha256:600000":
            return False

        actual_hash, _ = hash_password(password, salt)

        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(actual_hash, expected_hash)
    except (ValueError, AttributeError):
        return False


class User:
    """Represents a user account."""

    id: int | None
    username: str
    password_hash: str
    created_at: pendulum.DateTime

    def __init__(
        self,
        username: str,
        password_hash: str,
        created_at: pendulum.DateTime,
        id: int | None = None,
    ):
        """Initialize User.

        Args:
            username: User's username
            password_hash: Hashed password in format 'pbkdf2:sha256:600000$salt$hash'
            created_at: When the user was created
            id: Database ID (optional, None if not yet saved)
        """
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at

    def set_password(self, password: str) -> None:
        """Hash and store a password.

        Args:
            password: Plain text password to hash
        """
        hashed, salt = hash_password(password)
        self.password_hash = f"pbkdf2:sha256:600000${salt}${hashed}"

    def check_password(self, password: str) -> bool:
        """Verify a password against this user's stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        return verify_password(password, self.password_hash)

    @classmethod
    def create(cls, username: str, password: str, db_path: str) -> Self | None:
        """Create a new user with the given username and password.

        Args:
            username: Username (must be unique)
            password: Plain text password
            db_path: Path to SQLite database

        Returns:
            User instance if created, None if username already exists
        """
        from feed_baby.db import get_connection

        # Hash the password
        hashed, salt = hash_password(password)
        password_hash = f"pbkdf2:sha256:600000${salt}${hashed}"

        conn = get_connection(db_path)
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
                user_id = cursor.lastrowid

                # Fetch the created_at timestamp from the database
                cursor = conn.execute(
                    "SELECT created_at FROM users WHERE id = ?", (user_id,)
                )
                row = cursor.fetchone()
                created_at_str = row["created_at"]

                # Parse the timestamp using pendulum
                created_at_parsed = pendulum.parse(created_at_str)
                if not isinstance(created_at_parsed, pendulum.DateTime):
                    raise ValueError(
                        f"Expected DateTime, got {type(created_at_parsed)}"
                    )

                return cls(
                    username=username,
                    password_hash=password_hash,
                    created_at=created_at_parsed,
                    id=user_id,
                )
        except sqlite3.IntegrityError:
            # Username already exists
            return None
        finally:
            conn.close()

    @classmethod
    def authenticate(cls, username: str, password: str, db_path: str) -> Self | None:
        """Authenticate a user with username and password.

        Args:
            username: Username to authenticate
            password: Plain text password
            db_path: Path to SQLite database

        Returns:
            User instance if authenticated, None otherwise
        """
        from feed_baby.db import get_connection

        conn = get_connection(db_path)
        try:
            cursor = conn.execute(
                "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            user = cls.from_db(row)
            if user.check_password(password):
                return user
            return None
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, user_id: int, db_path: str) -> Self | None:
        """Get a user by ID.

        Args:
            user_id: User ID to look up
            db_path: Path to SQLite database

        Returns:
            User instance if found, None otherwise
        """
        from feed_baby.db import get_connection

        conn = get_connection(db_path)
        try:
            cursor = conn.execute(
                "SELECT id, username, password_hash, created_at FROM users WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return cls.from_db(row)
        finally:
            conn.close()

    @classmethod
    def from_db(cls, row: sqlite3.Row) -> Self:
        """Create User from database row.

        Args:
            row: Database row with named column access

        Returns:
            User instance
        """
        created_at_parsed = pendulum.parse(row["created_at"])
        if not isinstance(created_at_parsed, pendulum.DateTime):
            raise ValueError(f"Expected DateTime, got {type(created_at_parsed)}")

        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            created_at=created_at_parsed,
        )
