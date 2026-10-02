from __future__ import annotations

import csv
from pathlib import Path

from .scoring import Brief, Score

LABEL = {
    "audience_fit": "Audience",
    "content_fit": "Content",
    "engagement_health": "Engagement",
    "cost_efficiency": "Cost",
    "brand_safety": "Safety",
}


def _bar(v: float, width: int = 10) -> str:
    n = round(v / 100 * width)
    return "█" * n + "░" * (width - n)


def to_markdown(scores: list[Score], brief: Brief, reviews: dict[str, dict] | None = None) -> str:
    reviews = reviews or {}
    lines = [
        f"# Creator shortlist · {brief.brand}",
        "",
        f"**Product:** {brief.product}  ",
        f"**Goal:** {brief.goal}  ",
        f"**Markets:** {', '.join(brief.target_countries)} · **Budget:** EUR {brief.budget_eur:,.0f}",
        "",
        "| Rank | Creator | Tier | Score | Verdict |",
        "|---:|---|---|---:|---|",
    ]
    for i, s in enumerate(scores, 1):
        lines.append(f"| {i} | {s.creator.handle} | {s.tier} | {s.total:.1f} | {s.verdict} |")
    lines.append("")
    for i, s in enumerate(scores, 1):
        c = s.creator
        adj = reviews.get(c.handle, {}).get("adjustment")
        head = f"## {i}. {c.handle} · {s.total:.1f}"
        if adj:
            head += f" (AI adjusted {adj:+d} → {s.total + adj:.1f})"
        lines += [head, "", f"{c.platform} · {c.followers:,} followers · {c.engagement_rate:.1f}% ER · EUR {c.est_fee_eur:,.0f}", ""]
        lines += [f"`{LABEL[k]:<10} {_bar(v)} {v:5.1f}`  " for k, v in s.pillars.items()]
        lines.append("")
        if s.reasons:
            lines += ["**Why**", *[f"- {r}" for r in s.reasons], ""]
        if s.risks:
            lines += ["**Watch out**", *[f"- {r}" for r in s.risks], ""]
        if c.handle in reviews:
            r = reviews[c.handle]
            lines += [
                "**AI review**",
                "",
                r["fit_summary"],
                "",
                f"*Content angle:* {r['content_angle']}",
                "",
                "*Outreach draft:*",
                "",
                "> " + r["outreach_message"].replace("\n", "\n> "),
                "",
            ]
    return "\n".join(lines)


def to_csv(scores: list[Score], path: Path, reviews: dict[str, dict] | None = None) -> None:
    reviews = reviews or {}
    fields = ["rank", "handle", "platform", "tier", "score", "verdict", *LABEL.keys(), "risks", "ai_adjustment", "outreach_message"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, s in enumerate(scores, 1):
            r = reviews.get(s.creator.handle, {})
            w.writerow(
                {
                    "rank": i,
                    "handle": s.creator.handle,
                    "platform": s.creator.platform,
                    "tier": s.tier,
                    "score": s.total,
                    "verdict": s.verdict,
                    **s.pillars,
                    "risks": " | ".join(s.risks),
                    "ai_adjustment": r.get("adjustment", ""),
                    "outreach_message": r.get("outreach_message", ""),
                }
            )
