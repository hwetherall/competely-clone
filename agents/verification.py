import re
from typing import List, Dict, Tuple
from agents.schemas import EvidencePassage

class NumericVerifier:
    """
    Verifies numeric claims against evidence.
    """
    
    # Regex for various number formats
    # Matches: $100, 100%, 1.5M, 2024, 1,000
    NUMBER_PATTERN = r'(?:\$|€|£)?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:[kKmMbBtT]|%)?'
    
    def __init__(self):
        pass

    def extract_numbers(self, text: str) -> List[str]:
        """Extract all numbers/metrics from text."""
        matches = re.findall(self.NUMBER_PATTERN, text)
        # Filter out standalone small integers that might be list indices or general counts
        return [m for m in matches if self._is_significant(m)]

    def _is_significant(self, num_str: str) -> bool:
        """Check if number is significant (not just a small integer)."""
        clean = re.sub(r'[^\d\.]', '', num_str)
        if not clean:
            return False
        try:
            val = float(clean)
            # Keep years, currencies, percentages, and numbers > 10
            if any(c in num_str for c in '$€£%kKmMbBtT'):
                return True
            if val > 1900 and val < 2100: # Years
                return True
            if val > 10 or '.' in num_str:
                return True
            return False
        except ValueError:
            return False

    def verify_numbers(self, text: str, evidence: List[EvidencePassage]) -> List[str]:
        """
        Check if numbers in text are supported by evidence.
        Returns list of unsupported numbers.
        """
        claims_nums = self.extract_numbers(text)
        if not claims_nums:
            return []
            
        evidence_text = " ".join([p.text for p in evidence])
        unsupported = []
        
        for num in claims_nums:
            # Simple exact match check (can be improved with fuzzy matching or LLM)
            # We strip formatting for comparison
            clean_num = re.sub(r'[^\d\.]', '', num)
            
            # Check if the exact string exists
            if num in evidence_text:
                continue
                
            # Check if the value exists (e.g. 1000 vs 1,000)
            if clean_num in evidence_text and len(clean_num) > 1:
                continue
                
            unsupported.append(num)
            
        return unsupported
