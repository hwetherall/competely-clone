"""
Unit tests for verification module.
"""

import pytest
from agents.verification import (
    extract_numbers,
    normalize_number,
    number_appears_in_text,
    verify_numbers_against_evidence,
    get_verification_summary,
    should_reduce_confidence,
)
from agents.schemas import ExtractedNumber, EvidencePassage


class TestExtractNumbers:
    """Tests for number extraction."""
    
    def test_extract_currency_dollar(self):
        text = "Stripe processed $1.4 trillion in payments."
        numbers = extract_numbers(text)
        
        assert len(numbers) >= 1
        assert any("$1.4 trillion" in n.value for n in numbers)
    
    def test_extract_percentage(self):
        text = "This resulted in a 42% reduction in fraud."
        numbers = extract_numbers(text)
        
        assert len(numbers) >= 1
        assert any("42%" in n.value for n in numbers)
    
    def test_extract_large_number(self):
        text = "The company serves 50 million customers worldwide."
        numbers = extract_numbers(text)
        
        assert len(numbers) >= 1
        assert any("50 million" in n.value for n in numbers)
    
    def test_extract_multiple_numbers(self):
        text = "Revenue grew by 38% to $14 billion, with 42% profit margin."
        numbers = extract_numbers(text)
        
        assert len(numbers) >= 3
    
    def test_extract_decimal_percentage(self):
        text = "Transaction fee is 2.9% + $0.30."
        numbers = extract_numbers(text)
        
        assert any("2.9%" in n.value for n in numbers)
    
    def test_no_numbers(self):
        text = "Stripe is a payment processing company."
        numbers = extract_numbers(text)
        
        # Should not extract plain words
        assert len(numbers) == 0
    
    def test_context_captured(self):
        text = "In 2024, Stripe processed $1.4 trillion in transaction volume."
        numbers = extract_numbers(text, context_chars=30)
        
        assert len(numbers) >= 1
        # Context should include surrounding text
        assert any("trillion" in n.context.lower() for n in numbers)


class TestNormalizeNumber:
    """Tests for number normalization."""
    
    def test_normalize_currency(self):
        assert normalize_number("$1.4 trillion") == "1.4t"
    
    def test_normalize_percentage(self):
        assert normalize_number("42 percent") == "42%"
    
    def test_normalize_billion(self):
        assert normalize_number("$14 billion") == "14b"
    
    def test_normalize_removes_commas(self):
        assert "," not in normalize_number("$1,400,000")


class TestNumberAppearsInText:
    """Tests for number matching in text."""
    
    def test_exact_match(self):
        number = ExtractedNumber(value="$1.4 trillion", number_type="currency", context="", position=0)
        text = "Stripe processed $1.4 trillion in payments."
        
        assert number_appears_in_text(number, text) is True
    
    def test_case_insensitive(self):
        number = ExtractedNumber(value="$1.4 TRILLION", number_type="currency", context="", position=0)
        text = "Stripe processed $1.4 trillion in payments."
        
        assert number_appears_in_text(number, text) is True
    
    def test_not_present(self):
        number = ExtractedNumber(value="$2.5 billion", number_type="currency", context="", position=0)
        text = "Stripe processed $1.4 trillion in payments."
        
        assert number_appears_in_text(number, text) is False
    
    def test_normalized_match(self):
        number = ExtractedNumber(value="42%", number_type="percentage", context="", position=0)
        text = "This resulted in a 42 percent reduction."
        
        assert number_appears_in_text(number, text) is True


