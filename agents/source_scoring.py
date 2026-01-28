import re
from urllib.parse import urlparse

class SourceScorer:
    """
    Scores URLs based on domain reputation and relevance.
    """
    
    # High authority domains
    OFFICIAL_DOMAINS = {
        "sec.gov", "investor.gov", "gov.uk", "usa.gov", 
        "europa.eu", "worldbank.org", "imf.org"
    }
    
    # Reputable news and research
    TIER1_DOMAINS = {
        "bloomberg.com", "reuters.com", "wsj.com", "ft.com", 
        "nytimes.com", "forbes.com", "techcrunch.com", 
        "venturebeat.com", "gartner.com", "forrester.com",
        "mckinsey.com", "bcg.com", "bain.com", "deloitte.com",
        "pwc.com", "ey.com", "kpmg.com", "statista.com",
        "crunchbase.com", "pitchbook.com", "cbinsights.com"
    }
    
    # Low quality / UGC domains to penalize
    LOW_QUALITY_DOMAINS = {
        "reddit.com", "quora.com", "teamblind.com", 
        "glassdoor.com", "g2.com", "capterra.com", 
        "trustpilot.com", "medium.com", "linkedin.com",
        "facebook.com", "twitter.com", "instagram.com",
        "pinterest.com", "youtube.com", "tiktok.com"
    }

    @classmethod
    def score_url(cls, url: str, company_name: str = "") -> float:
        """
        Calculate a quality score for a URL [0.0 - 1.0].
        
        Args:
            url: The URL to score
            company_name: Optional company name to check for official domains
            
        Returns:
            Float score between 0.0 and 1.0
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            
            score = 0.5  # Base score
            
            # Check for official company domain
            if company_name:
                clean_company = re.sub(r'[^a-z0-9]', '', company_name.lower())
                if clean_company in domain or domain in f"{clean_company}.com":
                    # Boost for likely official site
                    if "investor" in domain or "ir." in domain:
                        return 0.95  # Investor relations
                    if "blog" in domain or "news" in domain:
                        return 0.85  # Official blog
                    return 0.90  # Main site
            
            # Check domain lists
            if domain in cls.OFFICIAL_DOMAINS or domain.endswith(".gov"):
                return 0.95
            
            if domain in cls.TIER1_DOMAINS:
                return 0.85
                
            if domain in cls.LOW_QUALITY_DOMAINS:
                return 0.30
            
            # Freshness boost (heuristic based on URL structure)
            if "/2025/" in url or "-2025" in url:
                score += 0.1
            elif "/2024/" in url or "-2024" in url:
                score += 0.05
            elif "/2023/" in url or "-2023" in url:
                score -= 0.05
            elif "/2022/" in url or "-2022" in url:
                score -= 0.1
            elif re.search(r'/20[0-1][0-9]/', url):  # 2000-2019
                score -= 0.2
                
            # Penalize very long URLs (often SEO spam)
            if len(url) > 150:
                score -= 0.1
                
            # Clamp score
            return max(0.1, min(0.99, score))
            
        except Exception:
            return 0.5
