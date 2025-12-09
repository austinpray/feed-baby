"""User model for authentication."""

import sqlite3
import hashlib
import secrets
from typing import Self


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a salt.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
    
    Returns:
        Tuple of (password_hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    # Use 600,000 iterations as recommended by OWASP 2023 guidelines
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000)
    return hashed.hex(), salt


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash.
    
    Args:
        password: Plain text password to verify
        stored_hash: Stored hash in format 'salt:hash'
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        salt, expected_hash = stored_hash.split(':')
        actual_hash, _ = hash_password(password, salt)
        return secrets.compare_digest(actual_hash, expected_hash)
    except ValueError:
        return False


class User:
    """Represents a user account."""
    
    id: int | None
    username: str
    password_hash: str
    
    def __init__(self, username: str, password_hash: str, id: int | None = None):
        """Initialize User.
        
        Args:
            username: User's username
            password_hash: Hashed password (salt:hash format)
            id: Database ID (optional, None if not yet saved)
        """
        self.id = id
        self.username = username
        self.password_hash = password_hash
    
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
        
        hashed, salt = hash_password(password)
        password_hash = f"{salt}:{hashed}"
        
        conn = get_connection(db_path)
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
                user_id = cursor.lastrowid
                return cls(username=username, password_hash=password_hash, id=user_id)
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
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            
            user = cls.from_db(row)
            if verify_password(password, user.password_hash):
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
                "SELECT id, username, password_hash FROM users WHERE id = ?",
                (user_id,)
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
        return cls(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash']
        )
