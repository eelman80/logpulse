"""Alert escalation: promote severity when a pattern fires repeatedly within a window."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Dict, List, Optional, Tuple


@dataclass
class EscalationConfig:
    """Configuration for a single escalation tier."""
    threshold: int = 5          # hits within *window_seconds* to trigger escalation
    window_seconds: float = 60.0
    escalated_severity: str = "critical"
    enabled: bool = True

    @staticmethod
    def from_dict(d: dict) -> "EscalationConfig":
        return EscalationConfig(
            threshold=int(d.get("threshold", 5)),
            window_seconds=float(d.get("window_seconds", 60.0)),
            escalated_severity=str(d.get("escalated_severity", "critical")),
            enabled=bool(d.get("enabled", True)),
        )


@dataclass
class _LabelState:
    hits: List[float] = field(default_factory=list)
    escalated: bool = False


class AlertEscalator:
    """Track per-label hit counts and escalate severity when thresholds are crossed."""

    def __init__(self, cfg: Optional[EscalationConfig] = None) -> None:
        self._cfg: EscalationConfig = cfg or EscalationConfig()
        self._state: Dict[str, _LabelState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, label: str, severity: str, *, _now: Optional[float] = None) -> str:
        """Record a hit for *label* and return the (possibly escalated) severity."""
        if not self._cfg.enabled:
            return severity

        now = _now if _now is not None else monotonic()
        state = self._state.setdefault(label, _LabelState())

        # Prune stale hits outside the window
        cutoff = now - self._cfg.window_seconds
        state.hits = [t for t in state.hits if t >= cutoff]
        state.hits.append(now)

        if len(state.hits) >= self._cfg.threshold:
            state.escalated = True
            return self._cfg.escalated_severity

        return severity

    def is_escalated(self, label: str) -> bool:
        """Return True if *label* is currently in an escalated state."""
        return self._state.get(label, _LabelState()).escalated

    def reset(self, label: str) -> None:
        """Clear hit history and escalation flag for *label*."""
        self._state.pop(label, None)

    def snapshot(self) -> Dict[str, Tuple[int, bool]]:
        """Return {label: (hit_count, escalated)} for all tracked labels."""
        return {lbl: (len(s.hits), s.escalated) for lbl, s in self._state.items()}
