# Security Policy

## Security Features

### CSRF Protection

This application implements robust CSRF (Cross-Site Request Forgery) protection using the **Synchronizer Token Pattern**:

#### How It Works

1. **Token Generation**: When a user visits the application, a unique session ID is created and stored in a secure, HTTP-only cookie
2. **Token Binding**: A CSRF token is generated and bound to that session ID
3. **Form Inclusion**: All forms that perform state-changing operations include a hidden field with the CSRF token
4. **Validation**: When forms are submitted, the server validates that:
   - The CSRF token matches the one stored for the session
   - The session ID cookie is present and matches
   - The tokens are compared using constant-time comparison to prevent timing attacks
5. **Rejection**: If validation fails, the request is rejected with a 403 Forbidden error

#### Protected Endpoints

- `POST /feed` - Create new feed entry
- `POST /feed/{id}/delete` - Delete feed entry

Both endpoints require a valid CSRF token in the form submission.

#### Security Properties

✅ **Session-Specific**: Tokens are bound to specific user sessions
✅ **Secure Cookies**: Session cookies use `httponly` and `samesite=strict` flags
✅ **Constant-Time Comparison**: Token validation uses `secrets.compare_digest()` to prevent timing attacks
✅ **Memory Management**: Automatic cleanup prevents memory leaks from token accumulation
✅ **Clear Error Messages**: Invalid tokens result in 403 Forbidden responses

### Database Security

- **Context Managers**: All database connections use context managers to ensure proper cleanup
- **Parameterized Queries**: All SQL queries use parameterization to prevent SQL injection

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by:

1. **DO NOT** create a public GitHub issue
2. Email the maintainer at austin@austinpray.com with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

We will respond within 48 hours and work with you to address the issue.

## Security Compliance

This application follows security best practices from:

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)

## Testing

The application includes comprehensive security tests:

- CSRF token validation tests
- Session-specific token tests
- Invalid/missing token rejection tests
- All tests must pass before deployment

Run security tests with:
```bash
pytest tests/test_csrf_protection.py -v
```

## CodeQL Analysis

This project uses GitHub CodeQL for automated security scanning. All code changes are scanned for:

- Security vulnerabilities
- Code quality issues
- Common programming errors

Current Status: ✅ **No vulnerabilities detected**

## Production Recommendations

When deploying to production:

1. **Set Environment Variable**: Set `ENVIRONMENT=production` to enable secure cookies
   ```bash
   export ENVIRONMENT=production
   ```

2. **Use HTTPS**: Always use HTTPS to prevent cookie theft - the application automatically sets `secure=True` on cookies when `ENVIRONMENT=production`

3. **Consider Shared Token Storage**: For multi-process deployments:
   - The current in-memory token storage works for single-process development
   - For production with multiple workers/servers, use Redis or database for token storage
   - Example with Redis:
     ```python
     import redis
     redis_client = redis.Redis(host='localhost', port=6379, db=0)
     
     class RedisCSRFProtection:
         def generate_token(self, session_id):
             token = secrets.token_urlsafe(32)
             redis_client.setex(f"csrf:{session_id}", 3600, token)  # 1 hour expiry
             return token
         
         def validate_token(self, session_id, token):
             expected = redis_client.get(f"csrf:{session_id}")
             return expected and secrets.compare_digest(expected.decode(), token)
     ```

4. **Session Expiration**: Consider adding explicit session timeouts

5. **Rate Limiting**: Add rate limiting to prevent abuse

6. **Logging**: Monitor for suspicious CSRF validation failures

7. **Regular Updates**: Keep dependencies updated for security patches

## Version History

- **v0.1.0** (2025-12-09): Initial release with CSRF protection
