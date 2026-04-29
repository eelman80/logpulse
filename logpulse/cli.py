"""Command-line entry point for logpulse."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from logpulse.config import load
from logpulse.formatter import FormatConfig, format_alert
from logpulse.matcher import Matcher
from logpulse.notifier import WebhookNotifier
from logpulse.pipeline import Pipeline
from logpulse.throttle import AlertThrottle, ThrottleConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("logpulse")


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logpulse",
        description="Tail a log file and send alerts on pattern matches.",
    )
    p.add_argument("config", metavar="CONFIG", help="Path to TOML config file")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print alerts to stdout instead of sending notifications",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Process current log content once and exit",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging verbosity (default: INFO)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    logging.getLogger().setLevel(args.log_level)

    config_path = Path(args.config)
    if not config_path.exists():
        log.error("Config file not found: %s", config_path)
        return 1

    try:
        app_config = load(config_path)
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to load config: %s", exc)
        return 1

    matcher = Matcher.from_config(app_config.patterns)
    fmt_config = FormatConfig()

    if args.dry_run:
        def notify(alert):
            print(format_alert(alert, source=str(app_config.log_path), config=fmt_config))
        notifier = type("_DryRun", (), {"send": staticmethod(notify)})()
    else:
        nc = app_config.notifier
        notifier = WebhookNotifier(url=nc.url, timeout=nc.timeout)

    throttle_cfg = ThrottleConfig(cooldown_seconds=app_config.throttle_seconds)
    throttle = AlertThrottle(throttle_cfg)

    pipeline = Pipeline(
        log_path=app_config.log_path,
        matcher=matcher,
        notifier=notifier,
        throttle=throttle,
        poll_interval=app_config.poll_interval,
    )

    if args.once:
        pipeline.run_once()
        return 0

    try:
        pipeline.run()
    except KeyboardInterrupt:
        log.info("Interrupted — shutting down.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
