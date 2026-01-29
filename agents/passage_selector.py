"""
Passage selection for evidence-grounded research.

This module provides heuristic-based passage selection from page text,
with optional LLM-based selection for difficult cases.
"""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

from agents.schemas import EvidencePassage

logger = logging.getLogger(__name__)


# Minimum paragraph length to consider
MIN_PARAGRAPH_LENGTH = 50

# Maximum paragraph length before splitting
MAX_PARAGRAPH_LENGTH = 1000

# Context window size (characters) around a paragraph
CONTEXT_WINDOW = 100


@dataclass
class ScoredParagraph:
    """A paragraph with relevance score."""
    text: str
    score: float
    start_offset: int
    keyword_hits: int
    company_hits: int


def split_into_paragraphs(text: str) -> List[Tuple[str, int]]:
    """
    Split text into paragraphs.
    
    Args:
        text: The text to split
        
    Returns:
        List of (paragraph_text, start_offset) tuples
    """
    # Split on double newlines or multiple newlines
    paragraphs = []
    current_pos = 0
    
    # Split on paragraph boundaries
    parts = re.split(r'\n\s*\n', text)
    
    for part in parts:
        part = part.strip()
        if len(part) >= MIN_PARAGRAPH_LENGTH:
            # Find actual position in original text
            pos = text.find(part, current_pos)
            if pos == -1:
                pos = current_pos
            
            # Split very long paragraphs
            if len(part) > MAX_PARAGRAPH_LENGTH:
                # Split on sentence boundaries
                sentences = re.split(r'(?<=[.!?])\s+', part)
                chunk = ""
                chunk_start = pos
                
                for sentence in sentences:
                    if len(chunk) + len(sentence) > MAX_PARAGRAPH_LENGTH:
                        if chunk:
                            paragraphs.append((chunk.strip(), chunk_start))
                        chunk = sentence
                        chunk_start = pos + part.find(sentence)
                    else:
                        chunk += " " + sentence if chunk else sentence
                
                if chunk:
                    paragraphs.append((chunk.strip(), chunk_start))
            else:
                paragraphs.append((part, pos))
            
            current_pos = pos + len(part)
    
    return paragraphs


def count_keyword_hits(text: str, keywords: List[str]) -> int:
    """
    Count keyword occurrences in text.
    
    Args:
        text: The text to search
        keywords: List of keywords to find
        
    Returns:
        Total count of keyword hits
    """
    text_lower = text.lower()
    count = 0
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        matches = re.findall(pattern, text_lower)
        count += len(matches)
    
    return count


def count_company_hits(text: str, company: str) -> int:
    """
    Count company name occurrences in text.
    
    Args:
        text: The text to search
        company: Company name to find
        
    Returns:
        Count of company name mentions
    """
    text_lower = text.lower()
    company_lower = company.lower()
    
    # Exact match
    pattern = r'\b' + re.escape(company_lower) + r'\b'
    exact_matches = len(re.findall(pattern, text_lower))
    
    # Also check for possessive form
    possessive_pattern = r'\b' + re.escape(company_lower) + r"'s\b"
    possessive_matches = len(re.findall(possessive_pattern, text_lower))
    
    return exact_matches + possessive_matches


def score_paragraph(
    paragraph: str,
    keywords: List[str],
    company: str,
    position_weight: float = 0.1,
    position_index: int = 0,
    total_paragraphs: int = 1,
) -> ScoredParagraph:
    """
    Score a paragraph for relevance.
    
    Args:
        paragraph: The paragraph text
        keywords: List of keywords to match
        company: Company name
        position_weight: How much to weight position (earlier = better)
        position_index: Index of this paragraph in the document
        total_paragraphs: Total number of paragraphs
        
    Returns:
        ScoredParagraph with relevance score
    """
    keyword_hits = count_keyword_hits(paragraph, keywords)
    company_hits = count_company_hits(paragraph, company)
    
    # Base score from keyword and company hits
    keyword_score = min(keyword_hits * 0.2, 1.0)  # Cap at 1.0
    company_score = min(company_hits * 0.3, 0.6)  # Cap at 0.6
    
    # Position score (earlier paragraphs get slight boost)
    if total_paragraphs > 1:
        position_score = position_weight * (1 - position_index / total_paragraphs)
    else:
        position_score = position_weight
    
    # Length bonus (prefer substantial paragraphs)
    length_score = min(len(paragraph) / 500, 0.2)  # Cap at 0.2
    
    # Penalty for boilerplate patterns
    boilerplate_penalty = 0.0
    boilerplate_patterns = [
        r'cookie',
        r'privacy policy',
        r'terms of service',
        r'subscribe',
        r'sign up',
        r'newsletter',
        r'copyright',
        r'all rights reserved',
    ]
    for pattern in boilerplate_patterns:
        if re.search(pattern, paragraph.lower()):
            boilerplate_penalty += 0.1
    boilerplate_penalty = min(boilerplate_penalty, 0.5)
    
    # Calculate total score
    total_score = keyword_score + company_score + position_score + length_score - boilerplate_penalty
    total_score = max(0.0, min(1.0, total_score))  # Clamp to [0, 1]
    
    return ScoredParagraph(
        text=paragraph,
        score=total_score,
        start_offset=0,  # Will be set by caller
        keyword_hits=keyword_hits,
        company_hits=company_hits,
    )


