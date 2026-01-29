"""
Unit tests for source_scoring module.
"""

import pytest
from agents.source_scoring import (
    score_url,
    extract_domain,
    extract_base_domain,
    is_official_domain,
    get_freshness_boost,
    rank_urls,
    filter_by_min_score,
)


class TestExtractDomain:
    """Tests for domain extraction."""
    
    def test_simple_domain(self):
        assert extract_domain("https://stripe.com/pricing") == "stripe.com"
    
    def test_www_prefix_removed(self):
        assert extract_domain("https://www.stripe.com/pricing") == "stripe.com"
    
    def test_subdomain_preserved(self):
        assert extract_domain("https://docs.stripe.com/api") == "docs.stripe.com"
    
    def test_empty_url(self):
        assert extract_domain("") == ""
    
    def test_invalid_url(self):
        assert extract_domain("not-a-url") == ""


class TestExtractBaseDomain:
    """Tests for base domain extraction."""
    
    def test_simple_domain(self):
        assert extract_base_domain("stripe.com") == "stripe.com"
    
    def test_subdomain(self):
        assert extract_base_domain("docs.stripe.com") == "stripe.com"
    
    def test_multiple_subdomains(self):
        assert extract_base_domain("api.docs.stripe.com") == "stripe.com"
    
    def test_country_tld(self):
        assert extract_base_domain("stripe.co.uk") == "stripe.co.uk"


class TestIsOfficialDomain:
    """Tests for official domain detection."""
    
    def test_official_stripe(self):
        assert is_official_domain("https://stripe.com/pricing", "Stripe") is True
    
    def test_official_subdomain(self):
        assert is_official_domain("https://docs.stripe.com/api", "Stripe") is True
    
    def test_not_official(self):
        assert is_official_domain("https://reddit.com/r/stripe", "Stripe") is False
    
    def test_case_insensitive(self):
        assert is_official_domain("https://STRIPE.com/pricing", "stripe") is True
    
    def test_company_with_spaces(self):
        assert is_official_domain("https://paypal.com/", "Pay Pal") is True


class TestGetFreshnessBoost:
    """Tests for freshness boost calculation."""
    
    def test_current_year_boost(self):
        boost = get_freshness_boost("https://example.com/2026/article")
        assert boost == 0.1
    
    def test_previous_year_boost(self):
        boost = get_freshness_boost("https://example.com/2025/article")
        assert boost == 0.05
    
    def test_older_year_boost(self):
        boost = get_freshness_boost("https://example.com/2024/article")
        assert boost == 0.02
    
    def test_no_year_no_boost(self):
        boost = get_freshness_boost("https://example.com/article")
        assert boost == 0.0


class TestScoreUrl:
    """Tests for URL scoring."""
    
    def test_official_domain_high_score(self):
        score = score_url("https://stripe.com/pricing", "Stripe")
        assert score.score >= 0.85
        assert score.is_official is True
        assert score.tier == "official"
    
    def test_regulatory_domain_high_score(self):
        score = score_url("https://sec.gov/cgi-bin/browse-edgar", "")
        assert score.score >= 0.9
        assert score.tier == "regulatory"
    
    def test_tier1_news_good_score(self):
        score = score_url("https://techcrunch.com/2024/01/stripe-news", "")
        assert score.score >= 0.7
        assert score.tier == "tier1_news"
    
    def test_reddit_low_score(self):
        score = score_url("https://reddit.com/r/stripe/comments/abc", "Stripe")
        assert score.score <= 0.4
        assert score.tier == "low_quality"
        assert "low_quality_domain" in score.penalties[0]
    
    def test_generic_domain_medium_score(self):
        score = score_url("https://example-blog.com/stripe-review", "Stripe")
        assert 0.3 <= score.score <= 0.7
        assert score.tier == "general"
    
    def test_freshness_boost_applied(self):
        score_old = score_url("https://example.com/article", "")
        score_new = score_url("https://example.com/2026/article", "")
        assert score_new.score > score_old.score
        assert score_new.freshness_boost > 0


class TestRankUrls:
    """Tests for URL ranking with diversity."""
    
    def test_rank_by_score(self):
        urls = [
            "https://reddit.com/r/stripe",
            "https://stripe.com/pricing",
            "https://techcrunch.com/stripe",
        ]
        ranked = rank_urls(urls, company="Stripe", ensure_diversity=False)
        
        # Official should be first
        assert "stripe.com" in ranked[0][0]
    
    def test_diversity_enforcement(self):
        urls = [
            "https://stripe.com/pricing",
            "https://stripe.com/features",
            "https://stripe.com/docs",
            "https://techcrunch.com/stripe",
            "https://reddit.com/r/stripe",
        ]
        ranked = rank_urls(urls, company="Stripe", ensure_diversity=True, min_domains=3)
        
        # Should have at least 3 different domains
        domains = set(r[1].domain for r in ranked[:5])
        assert len(domains) >= 3


class TestFilterByMinScore:
    """Tests for score filtering."""
    
    def test_filter_removes_low_scores(self):
        urls = [
            "https://stripe.com/pricing",  # High score
            "https://reddit.com/r/stripe",  # Low score
        ]
        filtered = filter_by_min_score(urls, min_score=0.5, company="Stripe")
        
        assert len(filtered) == 1
        assert "stripe.com" in filtered[0][0]
    
    def test_filter_keeps_all_above_threshold(self):
        urls = [
            "https://stripe.com/pricing",
            "https://techcrunch.com/stripe",
        ]
        filtered = filter_by_min_score(urls, min_score=0.5, company="Stripe")
        
        assert len(filtered) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
