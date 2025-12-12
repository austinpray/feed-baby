# feed-baby

Workflow:

1. Configure your feeding goals and constraints
1. Log a feed
2. Based on latest logged feed a feeding calendar is generated

Nice to have analysis features:
- Heatmap of feeding times

## Environment Variables

The application can be configured using the following environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URL` | Path to the SQLite database file | `main.db` | `DATABASE_URL=/data/feeds.db` |
| `SECURE_COOKIES` | Enable secure flag on session cookies (HTTPS-only). Set to `true`, `1`, or `yes` to enable. Required for production. | `false` | `SECURE_COOKIES=true` |
| `E2E_DB_PATH` | Path to the database file for end-to-end tests (testing only) | `e2e.db` | `E2E_DB_PATH=/tmp/test.db` |

### Production Deployment

For production deployments, you should set:
```bash
SECURE_COOKIES=true
```

This ensures session cookies are only transmitted over HTTPS connections, protecting against man-in-the-middle attacks.

## Configuration

```toml
daily_goal_ounces = 24

max_interval_hours = 3

sleep_hours = 5
```