def select_passages(
    text: str,
    keywords: List[str],
    company: str,
    max_passages: int = 6,
    min_score: float = 0.1,
) -> List[EvidencePassage]:
    """
    Select the most relevant passages from text.
    
    Args:
        text: The full text to extract passages from
        keywords: Keywords to use for relevance scoring
        company: Company name for relevance scoring
        max_passages: Maximum number of passages to return
        min_score: Minimum score threshold
        
    Returns:
        List of EvidencePassage objects
    """
    if not text or not text.strip():
        return []
    
    # Split into paragraphs
    paragraphs = split_into_paragraphs(text)
    
    if not paragraphs:
        return []
    
    # Score each paragraph
    scored = []
    for i, (para_text, start_offset) in enumerate(paragraphs):
        scored_para = score_paragraph(
            paragraph=para_text,
            keywords=keywords,
            company=company,
            position_index=i,
            total_paragraphs=len(paragraphs),
        )
        scored_para.start_offset = start_offset
        scored.append(scored_para)
    
    # Sort by score descending
    scored.sort(key=lambda x: -x.score)
    
    # Filter by minimum score and take top N
    selected = [p for p in scored if p.score >= min_score][:max_passages]
    
    # Convert to EvidencePassage objects
    passages = []
    for i, para in enumerate(selected):
        passage = EvidencePassage(
            source_id="",  # Will be set by caller
            passage_id=f"P{i + 1}",
            text=para.text,
            start_offset=para.start_offset,
            relevance_score=para.score,
        )
        passages.append(passage)
    
    return passages


def select_passages_for_variable(
    text: str,
    company: str,
    key_terms: List[str],
    answer_spec: List[str],
    max_passages: int = 6,
) -> List[EvidencePassage]:
    """
    Select passages optimized for a specific variable.
    
    Args:
        text: The full text to extract passages from
        company: Company name
        key_terms: Variable-specific key terms
        answer_spec: What must be answered for this variable
        max_passages: Maximum passages to return
        
    Returns:
        List of EvidencePassage objects
    """
    # Combine key terms and answer spec for keyword matching
    keywords = list(key_terms) + list(answer_spec)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)
    
    return select_passages(
        text=text,
        keywords=unique_keywords,
        company=company,
        max_passages=max_passages,
    )


def merge_passages(
    passages: List[EvidencePassage],
    max_total_chars: int = 12000,
) -> List[EvidencePassage]:
    """
    Merge passages to fit within character limit.
    
    Args:
        passages: List of passages to merge
        max_total_chars: Maximum total characters
        
    Returns:
        List of passages within the limit
    """
    if not passages:
        return []
    
    total_chars = 0
    selected = []
    
    for passage in passages:
        passage_chars = len(passage.text)
        if total_chars + passage_chars <= max_total_chars:
            selected.append(passage)
            total_chars += passage_chars
        else:
            # Try to fit a truncated version
            remaining = max_total_chars - total_chars
            if remaining > 200:  # Only include if we can fit meaningful content
                truncated = EvidencePassage(
                    source_id=passage.source_id,
                    passage_id=passage.passage_id,
                    text=passage.text[:remaining - 3] + "...",
                    start_offset=passage.start_offset,
                    relevance_score=passage.relevance_score,
                )
                selected.append(truncated)
            break
    
    return selected


def get_passage_context(
    text: str,
    passage: EvidencePassage,
    context_chars: int = CONTEXT_WINDOW,
) -> str:
    """
    Get a passage with surrounding context.
    
    Args:
        text: The full text
        passage: The passage to get context for
        context_chars: Characters of context on each side
        
    Returns:
        Passage text with context
    """
    if passage.start_offset is None:
        return passage.text
    
    start = max(0, passage.start_offset - context_chars)
    end = min(len(text), passage.start_offset + len(passage.text) + context_chars)
    
    context_text = text[start:end]
    
    # Add ellipsis if truncated
    if start > 0:
        context_text = "..." + context_text
    if end < len(text):
        context_text = context_text + "..."
    
    return context_text
