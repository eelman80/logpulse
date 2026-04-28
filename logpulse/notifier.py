"""Webhook / Slack notification dispatcher."""

import json
import logging
import urllib.request
from typing import Optional

from logpulse.matcher import Alert

logger = logging.getLogger(__name__)


SEVERITY_EMOJI = {
    "info": ":information_source:",
    "warning": ":warning:",
    "critical": ":red_circle:",
}


def _slack_payload(alert: Alert, source: Optional[str] = None) -> dict:
    """Build a Slack-compatible JSON payload for *alert*."""
    emoji = SEVERITY_EMOJI.get(alert.severity, ":bell:")
    header = f"{emoji} *{alert.label}* ({alert.severity})"
    body = f"```{alert.line.rstrip()}```"
    if source:
        body = f"_Source: {source}_\n" + body
    return {"text": f"{header}\n{body}"}


class WebhookNotifier:
    """Sends alert notifications to a webhook URL (Slack-compatible)."""

    def __init__(
        self,
        url: str,
        timeout: int = 5,
        source: Optional[str] = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.source = source

    def send(self, alert: Alert) -> bool:
        """POST *alert* to the webhook.  Returns True on success."""
        payload = _slack_payload(alert, source=self.source)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                if status != 200:
                    logger.warning("Webhook returned HTTP %s", status)
                    return False
                return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send webhook notification: %s", exc)
            return False
