"""Command line: creator-fit examples/creators.csv examples/brief.toml"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import tomllib
from pathlib import Path

from .report import to_csv, to_markdown
from .scoring import Brief, Creator, rank


def load(creators_path: Path, brief_path: Path) -> tuple[list[Creator], Brief]:
    with open(creators_path, newline="", encoding="utf-8") as f:
        creators = [Creator.from_row(r) for r in csv.DictReader(f)]
    with open(brief_path, "rb") as f:
        brief = Brief.from_dict(tomllib.load(f))
    return creators, brief


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="creator-fit", description="Score and rank creators against a brand brief.")
    p.add_argument("creators", type=Path, help="CSV of creators")
    p.add_argument("brief", type=Path, help="TOML brand brief")
    p.add_argument("--out", type=Path, default=Path("out"), help="Output folder (default: out)")
    p.add_argument("--ai", action="store_true", help="Add a Claude review and outreach draft for the shortlist")
    p.add_argument("--top", type=int, default=5, help="How many creators get an AI review (default: 5)")
    args = p.parse_args(argv)

    creators, brief = load(args.creators, args.brief)
    scores = rank(creators, brief)

    reviews: dict[str, dict] = {}
    if args.ai:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Set ANTHROPIC_API_KEY to use --ai. Continuing with rule-based scores only.", file=sys.stderr)
        else:
            from .llm import review

            for s in [s for s in scores if s.verdict in ("shortlist", "maybe")][: args.top]:
                reviews[s.creator.handle] = review(s, brief)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "shortlist.md").write_text(to_markdown(scores, brief, reviews), encoding="utf-8")
    to_csv(scores, args.out / "ranked.csv", reviews)

    width = max(len(s.creator.handle) for s in scores)
    print(f"\n{brief.brand} · {brief.product} · {len(scores)} creators scored\n")
    for s in scores:
        print(f"  {s.creator.handle:<{width}}  {s.total:5.1f}  {s.verdict}")
    print(f"\nReport: {args.out / 'shortlist.md'}\nTable:  {args.out / 'ranked.csv'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
