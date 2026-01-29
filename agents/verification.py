"""
Numeric verification for evidence-grounded research.

This module provides functions to:
- Extract numbers from text (currency, percentages, large numbers, dates)
- Verify extracted numbers against evidence passages
- Identify unsupported claims
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from agents.schemas import ExtractedNumber, VerificationResult, EvidencePassage

logger = logging.getLogger(__name__)


# =============================================================================
# Number Extraction Patterns
# =============================================================================

# Currency patterns (e.g., $1.4 trillion, €50 million, $2.9%)
CURRENCY_PATTERN = r'\$[\d,]+(?:\.\d+)?(?:\s*(?:trillion|billion|million|thousand|k|m|b|t))?'
CURRENCY_PATTERN_EUR = r'€[\d,]+(?:\.\d+)?(?:\s*(?:trillion|billion|million|thousand|k|m|b|t))?'
CURRENCY_PATTERN_GBP = r'£[\d,]+(?:\.\d+)?(?:\s*(?:trillion|billion|million|thousand|k|m|b|t))?'

# Percentage patterns (e.g., 42%, 2.9%, 14.5 percent)
PERCENTAGE_PATTERN = r'\d+(?:\.\d+)?(?:\s*)?(?:%|percent|percentage)'

# Large numbers with scale words (e.g., 1.4 trillion, 50 million)
LARGE_NUMBER_PATTERN = r'\d+(?:\.\d+)?\s*(?:trillion|billion|million|thousand)'

# Year patterns (e.g., 2024, 2025)
YEAR_PATTERN = r'(?:19|20)\d{2}'

# Specific number patterns (e.g., "3x", "10x", "100+")
MULTIPLIER_PATTERN = r'\d+(?:\.\d+)?x'
COUNT_PATTERN = r'\d{1,3}(?:,\d{3})+|\d+\+'

# Combined pattern for general numbers in context
# Matches numbers that look like statistics (not just any number)
STAT_NUMBER_PATTERN = r'(?:\$|€|£)?[\d,]+(?:\.\d+)?(?:\s*)?(?:%|percent|trillion|billion|million|thousand|x|k|m|b)?'


def extract_numbers(text: str, context_chars: int = 50) -> List[ExtractedNumber]:
    """
    Extract numbers from text that look like statistics or metrics.
    
    Args:
        text: The text to extract numbers from
        context_chars: Number of characters of context to include
        
    Returns:
        List of ExtractedNumber objects
    """
    if not text:
        return []
    
    numbers = []
    seen_values = set()
    
    # Define patterns with their types
    patterns = [
        (CURRENCY_PATTERN, "currency"),
        (CURRENCY_PATTERN_EUR, "currency"),
        (CURRENCY_PATTERN_GBP, "currency"),
        (PERCENTAGE_PATTERN, "percentage"),
        (LARGE_NUMBER_PATTERN, "large_number"),
        (MULTIPLIER_PATTERN, "multiplier"),
    ]
    
    for pattern, number_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(0).strip()
            
            # Skip if we've already seen this exact value
            if value.lower() in seen_values:
                continue
            seen_values.add(value.lower())
            
            # Get context around the match
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end]
            
            numbers.append(ExtractedNumber(
                value=value,
                number_type=number_type,
                context=context,
                position=match.start(),
            ))
    
    # Sort by position in text
    numbers.sort(key=lambda x: x.position)
    
    return numbers


def normalize_number(value: str) -> str:
    """
    Normalize a number string for comparison.
    
    Args:
        value: The number string to normalize
        
    Returns:
        Normalized string for fuzzy matching
    """
    # Remove currency symbols and whitespace
    normalized = value.lower().strip()
    normalized = re.sub(r'[\$€£,\s]', '', normalized)
    
    # Standardize scale words
    normalized = normalized.replace('percent', '%')
    normalized = normalized.replace('trillion', 't')
    normalized = normalized.replace('billion', 'b')
    normalized = normalized.replace('million', 'm')
    normalized = normalized.replace('thousand', 'k')
    
    return normalized


def number_appears_in_text(number: ExtractedNumber, text: str) -> bool:
    """
    Check if a number appears in the given text.
    
    Args:
        number: The ExtractedNumber to look for
        text: The text to search in
        
    Returns:
        True if the number (or a close variant) appears in the text
    """
    if not text:
        return False
    
    # Direct match
    if number.value.lower() in text.lower():
        return True
    
    # Normalized match
    normalized_value = normalize_number(number.value)
    normalized_text = normalize_number(text)
    
    if normalized_value in normalized_text:
        return True
    
    # Try extracting just the numeric part and checking
    numeric_part = re.search(r'[\d.]+', number.value)
    if numeric_part:
        numeric_str = numeric_part.group(0)
        # Check if this numeric value appears with similar context
        if numeric_str in text:
            return True
    
    return False


def verify_numbers_against_evidence(
    numbers: List[ExtractedNumber],
    passages: List[EvidencePassage],
) -> Tuple[List[VerificationResult], List[ExtractedNumber]]:
    """
    Verify extracted numbers against evidence passages.
    
    Args:
        numbers: List of extracted numbers to verify
        passages: List of evidence passages to check against
        
    Returns:
        Tuple of (all verification results, unsupported numbers only)
    """
    results = []
    unsupported = []
    
    # Combine all passage text for easier searching
    passage_texts = {p.passage_id: p.text for p in passages}
    
    for number in numbers:
        supporting_passages = []
        
        # Check each passage for this number
        for passage in passages:
            if number_appears_in_text(number, passage.text):
                supporting_passages.append(passage.passage_id)
        
        is_supported = len(supporting_passages) > 0
        
        # Determine confidence based on support
        if is_supported and len(supporting_passages) >= 2:
            confidence = "high"
        elif is_supported:
            confidence = "medium"
        else:
            confidence = "low"
        
        result = VerificationResult(
            number=number,
            is_supported=is_supported,
            supporting_passages=supporting_passages,
            confidence=confidence,
        )
        results.append(result)
        
        if not is_supported:
            unsupported.append(number)
    
    return results, unsupported


def get_verification_summary(results: List[VerificationResult]) -> dict:
    """
    Get a summary of verification results.
    
    Args:
        results: List of VerificationResult objects
        
    Returns:
        Summary dictionary with counts and statistics
    """
    total = len(results)
    supported = sum(1 for r in results if r.is_supported)
    unsupported = total - supported
    
    high_confidence = sum(1 for r in results if r.confidence == "high")
    medium_confidence = sum(1 for r in results if r.confidence == "medium")
    low_confidence = sum(1 for r in results if r.confidence == "low")
    
    return {
        "total_numbers": total,
        "supported": supported,
        "unsupported": unsupported,
        "support_rate": supported / total if total > 0 else 1.0,
        "high_confidence": high_confidence,
        "medium_confidence": medium_confidence,
        "low_confidence": low_confidence,
    }


def should_reduce_confidence(
    verification_results: List[VerificationResult],
    unsupported_threshold: int = 3,
    unsupported_ratio_threshold: float = 0.3,
) -> bool:
    """
    Determine if confidence should be reduced based on verification.
    
    Args:
        verification_results: List of verification results
        unsupported_threshold: Number of unsupported numbers that triggers reduction
        unsupported_ratio_threshold: Ratio of unsupported that triggers reduction
        
    Returns:
        True if confidence should be reduced
    """
    if not verification_results:
        return False
    
    summary = get_verification_summary(verification_results)
    
    # Reduce if too many unsupported numbers
    if summary["unsupported"] >= unsupported_threshold:
        return True
    
    # Reduce if high ratio of unsupported
    if summary["support_rate"] < (1 - unsupported_ratio_threshold):
        return True
    
    return False


def format_unsupported_for_fix(unsupported: List[ExtractedNumber]) -> str:
    """
    Format unsupported numbers for the fix prompt.
    
    Args:
        unsupported: List of unsupported ExtractedNumber objects
        
    Returns:
        Formatted string for the LLM fix prompt
    """
    lines = []
    for num in unsupported:
        lines.append(f"- {num.value}")
        if num.context:
            # Show truncated context
            context = num.context[:100] + "..." if len(num.context) > 100 else num.context
            lines.append(f"  Context: \"{context}\"")
    return "\n".join(lines)
