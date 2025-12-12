"""Unit tests for authentication module."""

from feed_baby.auth import create_session, get_session, delete_session
from feed_baby.user import User


def test_create_session(e2e_db_path: str) -> None:
    """Test session creation returns valid UUID and stores in database."""
    # Create a user first
    user = User.create(username="testuser", password="testpass", db_path=e2e_db_path)
    assert user is not None
    assert user.id is not None
    
    session_id = create_session(user.id, e2e_db_path)

    assert isinstance(session_id, str)
    assert len(session_id) > 0
    # UUID4 should contain hyphens
    assert "-" in session_id
    # Session should be retrievable
    assert get_session(session_id, e2e_db_path) == user.id


def test_get_session(e2e_db_path: str) -> None:
    """Test retrieving user_id from session."""
    # Create a user first
    user = User.create(username="getuser", password="testpass", db_path=e2e_db_path)
    assert user is not None
    assert user.id is not None
    
    session_id = create_session(user.id, e2e_db_path)

    retrieved_user_id = get_session(session_id, e2e_db_path)

    assert retrieved_user_id == user.id


def test_get_invalid_session(e2e_db_path: str) -> None:
    """Test retrieving non-existent session returns None."""
    retrieved_user_id = get_session("nonexistent-session-id", e2e_db_path)

    assert retrieved_user_id is None


def test_delete_session(e2e_db_path: str) -> None:
    """Test deleting session removes it."""
    # Create a user first
    user = User.create(username="deluser", password="testpass", db_path=e2e_db_path)
    assert user is not None
    assert user.id is not None
    
    session_id = create_session(user.id, e2e_db_path)

    # Verify session exists
    assert get_session(session_id, e2e_db_path) == user.id

    # Delete session
    delete_session(session_id, e2e_db_path)

    # Verify session is gone
    assert get_session(session_id, e2e_db_path) is None


def test_delete_nonexistent_session(e2e_db_path: str) -> None:
    """Test deleting non-existent session doesn't raise error."""
    # This should not raise an exception
    delete_session("nonexistent-session-id", e2e_db_path)


def test_multiple_sessions(e2e_db_path: str) -> None:
    """Test multiple sessions can coexist."""
    # Create multiple users
    user1 = User.create(username="user1", password="pass1", db_path=e2e_db_path)
    user2 = User.create(username="user2", password="pass2", db_path=e2e_db_path)
    user3 = User.create(username="user3", password="pass3", db_path=e2e_db_path)
    
    assert user1 is not None and user1.id is not None
    assert user2 is not None and user2.id is not None
    assert user3 is not None and user3.id is not None

    session1 = create_session(user1.id, e2e_db_path)
    session2 = create_session(user2.id, e2e_db_path)
    session3 = create_session(user3.id, e2e_db_path)

    assert get_session(session1, e2e_db_path) == user1.id
    assert get_session(session2, e2e_db_path) == user2.id
    assert get_session(session3, e2e_db_path) == user3.id

    # Sessions should be unique
    assert session1 != session2
    assert session2 != session3
    assert session1 != session3


def test_create_session_success(e2e_db_path: str) -> None:
    """Test session creation works with valid user_id."""
    # Create a user first
    user = User.create(username="succuser", password="testpass", db_path=e2e_db_path)
    assert user is not None
    assert user.id is not None
    
    session_id = create_session(user.id, e2e_db_path)
    assert get_session(session_id, e2e_db_path) == user.id
