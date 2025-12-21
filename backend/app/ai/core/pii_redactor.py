"""
AI Tutor Platform - PII Redactor
Microsoft Presidio integration for detecting and anonymizing personally identifiable information.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Try to import Presidio, gracefully handle if not installed
try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None
    AnonymizerEngine = None


class PIIEntityType(str, Enum):
    """Types of PII entities we detect."""
    PERSON = "PERSON"
    EMAIL = "EMAIL_ADDRESS"
    PHONE = "PHONE_NUMBER"
    LOCATION = "LOCATION"
    DATE_TIME = "DATE_TIME"
    # India-specific
    AADHAAR = "IN_AADHAAR"
    PAN = "IN_PAN"
    # Education-specific
    ROLL_NUMBER = "ROLL_NUMBER"
    SCHOOL_NAME = "SCHOOL_NAME"


@dataclass
class PIIDetection:
    """A detected PII entity."""
    entity_type: str
    text: str
    start: int
    end: int
    score: float


@dataclass
class RedactionResult:
    """Result of PII redaction."""
    original_text: str
    redacted_text: str
    detections: List[PIIDetection] = field(default_factory=list)
    has_pii: bool = False

    @property
    def detection_summary(self) -> Dict[str, int]:
        """Summary of detected PII by type."""
        summary = {}
        for detection in self.detections:
            summary[detection.entity_type] = summary.get(detection.entity_type, 0) + 1
        return summary


class PIIRedactor:
    """
    PII detection and anonymization using Microsoft Presidio.
    
    Includes custom recognizers for:
    - India-specific: Aadhaar, PAN
    - Education-specific: Roll numbers, School names
    """
    
    # Fallback regex patterns when Presidio is not available
    FALLBACK_PATTERNS = {
        "EMAIL_ADDRESS": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "PHONE_NUMBER": r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "IN_AADHAAR": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "IN_PAN": r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "ROLL_NUMBER": r"\b(?:Roll\s*(?:No\.?|Number)?:?\s*)\d{1,10}\b",
    }
    
    def __init__(self, 
                 entities_to_detect: Optional[List[str]] = None,
                 use_presidio: bool = True):
        """
        Initialize the PII Redactor.
        
        Args:
            entities_to_detect: List of entity types to detect. If None, detects all.
            use_presidio: Whether to use Presidio (falls back to regex if unavailable).
        """
        self.use_presidio = use_presidio and PRESIDIO_AVAILABLE
        
        # Default entities to detect
        self.entities = entities_to_detect or [
            "PERSON",
            "EMAIL_ADDRESS", 
            "PHONE_NUMBER",
            "LOCATION",
            "IN_AADHAAR",
            "IN_PAN",
            "ROLL_NUMBER",
        ]
        
        if self.use_presidio:
            self._init_presidio()
        else:
            self._init_fallback()
    
    def _init_presidio(self):
        """Initialize Presidio analyzer and anonymizer."""
        # Create custom recognizers for India-specific PII
        custom_recognizers = self._create_custom_recognizers()
        
        # Initialize analyzer with custom recognizers
        self.analyzer = AnalyzerEngine()
        for recognizer in custom_recognizers:
            self.analyzer.registry.add_recognizer(recognizer)
        
        # Initialize anonymizer
        self.anonymizer = AnonymizerEngine()
    
    def _create_custom_recognizers(self) -> List:
        """Create custom pattern recognizers for India and education context."""
        recognizers = []
        
        # Aadhaar Number (12-digit Indian ID)
        aadhaar_pattern = Pattern(
            name="aadhaar_pattern",
            regex=r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            score=0.85
        )
        recognizers.append(PatternRecognizer(
            supported_entity="IN_AADHAAR",
            patterns=[aadhaar_pattern],
            context=["aadhaar", "aadhar", "uid", "uidai"]
        ))
        
        # PAN Card (AAAAA0000A format)
        pan_pattern = Pattern(
            name="pan_pattern",
            regex=r"\b[A-Z]{5}\d{4}[A-Z]\b",
            score=0.9
        )
        recognizers.append(PatternRecognizer(
            supported_entity="IN_PAN",
            patterns=[pan_pattern],
            context=["pan", "permanent account number", "income tax"]
        ))
        
        # Roll Number
        roll_pattern = Pattern(
            name="roll_number_pattern",
            regex=r"\b(?:Roll\s*(?:No\.?|Number)?:?\s*)\d{1,10}\b",
            score=0.7
        )
        recognizers.append(PatternRecognizer(
            supported_entity="ROLL_NUMBER",
            patterns=[roll_pattern],
            context=["roll", "student", "exam", "admission"]
        ))
        
        return recognizers
    
    def _init_fallback(self):
        """Initialize fallback regex-based detection."""
        self.analyzer = None
        self.anonymizer = None
    
    def detect(self, text: str, language: str = "en") -> List[PIIDetection]:
        """
        Detect PII entities in text.
        
        Args:
            text: Text to analyze
            language: Language code (default: "en")
            
        Returns:
            List of detected PII entities
        """
        if not text or not text.strip():
            return []
        
        if self.use_presidio:
            return self._detect_presidio(text, language)
        else:
            return self._detect_fallback(text)
    
    def _detect_presidio(self, text: str, language: str) -> List[PIIDetection]:
        """Detect PII using Presidio."""
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language=language
        )
        
        return [
            PIIDetection(
                entity_type=r.entity_type,
                text=text[r.start:r.end],
                start=r.start,
                end=r.end,
                score=r.score
            )
            for r in results
        ]
    
    def _detect_fallback(self, text: str) -> List[PIIDetection]:
        """Detect PII using fallback regex patterns."""
        detections = []
        
        for entity_type, pattern in self.FALLBACK_PATTERNS.items():
            if entity_type in self.entities or entity_type.split("_")[-1] in self.entities:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    detections.append(PIIDetection(
                        entity_type=entity_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        score=0.8
                    ))
        
        return detections
    
    def redact(self, 
               text: str, 
               language: str = "en",
               replacement_strategy: str = "type_placeholder") -> RedactionResult:
        """
        Detect and redact PII from text.
        
        Args:
            text: Text to redact
            language: Language code
            replacement_strategy: How to replace PII:
                - "type_placeholder": Replace with <ENTITY_TYPE>
                - "masked": Replace with asterisks
                - "numbered": Replace with <ENTITY_TYPE_1>, <ENTITY_TYPE_2>
                
        Returns:
            RedactionResult with original and redacted text
        """
        if not text or not text.strip():
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                has_pii=False
            )
        
        # Detect PII
        detections = self.detect(text, language)
        
        if not detections:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                has_pii=False
            )
        
        # Redact based on strategy
        if self.use_presidio:
            redacted_text = self._redact_presidio(text, detections, replacement_strategy)
        else:
            redacted_text = self._redact_fallback(text, detections, replacement_strategy)
        
        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            detections=detections,
            has_pii=True
        )
    
    def _redact_presidio(self, 
                         text: str, 
                         detections: List[PIIDetection],
                         strategy: str) -> str:
        """Redact using Presidio anonymizer."""
        # Convert our detections back to Presidio format
        results = [
            RecognizerResult(
                entity_type=d.entity_type,
                start=d.start,
                end=d.end,
                score=d.score
            )
            for d in detections
        ]
        
        # Configure operators based on strategy
        if strategy == "masked":
            operators = {
                entity: OperatorConfig("mask", {"chars_to_mask": 8, "masking_char": "*"})
                for entity in self.entities
            }
        else:  # type_placeholder (default)
            operators = {
                entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
                for entity in self.entities
            }
        
        result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        
        return result.text
    
    def _redact_fallback(self, 
                         text: str, 
                         detections: List[PIIDetection],
                         strategy: str) -> str:
        """Redact using simple string replacement."""
        # Sort by position (reverse) to replace from end to start
        sorted_detections = sorted(detections, key=lambda d: d.start, reverse=True)
        
        result = text
        entity_counts = {}
        
        for detection in sorted_detections:
            entity_type = detection.entity_type
            
            if strategy == "numbered":
                count = entity_counts.get(entity_type, 0) + 1
                entity_counts[entity_type] = count
                replacement = f"<{entity_type}_{count}>"
            elif strategy == "masked":
                replacement = "*" * min(len(detection.text), 8)
            else:  # type_placeholder
                replacement = f"<{entity_type}>"
            
            result = result[:detection.start] + replacement + result[detection.end:]
        
        return result
    
    def is_pii_present(self, text: str) -> bool:
        """Quick check if any PII is present in text."""
        detections = self.detect(text)
        return len(detections) > 0
    
    def get_pii_summary(self, text: str) -> Dict[str, int]:
        """Get summary of PII types found in text."""
        result = self.redact(text)
        return result.detection_summary


# Singleton instance for reuse
_pii_redactor: Optional[PIIRedactor] = None


def get_pii_redactor() -> PIIRedactor:
    """Get or create singleton PIIRedactor instance."""
    global _pii_redactor
    if _pii_redactor is None:
        _pii_redactor = PIIRedactor()
    return _pii_redactor


def redact_pii(text: str) -> Tuple[str, bool]:
    """
    Convenience function to redact PII from text.
    
    Returns:
        Tuple of (redacted_text, had_pii)
    """
    redactor = get_pii_redactor()
    result = redactor.redact(text)
    return result.redacted_text, result.has_pii
