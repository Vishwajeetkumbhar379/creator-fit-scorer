"""Optional Claude layer: a second opinion on the shortlist plus a drafted outreach note.

The rule-based score stays the source of truth. Claude reads the brief, the
creator's numbers and the rule-based reasons, then returns structured JSON
through a tool call, so the output is always machine-readable.
"""
from __future__ import annotations

import json
import os

from .scoring import Brief, Score

DEFAULT_MODEL = os.environ.get("CREATOR_FIT_MODEL", "claude-sonnet-4-5")

REVIEW_TOOL = {
    "name": "record_review",
    "description": "Record a brand-fit review and an outreach draft for one creator.",
    "input_schema": {
        "type": "object",
        "properties": {
            "fit_summary": {"type": "string", "description": "Two sentences on why this creator fits or not."},
            "adjustment": {
                "type": "integer",
                "minimum": -15,
                "maximum": 15,
                "description": "Points to add or remove from the rule-based score, with a reason in fit_summary.",
            },
            "content_angle": {"type": "string", "description": "One concrete content idea for this creator and product."},
            "outreach_message": {
                "type": "string",
                "description": "A short, warm first DM or email under 90 words. No hashtags, no emojis.",
            },
        },
        "required": ["fit_summary", "adjustment", "content_angle", "outreach_message"],
    },
}

SYSTEM = (
    "You are a senior creator-partnerships manager. You review shortlists for brands. "
    "Be specific and commercially minded. Never invent statistics that are not in the data."
)


def review(score: Score, brief: Brief, client=None, model: str = DEFAULT_MODEL) -> dict:
    """Ask Claude for a structured review. Raises if no API key is configured."""
    if client is None:
        import anthropic  # imported lazily so the tool works offline without it

        client = anthropic.Anthropic()
    c = score.creator
    payload = {
        "brief": {
            "brand": brief.brand,
            "product": brief.product,
            "goal": brief.goal,
            "markets": brief.target_countries,
            "topics": brief.topics,
        },
        "creator": {
            "handle": c.handle,
            "platform": c.platform,
            "followers": c.followers,
            "avg_reach": c.avg_reach,
            "engagement_rate_pct": c.engagement_rate,
            "audience_country": c.audience_country,
            "audience_age": c.audience_age,
            "topics": c.topics,
            "fee_eur": c.est_fee_eur,
        },
        "rule_based": {"score": score.total, "reasons": score.reasons, "risks": score.risks},
    }
    msg = client.messages.create(
        model=model,
        max_tokens=800,
        system=SYSTEM,
        tools=[REVIEW_TOOL],
        tool_choice={"type": "tool", "name": "record_review"},
        messages=[{"role": "user", "content": "Review this creator for the brief:\n" + json.dumps(payload, indent=2)}],
    )
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use":
            out = dict(block.input)
            out["adjustment"] = max(-15, min(15, int(out.get("adjustment", 0))))
            return out
    raise RuntimeError("Claude did not return a structured review")
