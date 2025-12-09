# feed-baby

A baby feeding tracker application with built-in CSRF protection.

## Features

- Track baby feeding times and volumes
- Simple web interface
- **CSRF Protection** on all state-changing operations (create, delete)
- SQLite database backend
- Automatic database migrations

## Security

### CSRF Protection

This application implements CSRF (Cross-Site Request Forgery) protection using the Synchronizer Token Pattern:

- **Token Generation**: A unique CSRF token is generated for each user session
- **Token Validation**: All POST requests (create feed, delete feed) require a valid CSRF token
- **Session Binding**: CSRF tokens are bound to session IDs stored in secure, HTTP-only cookies
- **Protection Against**: Malicious websites cannot submit forms on behalf of users

#### How It Works

1. When a user visits the application, a session ID is created and stored in a secure cookie
2. A CSRF token is generated and tied to that session
3. All forms include a hidden field with the CSRF token
4. When forms are submitted, the server validates:
   - The CSRF token matches the one stored for the session
   - The session ID cookie is present and matches
5. If validation fails, the request is rejected with a 403 Forbidden error

#### Protected Endpoints

- `POST /feed` - Create new feed entry (requires CSRF token)
- `POST /feed/{id}/delete` - Delete feed entry (requires CSRF token)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Usage

```bash
# Run the server
uvicorn server:app --reload

# Access the application
open http://localhost:8000
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=feed_baby --cov-report=html
```

### CSRF Protection Tests

The test suite includes comprehensive tests for CSRF protection:
- Valid token acceptance
- Invalid token rejection
- Missing token rejection
- Session-specific token validation
- Cross-session token rejection

## Development

The application uses:
- **FastAPI**: Modern web framework
- **Jinja2**: Template engine
- **Pendulum**: DateTime handling
- **SQLite**: Database
- **pytest**: Testing framework

## License

MIT License - see LICENSE file for details
