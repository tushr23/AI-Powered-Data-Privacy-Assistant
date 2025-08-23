
import re
from typing import List, Dict

_SPACY_AVAILABLE = None
_spacy = None

def _check_spacy():
    global _SPACY_AVAILABLE, _spacy
    if _SPACY_AVAILABLE is None:
        try:
            import spacy
            _spacy = spacy
            _SPACY_AVAILABLE = True
        except Exception:
            _SPACY_AVAILABLE = False
            _spacy = None
    return _SPACY_AVAILABLE

_check_spacy()

_TRANSFORMERS_AVAILABLE = None
pipeline = None

def _check_transformers():
    global _TRANSFORMERS_AVAILABLE, pipeline
    if _TRANSFORMERS_AVAILABLE is None:
        try:
            from transformers import pipeline as _pipeline
            pipeline = _pipeline
            _TRANSFORMERS_AVAILABLE = True
        except Exception:
            _TRANSFORMERS_AVAILABLE = False
            pipeline = None
    return _TRANSFORMERS_AVAILABLE

_HF_NER = None
_HF_CLASSIFIER = None


def _init_hf_models():
    global _HF_NER, _HF_CLASSIFIER
    if not _check_transformers():
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

def _load_spacy_model():
    global _SPACY_NLP
    if _SPACY_NLP is None and _check_spacy():
        try:
            _SPACY_NLP = _spacy.load("en_core_web_sm")
        except Exception:
            _SPACY_NLP = None
    return _SPACY_NLP

PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
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
    nlp = _load_spacy_model()
    if not nlp:
        return results
    doc = nlp(text)
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
    except Exception:
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

    return min(int(score), 100)