class TestVerifyNumbersAgainstEvidence:
    """Tests for verification against evidence."""
    
    def test_supported_number(self):
        numbers = [
            ExtractedNumber(value="$1.4 trillion", number_type="currency", context="", position=0)
        ]
        passages = [
            EvidencePassage(source_id="S1", passage_id="P1", text="Stripe processed $1.4 trillion in 2024.")
        ]
        
        results, unsupported = verify_numbers_against_evidence(numbers, passages)
        
        assert len(results) == 1
        assert results[0].is_supported is True
        assert len(unsupported) == 0
    
    def test_unsupported_number(self):
        numbers = [
            ExtractedNumber(value="$5 billion", number_type="currency", context="", position=0)
        ]
        passages = [
            EvidencePassage(source_id="S1", passage_id="P1", text="Stripe processed $1.4 trillion in 2024.")
        ]
        
        results, unsupported = verify_numbers_against_evidence(numbers, passages)
        
        assert len(results) == 1
        assert results[0].is_supported is False
        assert len(unsupported) == 1
    
    def test_mixed_support(self):
        numbers = [
            ExtractedNumber(value="$1.4 trillion", number_type="currency", context="", position=0),
            ExtractedNumber(value="42%", number_type="percentage", context="", position=50),
        ]
        passages = [
            EvidencePassage(source_id="S1", passage_id="P1", text="Stripe processed $1.4 trillion in 2024.")
        ]
        
        results, unsupported = verify_numbers_against_evidence(numbers, passages)
        
        assert len(unsupported) == 1
        assert unsupported[0].value == "42%"
    
    def test_multiple_passage_support(self):
        numbers = [
            ExtractedNumber(value="$1.4 trillion", number_type="currency", context="", position=0)
        ]
        passages = [
            EvidencePassage(source_id="S1", passage_id="P1", text="Stripe processed $1.4 trillion."),
            EvidencePassage(source_id="S2", passage_id="P2", text="Volume reached $1.4 trillion in 2024."),
        ]
        
        results, unsupported = verify_numbers_against_evidence(numbers, passages)
        
        assert results[0].is_supported is True
        assert len(results[0].supporting_passages) == 2
        assert results[0].confidence == "high"


class TestGetVerificationSummary:
    """Tests for verification summary."""
    
    def test_all_supported(self):
        from agents.schemas import VerificationResult
        
        number = ExtractedNumber(value="42%", number_type="percentage", context="", position=0)
        results = [
            VerificationResult(number=number, is_supported=True, supporting_passages=["P1"], confidence="high")
        ]
        
        summary = get_verification_summary(results)
        
        assert summary["total_numbers"] == 1
        assert summary["supported"] == 1
        assert summary["unsupported"] == 0
        assert summary["support_rate"] == 1.0
    
    def test_mixed_support(self):
        from agents.schemas import VerificationResult
        
        num1 = ExtractedNumber(value="42%", number_type="percentage", context="", position=0)
        num2 = ExtractedNumber(value="$5B", number_type="currency", context="", position=0)
        
        results = [
            VerificationResult(number=num1, is_supported=True, supporting_passages=["P1"], confidence="high"),
            VerificationResult(number=num2, is_supported=False, supporting_passages=[], confidence="low"),
        ]
        
        summary = get_verification_summary(results)
        
        assert summary["total_numbers"] == 2
        assert summary["supported"] == 1
        assert summary["unsupported"] == 1
        assert summary["support_rate"] == 0.5


class TestShouldReduceConfidence:
    """Tests for confidence reduction logic."""
    
    def test_many_unsupported_reduces(self):
        from agents.schemas import VerificationResult
        
        results = []
        for i in range(5):
            num = ExtractedNumber(value=f"${i}B", number_type="currency", context="", position=0)
            results.append(VerificationResult(
                number=num,
                is_supported=False,
                supporting_passages=[],
                confidence="low"
            ))
        
        assert should_reduce_confidence(results, unsupported_threshold=3) is True
    
    def test_few_unsupported_ok(self):
        from agents.schemas import VerificationResult
        
        # With 4 supported and 1 unsupported (80% support rate), should be OK
        results = []
        for i in range(4):
            num = ExtractedNumber(value=f"${i}B", number_type="currency", context="", position=0)
            results.append(VerificationResult(
                number=num, is_supported=True, supporting_passages=["P1"], confidence="high"
            ))
        # Add one unsupported
        num_unsupported = ExtractedNumber(value="42%", number_type="percentage", context="", position=0)
        results.append(VerificationResult(
            number=num_unsupported, is_supported=False, supporting_passages=[], confidence="low"
        ))
        
        # 1 unsupported out of 5 = 80% support rate, above the 70% threshold
        # And only 1 unsupported, below threshold of 3
        assert should_reduce_confidence(results, unsupported_threshold=3) is False
    
    def test_empty_results_ok(self):
        assert should_reduce_confidence([], unsupported_threshold=3) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
