"""Email service for sending daily digest newsletters via Resend."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import resend

from app.core.logging import logger
from app.config.settings import settings
from app.db.supabase import supabase
from app.models.daily_digest import DigestSendResult
from app.repositories.daily_digest_repository import DailyDigestRepository


class EmailService:
    """Service for sending digest emails via Resend API."""

    def __init__(self):
        """Initialize email service with Resend API key."""
        if settings.resend_api_key:
            resend.api_key = settings.resend_api_key
        else:
            logger.warning("Resend API key not configured - email sending will fail")

    async def send_digest(
        self,
        digest_id: str,
        html_content: str,
        subject: str,
        to_emails: List[str],
    ) -> DigestSendResult:
        """Send a digest email to specified recipients.

        Args:
            digest_id: UUID of the digest being sent
            html_content: HTML content of the email
            subject: Email subject line
            to_emails: List of email addresses to send to

        Returns:
            DigestSendResult with send status
        """
        logger.info(f"Sending digest {digest_id} to {len(to_emails)} recipients")

        if not settings.resend_api_key:
            return DigestSendResult(
                success=False,
                digest_id=digest_id,
                errors=["Resend API key not configured"],
            )

        if not to_emails:
            return DigestSendResult(
                success=False,
                digest_id=digest_id,
                errors=["No recipients specified"],
            )

        sent_count = 0
        failed_count = 0
        errors = []

        try:
            # Send to each recipient
            for email in to_emails:
                try:
                    response = resend.Emails.send({
                        "from": settings.email_from,
                        "to": [email],
                        "subject": subject,
                        "html": html_content,
                    })

                    if response and response.get("id"):
                        sent_count += 1
                        logger.debug(f"Sent digest to {email}: {response.get('id')}")
                    else:
                        failed_count += 1
                        errors.append(f"Failed to send to {email}: No response ID")

                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to send to {email}: {str(e)}")
                    logger.warning(f"Failed to send digest to {email}: {e}")

            # Update digest record if any were sent
            if sent_count > 0:
                digest_repo = DailyDigestRepository()
                await digest_repo.mark_digest_sent(digest_id, sent_count)

            return DigestSendResult(
                success=sent_count > 0,
                digest_id=digest_id,
                recipients_sent=sent_count,
                recipients_failed=failed_count,
                sent_at=datetime.now(timezone.utc) if sent_count > 0 else None,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Email sending failed for digest {digest_id}: {e}", exc_info=True)
            return DigestSendResult(
                success=False,
                digest_id=digest_id,
                errors=[f"Email sending failed: {str(e)}"],
            )

    async def send_digest_to_subscribers(self, digest_id: str) -> DigestSendResult:
        """Send a digest to all active subscribers.

        Args:
            digest_id: UUID of the digest to send

        Returns:
            DigestSendResult with send statistics
        """
        logger.info(f"Sending digest {digest_id} to all subscribers")

        try:
            # Get digest content
            digest_repo = DailyDigestRepository()
            digest = await digest_repo.get_digest_by_id(digest_id)

            if not digest:
                return DigestSendResult(
                    success=False,
                    digest_id=digest_id,
                    errors=["Digest not found"],
                )

            if not digest.formatted_html:
                return DigestSendResult(
                    success=False,
                    digest_id=digest_id,
                    errors=["Digest has no HTML content"],
                )

            # Get active subscribers
            subscribers = await self._get_active_subscribers()

            if not subscribers:
                return DigestSendResult(
                    success=False,
                    digest_id=digest_id,
                    errors=["No active subscribers found"],
                )

            # Send digest
            subject = f"{digest.title} - Daily AI Digest"
            to_emails = [s["email"] for s in subscribers]

            return await self.send_digest(
                digest_id=digest_id,
                html_content=digest.formatted_html,
                subject=subject,
                to_emails=to_emails,
            )

        except Exception as e:
            logger.error(f"Failed to send digest to subscribers: {e}", exc_info=True)
            return DigestSendResult(
                success=False,
                digest_id=digest_id,
                errors=[f"Failed to send to subscribers: {str(e)}"],
            )

    async def send_test_digest(
        self,
        digest_id: str,
        test_email: str,
    ) -> DigestSendResult:
        """Send a test digest to a single email address.

        Args:
            digest_id: UUID of the digest to test
            test_email: Email address to send test to

        Returns:
            DigestSendResult with send status
        """
        logger.info(f"Sending test digest {digest_id} to {test_email}")

        try:
            digest_repo = DailyDigestRepository()
            digest = await digest_repo.get_digest_by_id(digest_id)

            if not digest:
                return DigestSendResult(
                    success=False,
                    digest_id=digest_id,
                    errors=["Digest not found"],
                )

            if not digest.formatted_html:
                return DigestSendResult(
                    success=False,
                    digest_id=digest_id,
                    errors=["Digest has no HTML content"],
                )

            subject = f"[TEST] {digest.title} - Daily AI Digest"

            return await self.send_digest(
                digest_id=digest_id,
                html_content=digest.formatted_html,
                subject=subject,
                to_emails=[test_email],
            )

        except Exception as e:
            logger.error(f"Failed to send test digest: {e}", exc_info=True)
            return DigestSendResult(
                success=False,
                digest_id=digest_id,
                errors=[f"Failed to send test: {str(e)}"],
            )

    async def _get_active_subscribers(self) -> List[Dict[str, Any]]:
        """Get list of active subscribers from database.

        Returns:
            List of subscriber dicts with email and name
        """
        try:
            result = (
                supabase.table("subscribers")
                .select("email, name")
                .eq("is_active", True)
                .execute()
            )
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get subscribers: {e}", exc_info=True)
            return []

    async def add_subscriber(
        self,
        email: str,
        name: Optional[str] = None,
    ) -> bool:
        """Add a new subscriber.

        Args:
            email: Email address to subscribe
            name: Optional subscriber name

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "email": email,
                "is_active": True,
                "subscribed_at": datetime.now(timezone.utc).isoformat(),
            }
            if name:
                data["name"] = name

            supabase.table("subscribers").upsert(
                data,
                on_conflict="email"
            ).execute()

            logger.info(f"Added subscriber: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to add subscriber {email}: {e}", exc_info=True)
            return False

    async def remove_subscriber(self, email: str) -> bool:
        """Remove a subscriber (mark as inactive).

        Args:
            email: Email address to unsubscribe

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase.table("subscribers").update({
                "is_active": False,
                "unsubscribed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("email", email).execute()

            logger.info(f"Removed subscriber: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove subscriber {email}: {e}", exc_info=True)
            return False

    async def get_subscriber_count(self) -> int:
        """Get count of active subscribers.

        Returns:
            Number of active subscribers
        """
        try:
            result = (
                supabase.table("subscribers")
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            return result.count or 0

        except Exception as e:
            logger.error(f"Failed to get subscriber count: {e}", exc_info=True)
            return 0
