"""Rule-based creator scoring.

Every score is explainable: each pillar returns a 0-100 value plus the reasons
behind it, so a marketer can defend a shortlist in front of a client.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Typical engagement-rate bands by follower tier (Instagram-style, in %).
# Rough industry rules of thumb, used only to spot outliers. Tune per platform.
TIER_BANDS = [
    # (max_followers, tier_name, healthy_low, healthy_high)
    (10_000, "nano", 2.5, 9.0),
    (50_000, "micro", 1.8, 6.5),
    (250_000, "mid", 1.2, 4.5),
    (1_000_000, "macro", 0.8, 3.5),
    (float("inf"), "mega", 0.5, 2.5),
]

DEFAULT_WEIGHTS = {
    "audience_fit": 0.30,
    "content_fit": 0.25,
    "engagement_health": 0.25,
    "cost_efficiency": 0.10,
    "brand_safety": 0.10,
}


@dataclass
class Creator:
    handle: str
    platform: str
    followers: int
    avg_reach: int
    engagement_rate: float  # percent, e.g. 3.2
    audience_country: str  # top audience country, ISO-2
    audience_age: str  # dominant band, e.g. "25-34"
    topics: list[str]
    est_fee_eur: float
    recent_flags: list[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict) -> "Creator":
        def split(v: str) -> list[str]:
            return [t.strip().lower() for t in (v or "").split(";") if t.strip()]

        return cls(
            handle=row["handle"].strip(),
            platform=row["platform"].strip().lower(),
            followers=int(float(row["followers"])),
            avg_reach=int(float(row["avg_reach"])),
            engagement_rate=float(row["engagement_rate"]),
            audience_country=row["audience_country"].strip().upper(),
            audience_age=row["audience_age"].strip(),
            topics=split(row.get("topics", "")),
            est_fee_eur=float(row["est_fee_eur"]),
            recent_flags=split(row.get("recent_flags", "")),
        )


@dataclass
class Brief:
    brand: str
    product: str
    goal: str
    target_countries: list[str]
    target_ages: list[str]
    topics: list[str]
    platforms: list[str]
    budget_eur: float
    max_cpm_eur: float = 60.0
    blocked_topics: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    @classmethod
    def from_dict(cls, d: dict) -> "Brief":
        low = lambda xs: [x.strip().lower() for x in xs]
        weights = dict(DEFAULT_WEIGHTS)
        weights.update(d.get("weights", {}))
        return cls(
            brand=d["brand"],
            product=d["product"],
            goal=d["goal"],
            target_countries=[c.upper() for c in d["target_countries"]],
            target_ages=d["target_ages"],
            topics=low(d["topics"]),
            platforms=low(d["platforms"]),
            budget_eur=float(d["budget_eur"]),
            max_cpm_eur=float(d.get("max_cpm_eur", 60.0)),
            blocked_topics=low(d.get("blocked_topics", [])),
            weights=weights,
        )


@dataclass
class Score:
    creator: Creator
    total: float
    pillars: dict[str, float]
    reasons: list[str]
    risks: list[str]
    tier: str

    @property
    def verdict(self) -> str:
        if self.risks and any(r.startswith("BLOCK") for r in self.risks):
            return "reject"
        if self.total >= 75:
            return "shortlist"
        if self.total >= 55:
            return "maybe"
        return "pass"


def tier_for(followers: int) -> tuple[str, float, float]:
    for max_f, name, lo, hi in TIER_BANDS:
        if followers <= max_f:
            return name, lo, hi
    raise ValueError("unreachable")


def _audience_fit(c: Creator, b: Brief, reasons: list[str]) -> float:
    score = 0.0
    if c.audience_country in b.target_countries:
        score += 60
        reasons.append(f"Audience mostly in {c.audience_country}, a target market")
    else:
        reasons.append(f"Audience mostly in {c.audience_country}, outside target markets")
    if c.audience_age in b.target_ages:
        score += 40
        reasons.append(f"Core age band {c.audience_age} matches the brief")
    return score


def _content_fit(c: Creator, b: Brief, reasons: list[str]) -> float:
    if not b.topics:
        return 50.0
    overlap = sorted(set(c.topics) & set(b.topics))
    score = min(100.0, 100.0 * len(overlap) / min(3, len(b.topics)))
    if overlap:
        reasons.append("Content overlaps on " + ", ".join(overlap))
    if c.platform not in b.platforms:
        score *= 0.5
        reasons.append(f"Mainly on {c.platform}, not a priority platform")
    return score


def _engagement_health(c: Creator, risks: list[str], reasons: list[str]) -> tuple[float, str]:
    tier, lo, hi = tier_for(c.followers)
    er = c.engagement_rate
    reach_ratio = c.avg_reach / max(c.followers, 1)
    if er < lo:
        score = max(0.0, 100.0 * er / lo) * 0.7
        risks.append(f"Engagement {er:.1f}% is below the {tier} band ({lo}-{hi}%)")
    elif er > hi * 1.8:
        score = 40.0
        risks.append(f"Engagement {er:.1f}% is unusually high for {tier}; check for engagement pods")
    else:
        score = 100.0 if er <= hi else 85.0
        reasons.append(f"Healthy engagement for a {tier} creator ({er:.1f}%)")
    if reach_ratio < 0.08:
        score *= 0.8
        risks.append(f"Reach is only {reach_ratio:.0%} of followers; audience may be inactive")
    return score, tier


def _cost_efficiency(c: Creator, b: Brief, reasons: list[str], risks: list[str]) -> float:
    cpm = c.est_fee_eur / max(c.avg_reach, 1) * 1000
    if c.est_fee_eur > b.budget_eur * 0.4:
        risks.append(f"Fee would use {c.est_fee_eur / b.budget_eur:.0%} of the budget")
    if cpm <= b.max_cpm_eur * 0.5:
        reasons.append(f"Strong value at about EUR {cpm:.0f} per 1,000 reached")
        return 100.0
    if cpm <= b.max_cpm_eur:
        return 75.0
    risks.append(f"Expensive reach at about EUR {cpm:.0f} per 1,000 (cap EUR {b.max_cpm_eur:.0f})")
    return max(0.0, 100.0 - (cpm - b.max_cpm_eur) * 3)


def _brand_safety(c: Creator, b: Brief, risks: list[str]) -> float:
    hits = sorted(set(c.topics) & set(b.blocked_topics))
    if hits:
        risks.append("BLOCK: covers blocked topics: " + ", ".join(hits))
        return 0.0
    if c.recent_flags:
        risks.append("Recent flags: " + ", ".join(c.recent_flags))
        return max(0.0, 100.0 - 35.0 * len(c.recent_flags))
    return 100.0


def score_creator(c: Creator, b: Brief) -> Score:
    reasons: list[str] = []
    risks: list[str] = []
    eng, tier = _engagement_health(c, risks, reasons)
    pillars = {
        "audience_fit": _audience_fit(c, b, reasons),
        "content_fit": _content_fit(c, b, reasons),
        "engagement_health": eng,
        "cost_efficiency": _cost_efficiency(c, b, reasons, risks),
        "brand_safety": _brand_safety(c, b, risks),
    }
    wsum = sum(b.weights.values()) or 1.0
    total = sum(pillars[k] * b.weights.get(k, 0) for k in pillars) / wsum
    return Score(c, round(total, 1), {k: round(v, 1) for k, v in pillars.items()}, reasons, risks, tier)


def rank(creators: list[Creator], brief: Brief) -> list[Score]:
    scores = [score_creator(c, brief) for c in creators]
    order = {"shortlist": 0, "maybe": 1, "pass": 2, "reject": 3}
    return sorted(scores, key=lambda s: (order[s.verdict], -s.total))
