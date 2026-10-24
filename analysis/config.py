"""Analysis settings. Every threshold named in BUILD_SPEC.md lives here once."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Default file locations (see BUILD_SPEC.md "Data flow").
CLEAN_CSV = PROJECT_DIR / "outputs" / "listens_clean.csv"
LISTENS_PARQUET = PROJECT_DIR / "data" / "processed" / "listens.parquet"
AGGREGATES_DIR = PROJECT_DIR / "data" / "aggregates"
DEMO_DIR = PROJECT_DIR / "data" / "demo"

POPULATIONS = ("all", "exclude_heavy")


@dataclass(frozen=True)
class AnalysisConfig:
    """Offline settings used by build_aggregates.py. Changing one means rebuilding."""

    # 28 days ending on the last observed listen day (dump 2686 ends 2026-09-28).
    window_start: date = date(2026, 9, 1)   # first UTC day, inclusive
    window_end: date = date(2026, 9, 28)    # last UTC day, inclusive
    return_horizon_days: int = 7            # a return is a listen 1..7 days after discovery day
    early_period_days: int = 14             # early = days 1-14 of window, late = days 15-28
    store_min_listeners: int = 2            # artists below this are not written to aggregates
    segment_edges: tuple[int, int] = (50, 500)  # window listens: light < 50 <= moderate < 500 <= heavy

    @property
    def n_days(self) -> int:
        return (self.window_end - self.window_start).days + 1

    @property
    def last_eligible_discovery(self) -> date:
        """Latest discovery day that still has a full return horizon inside the window."""
        return self.window_end - timedelta(days=self.return_horizon_days)

    @property
    def late_start(self) -> date:
        return self.window_start + timedelta(days=self.early_period_days)


SEGMENT_ORDER = ("light", "moderate", "heavy")


@dataclass(frozen=True)
class ScoringParams:
    """Live settings the dashboard exposes as controls. Defaults are the starting view."""

    min_listeners: int = 5            # window listeners floor ("below_floor" under it)
    max_listeners: int = 200          # window listeners ceiling ("established" above it)
    min_eligible_new: int = 5         # eligible new listeners needed for a return rate
    single_fan_share: float = 0.5     # top_listener_share above this sets single_fan_risk
    exclude_single_fan: bool = True   # drop single_fan_risk artists from the shortlist
    weights: dict = field(default_factory=lambda: {
        "new_listeners": 0.25,
        "return_rate": 0.25,
        "repeat_listener_rate": 0.25,
        "growth_ratio": 0.25,
    })
