#!/usr/bin/env python3
"""Check Twitter OAuth2 token validity and provide actionable steps."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import tweepy

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Allow HTTP for localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def main():
    print("\n" + "="*70)
    print("Twitter OAuth2 Token Status Checker")
    print("="*70)
    print()

    # Load credentials from .env
    client_id = os.getenv("TWITTER_OAUTH2_CLIENT_ID")
    client_secret = os.getenv("TWITTER_OAUTH2_CLIENT_SECRET")
    access_token = os.getenv("TWITTER_OAUTH2_ACCESS_TOKEN")
    refresh_token = os.getenv("TWITTER_OAUTH2_REFRESH_TOKEN")

    if not all([client_id, client_secret, access_token, refresh_token]):
        print("❌ Missing OAuth2 credentials in .env file")
        print()
        print("Required variables:")
        print("  - TWITTER_OAUTH2_CLIENT_ID")
        print("  - TWITTER_OAUTH2_CLIENT_SECRET")
        print("  - TWITTER_OAUTH2_ACCESS_TOKEN")
        print("  - TWITTER_OAUTH2_REFRESH_TOKEN")
        print()
        print("Run: python scripts/generate_twitter_oauth2_tokens_auto.py")
        sys.exit(1)

    print(f"Client ID: {client_id[:20]}...")
    print(f"Access Token: {access_token[:30]}...")
    print(f"Refresh Token: {refresh_token[:30]}...")
    print()

    # Test 1: Check if access token works
    print("="*70)
    print("TEST 1: Access Token Validity")
    print("="*70)
    print()

    try:
        client = tweepy.Client(bearer_token=access_token)
        me = client.get_me(user_auth=False)
        print(f"✅ Access token is VALID")
        print(f"   User: @{me.data.username} (ID: {me.data.id})")
        print()
        print("🎉 Your tokens are working! No action needed.")
        sys.exit(0)

    except tweepy.errors.Unauthorized:
        print("❌ Access token is EXPIRED or INVALID")
        print("   Attempting refresh...")
        print()

    except Exception as e:
        print(f"❌ Unexpected error testing access token: {e}")
        print()

    # Test 2: Try to refresh the token
    print("="*70)
    print("TEST 2: Refresh Token Validity")
    print("="*70)
    print()

    try:
        oauth2_handler = tweepy.OAuth2UserHandler(
            client_id=client_id,
            redirect_uri="http://127.0.0.1:8080/callback",
            scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
            client_secret=client_secret,
        )

        oauth2_handler.token = {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        token_url = "https://api.twitter.com/2/oauth2/token"
        new_token = oauth2_handler.refresh_token(token_url)

        print("✅ Refresh token is VALID")
        print("   Successfully refreshed access token!")
        print()
        print("New tokens:")
        print(f"  Access Token: {new_token['access_token'][:30]}...")
        if 'refresh_token' in new_token:
            print(f"  Refresh Token: {new_token['refresh_token'][:30]}...")
        print()
        print("="*70)
        print("ACTION REQUIRED: Update .env file")
        print("="*70)
        print()
        print("Copy these lines to your .env file:")
        print()
        print(f"TWITTER_OAUTH2_ACCESS_TOKEN={new_token['access_token']}")
        if 'refresh_token' in new_token:
            print(f"TWITTER_OAUTH2_REFRESH_TOKEN={new_token['refresh_token']}")
        print()
        print("Then restart your application.")

    except Exception as e:
        print("❌ Refresh token is INVALID or EXPIRED")
        print(f"   Error: {e}")
        print()
        print("="*70)
        print("ACTION REQUIRED: Regenerate Tokens")
        print("="*70)
        print()
        print("Your refresh token has expired or been revoked.")
        print()
        print("Run this command to generate new tokens:")
        print()
        print("  python scripts/generate_twitter_oauth2_tokens_auto.py")
        print()
        print("Follow the prompts to authorize and get new tokens.")
        sys.exit(1)


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
