
import re
from typing import List, Dict

try:
    import spacy
    _SPACY_AVAILABLE = True
except Exception:
    _SPACY_AVAILABLE = False

try:
    from transformers import pipeline
    _TRANSFORMERS_AVAILABLE = True
except Exception:
    _TRANSFORMERS_AVAILABLE = False
    pipeline = None

_HF_NER = None
_HF_CLASSIFIER = None


def _init_hf_models():
    global _HF_NER, _HF_CLASSIFIER
    if not _TRANSFORMERS_AVAILABLE:
        return
    if _HF_NER is None:
        try:
            _HF_NER = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", grouped_entities=True)
        except Exception:
            try:
                _HF_NER = pipeline("ner", model="dslim/bert-base-NER", grouped_entities=True)
            except Exception:
                _HF_NER = None
    if _HF_CLASSIFIER is None:
        try:
            _HF_CLASSIFIER = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        except Exception:
            _HF_CLASSIFIER = None

_SPACY_NLP = None
if _SPACY_AVAILABLE:
    try:
        _SPACY_NLP = spacy.load("en_core_web_sm")
    except Exception:
        _SPACY_NLP = None

PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[- ]?)?(?:\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}|\d{7,12})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b")
}


def _regex_scan(text: str) -> List[Dict]:
    results = []
    for pii_type, pattern in PII_PATTERNS.items():
        for m in pattern.finditer(text):
            results.append({
                "type": pii_type,
                "value": m.group(0),
                "start": m.start(),
                "end": m.end(),
                "source": "regex",
                "confidence": 0.9
            })
    return results


def _spacy_scan(text: str) -> List[Dict]:
    results = []
    if not _SPACY_NLP:
        return results
    doc = _SPACY_NLP(text)
    for ent in doc.ents:
        results.append({
            "type": ent.label_.lower(),
            "value": ent.text,
            "start": ent.start_char,
            "end": ent.end_char,
            "source": "spacy",
            "confidence": getattr(ent, "kb_id", 0.8) or 0.8
        })
    return results


def _hf_ner_scan(text: str) -> List[Dict]:
    results = []
    if _HF_NER is None:
        try:
            _init_hf_models()
        except Exception:
            return results
    if not _HF_NER:
        return results
    try:
        ents = _HF_NER(text)
        for ent in ents:
            ent_type = ent.get("entity_group") or ent.get("entity")
            results.append({
                "type": str(ent_type).lower(),
                "value": ent.get("word") or ent.get("word", ""),
                "start": ent.get("start"),
                "end": ent.get("end"),
                "source": "hf_ner",
                "confidence": float(ent.get("score", 0.0))
            })
    except Exception:
        pass
    return results


def _dedupe_findings(findings: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for f in sorted(findings, key=lambda x: (x.get("start") or 0, -(x.get("end") or 0))):
        key = (f.get("type"), f.get("value"), f.get("start"), f.get("end"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def scan_text(text: str, use_spacy: bool = True, use_hf: bool = True, use_regex: bool = True) -> List[Dict]:
    """Run multiple detectors and return a deduplicated list of findings.

    Each finding: { type, value, start, end, source, confidence }
    """
    findings: List[Dict] = []
    if use_regex:
        findings.extend(_regex_scan(text))
    if use_spacy:
        findings.extend(_spacy_scan(text))
    if use_hf:
        findings.extend(_hf_ner_scan(text))

    try:
        if _HF_CLASSIFIER is None:
            _init_hf_models()
        # we avoid running a full classifier on long texts by default; leave hook for future
    except Exception:
        # best-effort only; never fail the scan
        return _dedupe_findings(findings)

    return _dedupe_findings(findings)


def redact_text(text: str, placeholder: str = "[REDACTED]") -> str:
    findings = scan_text(text)
    spans = [(f.get("start"), f.get("end")) for f in findings if f.get("start") is not None and f.get("end") is not None]
    if not spans:
        for pattern in PII_PATTERNS.values():
            text = pattern.sub(placeholder, text)
        return text

    spans = sorted(spans, key=lambda x: x[0])
    merged = []
    for s, e in spans:
        if not merged or s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    parts = []
    last = 0
    for s, e in merged:
        parts.append(text[last:s])
        parts.append(placeholder)
        last = e
    parts.append(text[last:])
    return "".join(parts)


def score_privacy_risk(findings: List[Dict]) -> int:
    """Simple risk scoring: high weight for direct identifiers, lower for named entities."""
    if not findings:
        return 0
    score = 0
    for f in findings:
        t = (f.get("type") or "").lower()
        if t in ["ssn", "credit_card"]:
            score += 35
        elif t in ["email", "phone"]:
            score += 20
        elif t in ["person", "org", "gpe"]:
            score += 10
        else:
            score += 5

    score = min(int(score), 100)
    return score

