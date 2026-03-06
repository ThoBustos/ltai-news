#!/usr/bin/env python3
"""Generate OAuth 2.0 User Context tokens for Twitter API.

This script uses the Authorization Code with PKCE flow to generate
tokens that support read+write operations (posting tweets).

Usage:
    python scripts/generate_twitter_oauth2_tokens.py

Requirements:
    - Twitter Developer Portal app with OAuth 2.0 enabled
    - Client ID and Client Secret from OAuth 2.0 section
    - Redirect URI configured: http://127.0.0.1:8080/callback
"""

import tweepy
import sys
from pathlib import Path

# Configuration
CLIENT_ID = input("Enter your OAuth 2.0 Client ID: ").strip()
CLIENT_SECRET = input("Enter your OAuth 2.0 Client Secret: ").strip()
REDIRECT_URI = "http://127.0.0.1:8080/callback"
SCOPES = ["tweet.read", "tweet.write", "users.read", "offline.access"]

def main():
    """Generate OAuth 2.0 User Context tokens using PKCE flow."""

    print("\n" + "="*70)
    print("Twitter OAuth 2.0 User Context Token Generator")
    print("="*70)
    print()
    print("This script will:")
    print("1. Generate an authorization URL")
    print("2. Open your browser for authorization")
    print("3. Exchange the authorization code for tokens")
    print("4. Display your access_token and refresh_token")
    print()
    print(f"Redirect URI: {REDIRECT_URI}")
    print(f"Scopes: {', '.join(SCOPES)}")
    print()

    # Create OAuth2UserHandler
    try:
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=SCOPES,
            client_secret=CLIENT_SECRET,
        )
    except Exception as e:
        print(f"❌ Error creating OAuth2UserHandler: {e}")
        print()
        print("Common issues:")
        print("- Invalid Client ID or Client Secret")
        print("- Redirect URI not configured in Twitter Developer Portal")
        print("- OAuth 2.0 not enabled in app settings")
        sys.exit(1)

    # Get authorization URL
    auth_url = oauth2_user_handler.get_authorization_url()

    print("="*70)
    print("STEP 1: Authorize the Application")
    print("="*70)
    print()
    print("Please open this URL in your browser:")
    print()
    print(f"    {auth_url}")
    print()
    print("After authorizing, you'll be redirected to a URL that starts with:")
    print(f"    {REDIRECT_URI}?code=...")
    print()

    # Get authorization response from user
    authorization_response = input("Paste the FULL redirect URL here: ").strip()

    if not authorization_response:
        print("❌ No URL provided. Exiting.")
        sys.exit(1)

    # Exchange authorization code for access token
    print()
    print("="*70)
    print("STEP 2: Fetching Tokens")
    print("="*70)
    print()

    try:
        token = oauth2_user_handler.fetch_token(authorization_response)
    except Exception as e:
        print(f"❌ Error fetching token: {e}")
        print()
        print("Common issues:")
        print("- Invalid authorization URL (make sure you copied the FULL URL)")
        print("- Authorization code expired (codes are single-use and expire quickly)")
        print("- Redirect URI mismatch between code and configuration")
        sys.exit(1)

    # Display tokens
    print("✅ Tokens generated successfully!")
    print()
    print("="*70)
    print("OAuth 2.0 User Context Tokens")
    print("="*70)
    print()
    print(f"Access Token:  {token['access_token']}")
    print(f"Refresh Token: {token.get('refresh_token', 'N/A')}")
    print()
    print("Token Type:", token.get('token_type', 'bearer'))
    print("Expires In:", token.get('expires_in', 'N/A'), "seconds (~2 hours)")
    print("Scope:", token.get('scope', SCOPES))
    print()

    # Generate .env configuration
    print("="*70)
    print(".env Configuration")
    print("="*70)
    print()
    print("Add these lines to your .env file:")
    print()
    print(f"TWITTER_OAUTH2_CLIENT_ID={CLIENT_ID}")
    print(f"TWITTER_OAUTH2_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"TWITTER_OAUTH2_ACCESS_TOKEN={token['access_token']}")
    print(f"TWITTER_OAUTH2_REFRESH_TOKEN={token.get('refresh_token', '')}")
    print("TWITTER_USE_OAUTH2=true")
    print()

    # Test the token
    print("="*70)
    print("STEP 3: Testing Token")
    print("="*70)
    print()

    try:
        # Create client with new token
        client = tweepy.Client(bearer_token=token['access_token'])

        # Test get_me()
        me = client.get_me(user_auth=False)
        print(f"✅ Token verified! User: @{me.data.username} (ID: {me.data.id})")
        print()
        print("Your OAuth 2.0 User Context tokens are ready to use!")
        print()

    except Exception as e:
        print(f"⚠️  Token generated but verification failed: {e}")
        print()
        print("The tokens should still work, but you may want to verify them manually.")
        print()

    print("="*70)
    print("Next Steps")
    print("="*70)
    print()
    print("1. Copy the tokens to your .env file")
    print("2. Set TWITTER_USE_OAUTH2=true")
    print("3. Restart your application")
    print("4. Test posting a tweet")
    print()
    print("Note: Access tokens expire after ~2 hours, but refresh tokens allow")
    print("      automatic renewal. Tweepy will handle this automatically.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
