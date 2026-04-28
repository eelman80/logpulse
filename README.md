# logpulse

Lightweight log tailer with pattern alerting and Slack/webhook notifications.

---

## Installation

```bash
pip install logpulse
```

Or install from source:

```bash
git clone https://github.com/youruser/logpulse.git && cd logpulse && pip install .
```

---

## Usage

Tail a log file and alert when a pattern is matched:

```bash
logpulse --file /var/log/app.log --pattern "ERROR|CRITICAL" --webhook https://hooks.slack.com/your/webhook
```

You can also use a config file:

```yaml
# logpulse.yml
file: /var/log/app.log
patterns:
  - ERROR
  - CRITICAL
  - "out of memory"
webhook: https://hooks.slack.com/your/webhook
cooldown: 60  # seconds between repeated alerts
```

```bash
logpulse --config logpulse.yml
```

**Python API:**

```python
from logpulse import LogPulse

pulse = LogPulse(file="/var/log/app.log", patterns=["ERROR"], webhook="https://...")
pulse.start()
```

---

## Features

- Real-time log tailing with low resource overhead
- Regex pattern matching with configurable cooldowns
- Slack and generic webhook notification support
- Simple CLI and Python API

---

## License

MIT © 2024 Your Name