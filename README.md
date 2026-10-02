# Creator Fit Scorer

**Turn a two-day creator shortlist into a one-hour review.**

Drop in a list of creators and a brand brief. The scorer ranks every creator on five pillars, explains each score in plain language, flags risky accounts, and (optionally) asks Claude for a second opinion plus a ready-to-send outreach draft.

I built this because I spent years doing this by hand. Across 850+ creator deals for brands like HUL, Philips and L'Oréal, the shortlist step always ate the most time and was the hardest to defend to clients. This makes it fast, consistent and explainable.

```
$ creator-fit examples/creators.csv examples/brief.toml

Nordlys Skin · Barrier Repair Serum · 8 creators scored

  @lena.glowlab      98.3  shortlist
  @sofia.selfcare    94.0  shortlist
  @mats.minimal      89.2  shortlist
  @hautnah.anna      82.7  shortlist
  @cleanbeauty.kai   81.3  shortlist
  @zurich.zoe        73.3  maybe
  @luxe.lifestyle    29.0  pass
  @quick.gains.max   50.0  reject
```

See the full generated report in [`examples/output/shortlist.md`](examples/output/shortlist.md).

## How scoring works

Each creator gets a 0 to 100 score per pillar. The brief sets the weights.

| Pillar | Weight | What it checks |
|---|---:|---|
| Audience fit | 30% | Is the audience in the target markets and age band? |
| Content fit | 25% | Do their topics overlap with the brief? Are they on a priority platform? |
| Engagement health | 25% | Is engagement normal for their follower tier? Very low means a passive audience; very high can mean engagement pods. Low reach-to-follower ratio is flagged. |
| Cost efficiency | 10% | Estimated cost per 1,000 people reached against the brief's cap, and share of total budget. |
| Brand safety | 10% | Blocked topics reject the creator outright; recent controversies lower the score. |

Verdicts: **shortlist** (75+), **maybe** (55 to 74), **pass** (below 55), **reject** (brand-safety block).

Every number comes with its reasons, for example *"Engagement 14.5% is unusually high for mid; check for engagement pods"*, so the shortlist is easy to defend in a client meeting.

## The AI layer (optional)

```bash
pip install -e ".[ai]"
export ANTHROPIC_API_KEY=sk-...
creator-fit examples/creators.csv examples/brief.toml --ai --top 5
```

For the top creators, Claude receives the brief, the creator's numbers and the rule-based reasons, and returns **structured JSON through tool use**:

- a two-sentence fit summary
- a score adjustment, clamped to ±15 so the AI can refine the ranking but never override the rules
- one concrete content angle for this creator and product
- a short first-outreach message

The rules stay the source of truth. The model adds judgement where rules are weak, like tone of voice or content ideas.

## Quick start

```bash
git clone https://github.com/Vishwajeetkumbhar379/creator-fit-scorer
cd creator-fit-scorer
pip install -e ".[dev]"
creator-fit examples/creators.csv examples/brief.toml
pytest
```

No dependencies are needed for rule-based scoring. Python 3.11+.

## Inputs

**`creators.csv`**: `handle, platform, followers, avg_reach, engagement_rate, audience_country, audience_age, topics, est_fee_eur, recent_flags` (lists separated by `;`).

**`brief.toml`**: brand, product, goal, target countries and ages, topics, platforms, budget, maximum cost per 1,000 reached, blocked topics and pillar weights. See [`examples/brief.toml`](examples/brief.toml).

All brands and creators in `examples/` are fictional.

## Roadmap

- Pull live creator stats from platform APIs instead of CSV
- Audience overlap between creators, to avoid paying twice for the same people
- A small web UI for non-technical teams

---

Built by [Vishwajeet Kumbhar](https://www.linkedin.com/in/vishwajeetkumbhar379) with Claude Code. MIT licence.
