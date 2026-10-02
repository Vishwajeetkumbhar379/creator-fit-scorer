from types import SimpleNamespace

from creator_fit.llm import review
from creator_fit.scoring import Brief, Creator, rank, score_creator, tier_for

BRIEF = Brief.from_dict(
    {
        "brand": "Test",
        "product": "Serum",
        "goal": "Sales",
        "target_countries": ["DE"],
        "target_ages": ["25-34"],
        "topics": ["skincare", "beauty"],
        "platforms": ["instagram"],
        "budget_eur": 10000,
        "max_cpm_eur": 40,
        "blocked_topics": ["crypto"],
    }
)


def make(**kw):
    base = dict(
        handle="@a", platform="instagram", followers=40000, avg_reach=20000, engagement_rate=4.0,
        audience_country="DE", audience_age="25-34", topics=["skincare", "beauty"], est_fee_eur=500,
    )
    base.update(kw)
    return Creator(**base)


def test_tiers():
    assert tier_for(5_000)[0] == "nano"
    assert tier_for(40_000)[0] == "micro"
    assert tier_for(2_000_000)[0] == "mega"


def test_perfect_fit_is_shortlisted():
    s = score_creator(make(), BRIEF)
    assert s.total >= 90
    assert s.verdict == "shortlist"


def test_blocked_topic_is_rejected():
    s = score_creator(make(topics=["skincare", "crypto"]), BRIEF)
    assert s.verdict == "reject"


def test_suspicious_engagement_is_flagged():
    s = score_creator(make(engagement_rate=15.0), BRIEF)
    assert any("pods" in r for r in s.risks)


def test_wrong_market_scores_lower():
    good = score_creator(make(), BRIEF).total
    bad = score_creator(make(audience_country="US"), BRIEF).total
    assert bad < good


def test_rank_orders_by_verdict_then_score():
    ranked = rank([make(handle="@x", topics=["crypto"]), make(handle="@y")], BRIEF)
    assert [s.creator.handle for s in ranked] == ["@y", "@x"]


def test_ai_review_uses_structured_tool_output():
    block = SimpleNamespace(type="tool_use", input={
        "fit_summary": "Fits.", "adjustment": 40, "content_angle": "GRWM", "outreach_message": "Hi!"
    })
    fake = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(content=[block])))
    out = review(score_creator(make(), BRIEF), BRIEF, client=fake)
    assert out["adjustment"] == 15  # clamped
