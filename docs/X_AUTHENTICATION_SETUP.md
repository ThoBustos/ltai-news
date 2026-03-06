# X/Twitter Authentication Setup Guide

This guide explains how to configure OAuth 2.0 PKCE authentication for posting threads to X (formerly Twitter).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Developer Portal Configuration](#developer-portal-configuration)
3. [Token Generation](#token-generation)
4. [Environment Variables](#environment-variables)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)
7. [Token Refresh](#token-refresh)
8. [Security](#security)

---

## Prerequisites

Before setting up X authentication, you need:

1. **X/Twitter Account** - The account you want to post from
2. **X Developer Account** - Applied for and approved at [developer.twitter.com](https://developer.twitter.com)
3. **X Developer App** - Created in the Developer Portal

If you don't have a developer account yet:
- Go to [developer.twitter.com](https://developer.twitter.com)
- Sign in with your X account
- Apply for Elevated access (required for posting)
- Create a new project and app

---

## Local Development Setup

### HTTP Localhost Callback

The token generation process uses a **local HTTP callback URL** for development:
```
http://127.0.0.1:8080/callback
```

**Why HTTP (not HTTPS) is safe for localhost:**

1. **No network traffic** - 127.0.0.1 is localhost, packets never leave your machine
2. **OAuth 2.0 standard** - The OAuth 2.0 specification explicitly allows HTTP for localhost
3. **Standard practice** - All OAuth 2.0 development uses HTTP localhost callbacks
4. **X Platform support** - X Developer Portal accepts HTTP localhost callback URLs

**Technical detail:** The token generation script sets `OAUTHLIB_INSECURE_TRANSPORT=1` environment variable to allow HTTP for localhost. This is the recommended approach in OAuth 2.0 documentation and only affects localhost/127.0.0.1 addresses.

**Production note:** In production, always use HTTPS callback URLs with your actual domain.

---

## Developer Portal Configuration

### Step 1: Navigate to Your App

1. Go to [X Developer Portal](https://developer.twitter.com/en/portal/projects-and-apps)
2. Select your project
3. Click on your app name

### Step 2: Configure User Authentication Settings

1. Click **"Settings"** in the left sidebar
2. Scroll to **"User authentication settings"**
3. Click **"Set up"** (or "Edit" if already configured)

**Configure these settings:**

| Setting | Value |
|---------|-------|
| **App permissions** | ✅ **Read and write** (NOT just "Read"!) |
| **Type of App** | ✅ **Web App** |
| **Callback URI / Redirect URL** | `http://127.0.0.1:8080/callback` |
| **Website URL** | Any valid URL (e.g., `https://example.com`) |

**Critical:** Make sure "Read and write" is selected. "Read only" will cause 403 errors when posting!

4. Click **"Save"**

### Step 3: Get OAuth 2.0 Credentials

1. Click **"Keys and tokens"** tab
2. Under **"OAuth 2.0 Client ID and Client Secret"**:
   - Copy the **Client ID** (save it somewhere safe)
   - Click **"Regenerate"** if you need a new Client Secret
   - Copy the **Client Secret** immediately (it won't be shown again!)

**Important:** Client Secret is only shown once. If you lose it, regenerate a new one.

---

## Token Generation

OAuth 2.0 PKCE requires generating access and refresh tokens through an authorization flow.

### Automatic Token Generation (Recommended)

Use the provided script to generate tokens automatically:

```bash
cd /Users/thomas/Documents/projects/ltai-news
source .venv/bin/activate
python scripts/generate_twitter_oauth2_tokens_auto.py
```

**What happens:**

1. Script opens your browser to X authorization page
2. You click **"Authorize app"**
3. Browser redirects to: `http://127.0.0.1:8080/callback?code=...&state=...`
4. **Copy the entire URL** from your browser address bar
5. Paste it into the terminal prompt
6. Script exchanges the code for tokens and displays them

**Example output:**

```
Generated tokens:
Access Token: bG9uZ19hY2Nlc3NfdG9rZW5faGVyZV...
Refresh Token: cmVmcmVzaF90b2tlbl9oZXJlX2xvbmdfc3RyaW5n...

Add these to your .env file:
TWITTER_OAUTH2_ACCESS_TOKEN=bG9uZ19hY2Nlc3NfdG9rZW5faGVyZV...
TWITTER_OAUTH2_REFRESH_TOKEN=cmVmcmVzaF90b2tlbl9oZXJlX2xvbmdfc3RyaW5n...
```

**Token characteristics:**

- **Access Token**: ~200 characters, expires in 2 hours
- **Refresh Token**: ~200 characters, long-lived (used to get new access tokens)

### Manual Token Generation (Alternative)

If the automatic script doesn't work, use the manual script:

```bash
python scripts/generate_twitter_oauth2_tokens.py
```

This provides step-by-step instructions but requires more manual intervention.

---

## Environment Variables

### Update Your `.env` File

Add the OAuth 2.0 credentials to your `.env` file:

```env
# X/Twitter OAuth 2.0 Configuration
TWITTER_OAUTH2_CLIENT_ID=<client_id_from_developer_portal>
TWITTER_OAUTH2_CLIENT_SECRET=<client_secret_from_developer_portal>
TWITTER_OAUTH2_ACCESS_TOKEN=<long_token_from_script>
TWITTER_OAUTH2_REFRESH_TOKEN=<long_token_from_script>

# Auto-posting (keep false until testing succeeds)
AUTO_POST_TO_X=false
```

**Remove these lines** (OAuth 1.0a is no longer supported):

```env
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
TWITTER_BEARER_TOKEN=...
TWITTER_USE_OAUTH2=...
```

### Configuration Validation

The application requires all 4 OAuth 2.0 fields to be set:

- `TWITTER_OAUTH2_CLIENT_ID` - From Developer Portal
- `TWITTER_OAUTH2_CLIENT_SECRET` - From Developer Portal
- `TWITTER_OAUTH2_ACCESS_TOKEN` - From token generation script
- `TWITTER_OAUTH2_REFRESH_TOKEN` - From token generation script

Missing any field will cause an authentication error on startup.

---

## Testing

### Test 1: Start the Server

```bash
cd /Users/thomas/Documents/projects/ltai-news
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

**Expected output:**

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Test 2: Post a Thread (Manual)

Post a thread for a specific date:

```bash
curl -X POST "http://localhost:8000/api/x-thread/post-to-x/2025-01-24"
```

**Success response (200 OK):**

```json
{
  "success": true,
  "target_date": "2025-01-24",
  "tweet_count": 11,
  "tweet_ids": ["1234567890123456789", "9876543210987654321", ...],
  "thread_url": "https://x.com/i/status/1234567890123456789",
  "message": "Thread posted successfully"
}
```

**Error response (401/403):**

```json
{
  "success": false,
  "target_date": "2025-01-24",
  "errors": ["Twitter authentication failed"],
  "message": "Failed to post thread to X"
}
```

### Test 3: Verify on X

1. Open the `thread_url` from the response
2. Check that all tweets are posted
3. Verify threading (each tweet replies to the previous one)
4. Confirm content matches expected format

---

## Troubleshooting

### Error: 403 Forbidden

**Symptom:**

```
Twitter API error: 403 Forbidden
Your client app is not configured with the appropriate oauth1 app permissions
```

**Cause:** App permissions are set to "Read only" instead of "Read and write"

**Fix:**

1. Go to Developer Portal → Your App → Settings
2. Click "User authentication settings" → Edit
3. Change **App permissions** to **"Read and write"**
4. Save and regenerate tokens

### Error: 401 Unauthorized

**Symptom:**

```
Twitter authentication failed: 401 Unauthorized
```

**Possible causes:**

1. **Invalid tokens** - Tokens may have been revoked or are malformed
2. **Expired access token** - Access token expires after 2 hours (should auto-refresh)
3. **Wrong credentials** - Client ID/Secret don't match the app

**Fix:**

1. Regenerate tokens using the script
2. Verify Client ID and Secret match your app
3. Check that all 4 env vars are set correctly

### Error: Token Expired

**Symptom:**

```
Token expired or invalid
```

**Cause:** Access token expired and refresh failed

**Fix:**

1. Check that `TWITTER_OAUTH2_REFRESH_TOKEN` is set
2. Verify Client Secret is correct
3. Regenerate tokens if refresh token is invalid

### Error: insecure_transport (HTTPS Required)

**Symptom:**

```
❌ Error fetching token: (insecure_transport) OAuth 2 MUST utilize https.
```

**Cause:** The OAuth library requires HTTPS by default, but the script is configured to allow HTTP for localhost development.

**Fix:**

This error should not occur with the latest version of `generate_twitter_oauth2_tokens_auto.py`. If you see it:

1. Verify you're using the latest script version (check for `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` near line 23)
2. Ensure the callback URI in Developer Portal is exactly: `http://127.0.0.1:8080/callback` (not https, not localhost)
3. If using a custom script, add this before calling `fetch_token()`:
   ```python
   os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
   ```

**Alternative:** Use ngrok to create an HTTPS tunnel (not recommended for local development):
```bash
brew install ngrok
ngrok http 8080
# Update callback URI to ngrok HTTPS URL
```

### Error: No Digest Found

**Symptom:**

```json
{
  "success": false,
  "errors": ["No digest found for 2025-01-24"]
}
```

**Cause:** No digest was generated for that date

**Fix:**

1. Run the daily pipeline first:
   ```bash
   curl -X POST "http://localhost:8000/api/orchestrator/run-daily-pipeline/2025-01-24"
   ```
2. Wait for pipeline to complete
3. Retry posting thread

### Error: Thread Partially Posted

**Symptom:** Some tweets posted, then error occurred

**Action:**

- Check Twitter for partial thread
- Note the tweet IDs in logs
- Decide whether to:
  - Delete partial thread manually
  - Continue with remaining tweets (not supported yet)

---

## Token Refresh

### How Auto-Refresh Works

OAuth 2.0 access tokens expire after **2 hours**. The client automatically refreshes them using the refresh token.

**Refresh flow:**

1. Client detects expired access token
2. Calls X API refresh endpoint with:
   - `refresh_token`
   - `client_id`
3. Receives new `access_token` (refresh_token stays the same)
4. Continues operation seamlessly

**Note:** You don't need to manually refresh tokens. The Tweepy library handles this automatically.

### When Refresh Fails

If refresh fails (invalid refresh token, revoked credentials), you'll need to regenerate tokens:

```bash
python scripts/generate_twitter_oauth2_tokens_auto.py
```

Update your `.env` with the new tokens and restart the server.

---

## Security

### Best Practices

1. **Never commit tokens** - `.env` is in `.gitignore`
2. **Use environment variables** - Don't hardcode credentials
3. **Regenerate compromised tokens** - If tokens leak, regenerate immediately
4. **Limit app permissions** - Only grant "Read and write" (not "Read and write and Direct messages")
5. **Monitor usage** - Check Developer Portal for unexpected API calls

### Securing Tokens

**Do:**

- Store tokens in `.env` (gitignored)
- Use secure credential management in production
- Rotate tokens periodically
- Restrict file permissions: `chmod 600 .env`

**Don't:**

- Commit `.env` to git
- Share tokens in Slack/email
- Log tokens in application logs
- Store tokens in plaintext in production

### Production Deployment

For production environments:

1. Use environment variable injection (Heroku, Vercel, etc.)
2. Consider using secret managers (AWS Secrets Manager, Google Secret Manager)
3. Enable audit logging for token usage
4. Set up alerts for failed authentication attempts

---

## Required Scopes

The application requests these OAuth 2.0 scopes:

| Scope | Purpose |
|-------|---------|
| `tweet.read` | Read tweets (for verification) |
| `tweet.write` | **Post tweets** (required for thread posting!) |
| `users.read` | Get authenticated user info (for logging) |
| `offline.access` | **Get refresh token** (required for auto-refresh!) |

**Important:** Without `tweet.write` and `offline.access`, posting will fail!

---

## References

- [X API Documentation](https://docs.x.com/)
- [X Authentication Overview](https://docs.x.com/xdks/python/authentication)
- [OAuth2PKCEAuth Class](https://docs.x.com/xdks/python/reference/xdk.oauth2_auth)
- [Tweepy Documentation](https://docs.tweepy.org/)
- [X Developer Portal](https://developer.twitter.com/en/portal/projects-and-apps)

---

## Quick Reference

**Generate tokens:**

```bash
python scripts/generate_twitter_oauth2_tokens_auto.py
```

**Test posting:**

```bash
curl -X POST "http://localhost:8000/api/x-thread/post-to-x/2025-01-24"
```

**Enable auto-posting:**

```env
AUTO_POST_TO_X=true
```

**Check logs:**

```bash
tail -f logs/app.log
```

---

## Support

If you encounter issues not covered in this guide:

1. Check the application logs for detailed error messages
2. Verify all configuration steps were followed exactly
3. Test with a simple POST request to isolate the issue
4. Regenerate tokens to rule out token-related problems

For X API-specific issues, consult the [X API Developer Community](https://twittercommunity.com/).
