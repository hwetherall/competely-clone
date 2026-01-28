import re
from typing import List, Dict
from agents.schemas import EvidencePassage

class PassageSelector:
    """
    Selects relevant passages from text based on keywords and context.
    """
    
    def __init__(self):
        pass

    def select_passages(
        self, 
        text: str, 
        source_id: str, 
        keywords: List[str], 
        company_name: str,
        limit: int = 6,
        window_size: int = 300
    ) -> List[EvidencePassage]:
        """
        Select top N passages from text.
        
        Args:
            text: Full text content
            source_id: ID of the source (e.g., "S1")
            keywords: List of keywords to match
            company_name: Company name to boost relevance
            limit: Max number of passages to return
            window_size: Approximate char length of each passage
            
        Returns:
            List of EvidencePassage objects
        """
        if not text:
            return []
            
        # Split into paragraphs (simple heuristic)
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        
        scored_paragraphs = []
        
        # Normalize terms for matching
        norm_keywords = [k.lower() for k in keywords]
        norm_company = company_name.lower()
        
        for i, para in enumerate(paragraphs):
            score = 0.0
            norm_para = para.lower()
            
            # Score based on keyword presence
            for kw in norm_keywords:
                if kw in norm_para:
                    score += 1.0
                    
            # Boost for company name
            if norm_company in norm_para:
                score += 0.5
                
            # Boost for proximity to beginning (often summary/intro)
            if i < 3:
                score += 0.2
            
            # Penalize very short or very long paragraphs
            if len(para) < 100:
                score -= 0.2
            if len(para) > 2000:
                score -= 0.2
                
            if score > 0:
                scored_paragraphs.append((score, i, para))
        
        # Sort by score descending
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
        
        # Select top N
        selected = []
        for rank, (score, idx, para) in enumerate(scored_paragraphs[:limit]):
            # Truncate if too long
            if len(para) > window_size * 2:
                para = para[:window_size*2] + "..."
                
            selected.append(EvidencePassage(
                source_id=source_id,
                passage_id=f"P{rank+1}",
                text=para,
                relevance_score=score,
                start_offset=0 # Placeholder
            ))
            
        return selected
