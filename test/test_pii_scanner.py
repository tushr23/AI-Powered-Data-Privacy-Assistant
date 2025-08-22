"""
Comprehensive tests for the PII scanner module.
Tests regex detection, spaCy/HF integration, redaction, scoring, and edge cases.
"""
import pytest
import sys
import importlib
import builtins
from types import ModuleType
from backend import pii_scanner as ps


# Basic functionality tests
def test_regex_detects_email_and_phone_from_ticket():
    """Test basic regex-based PII detection using a ticket-like string."""
    text = "Contact me at test.user@example.com or +1 5551234567."
    findings = ps.scan_text(text, use_spacy=False, use_hf=False, use_regex=True)
    types = {f['type'] for f in findings}
    assert 'email' in types
    assert 'phone' in types


def test_scan_with_multiple_pii_types():
    """Test scanning text with multiple PII types."""
    text = "Contact: alice@example.com or +1 (555) 123-4567"
    findings = ps.scan_text(text, use_spacy=False, use_hf=False, use_regex=True)
    types = {f["type"] for f in findings}
    assert "email" in types
    assert "phone" in types


def test_redaction_basic():
    """Test basic PII redaction functionality."""
    # Author note: used this simple example during initial development to verify redaction
    text = "Alice has SSN 123-45-6789 and email alice@example.com"
    redacted = ps.redact_text(text)
    assert '123-45-6789' not in redacted
    assert 'alice@example.com' not in redacted
    assert '[REDACTED]' in redacted


def test_redaction_with_custom_placeholder():
    """Test redaction with custom placeholder."""
    text = "Alice SSN: 123-45-6789 and email alice@example.com"
    redacted = ps.redact_text(text, placeholder="[X]")
    assert "123-45-6789" not in redacted
    assert "alice@example.com" not in redacted
    assert redacted.count("[X]") >= 2


def test_privacy_risk_scoring():
    """Test privacy risk scoring with different PII types."""
    findings = [
        {'type': 'ssn', 'value': '123-45-6789'},
        {'type': 'email', 'value': 'a@b.com'},
        {'type': 'person', 'value': 'Alice'}
    ]
    score = ps.score_privacy_risk(findings)
    assert isinstance(score, int)
    assert score > 0


def test_score_privacy_risk_bounds():
    """Test privacy risk scoring bounds and weights."""
    findings = [
        {"type": "ssn", "value": "x"},
        {"type": "credit_card", "value": "y"},
        {"type": "email", "value": "z"},
    ]
    score = ps.score_privacy_risk(findings)
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_score_with_org_and_unknown_types():
    """Test scoring with organization and unknown entity types."""
    findings = [{"type": "org"}, {"type": "unknown"}]
    score = ps.score_privacy_risk(findings)
    # org -> +10, unknown -> +5 => 15
    assert isinstance(score, int) and score >= 15


# Edge cases and error handling
def test_empty_text_handling():
    """Test handling of empty text input."""
    findings = ps.scan_text("", use_spacy=False, use_hf=False, use_regex=True)
    assert findings == []
    assert ps.score_privacy_risk(findings) == 0


def test_no_detectors_enabled():
    """Test scan with all detectors disabled."""
    text = "nothing"
    findings = ps.scan_text(text, use_spacy=False, use_hf=False, use_regex=False)
    assert findings == []


def test_deduplication():
    """Test deduplication of overlapping findings."""
    text = "Bob phone: 5551234567"
    findings = ps.scan_text(text, use_spacy=False, use_hf=False, use_regex=True)
    # duplicate detection shouldn't produce zero-length or duplicate entries
    vals = [(f.get('value'), f.get('start'), f.get('end')) for f in findings]
    assert len(vals) == len(set(vals))


def test_dedupe_findings_function():
    """Test the _dedupe_findings function directly."""
    findings = [
        {"type": "email", "value": "a@b.com", "start": 0, "end": 7},
        {"type": "email", "value": "a@b.com", "start": 0, "end": 7},
    ]
    out = ps._dedupe_findings(findings)
    assert len(out) == 1


def test_redact_regex_fallback(monkeypatch):
    """Test redaction falls back to regex when scan returns no spans."""
    # Force scan_text to return no spans so redact_text uses regex fallback
    monkeypatch.setattr(ps, "scan_text", lambda text: [])
    txt = "Contact: bob@example.com"
    red = ps.redact_text(txt, placeholder="[X]")
    assert "bob@example.com" not in red
    assert "[X]" in red


# Mock-based tests for external dependencies
def test_hf_init_failure_handling(monkeypatch):
    """Test handling of HuggingFace model initialization failure."""
    def _raise():
        raise RuntimeError("no hf")

    monkeypatch.setattr(ps, "_init_hf_models", _raise)
    monkeypatch.setattr(ps, "_HF_NER", None, raising=False)
    res = ps.scan_text("Alice", use_spacy=False, use_hf=True, use_regex=False)
    # Should not raise and should return a list (probably empty)
    assert isinstance(res, list)


def test_spacy_mocked_scan(monkeypatch):
    """Test spaCy scanning with mocked spaCy NLP."""
    class FakeEnt:
        def __init__(self, text, label_, start_char, end_char):
            self.text = text
            self.label_ = label_
            self.start_char = start_char
            self.end_char = end_char

    class FakeDoc:
        def __init__(self, ents):
            self.ents = ents

    def fake_load(text):
        return FakeDoc([FakeEnt("Alice", "PERSON", 0, 5)])

    monkeypatch.setattr(ps, "_SPACY_NLP", type("X", (), {"__call__": lambda self, t: fake_load(t)})())
    res = ps.scan_text("Alice", use_spacy=True, use_hf=False, use_regex=False)
    assert any(f["type"] in ("person", "person") or f["value"] == "Alice" for f in res)


def test_hf_ner_mocked_scan(monkeypatch):
    """Test HuggingFace NER scanning with mocked pipeline."""
    def fake_hf(text):
        return [{"entity_group": "PER", "word": "Alice", "start": 0, "end": 5, "score": 0.99}]

    monkeypatch.setattr(ps, "_HF_NER", fake_hf, raising=False)
    res = ps.scan_text("Alice", use_spacy=False, use_hf=True, use_regex=False)
    assert any(f["type"] == "per" or f["value"] == "Alice" for f in res)


def test_scan_text_hf_init_exception(monkeypatch):
    """Test scan_text handles _init_hf_models raising exceptions."""
    if 'backend.pii_scanner' in sys.modules:
        importlib.reload(sys.modules['backend.pii_scanner'])
    import backend.pii_scanner as ps

    def _raise_init():
        raise RuntimeError('boom')

    monkeypatch.setattr(ps, '_init_hf_models', _raise_init)
    # run with regex enabled so we have findings but init_hf_models will raise and be caught
    res = ps.scan_text('Contact: alice@example.com', use_spacy=False, use_hf=True, use_regex=True)
    assert isinstance(res, list)


# Module reload tests for import-time coverage
def test_spacy_import_failure(monkeypatch):
    """Test module behavior when spaCy import fails."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == 'spacy':
            raise ImportError('blocked')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', fake_import)
    if 'backend.pii_scanner' in sys.modules:
        del sys.modules['backend.pii_scanner']
    import backend.pii_scanner as ps
    importlib.reload(ps)
    assert ps._SPACY_AVAILABLE is False
    assert ps._spacy_scan('Alice') == []


def test_hf_ner_entity_key_branch(monkeypatch):
    """Test HF NER handling of 'entity' vs 'entity_group' keys."""
    fake_transformers = ModuleType('transformers')

    def fake_pipeline(task, model=None, grouped_entities=None):
        if task == 'ner':
            def ner(text):
                return [{'entity': 'LOC', 'word': 'Paris', 'start': 0, 'end': 5, 'score': 0.8}]
            return ner
        return None

    monkeypatch.setitem(sys.modules, 'transformers', fake_transformers)
    fake_transformers.pipeline = fake_pipeline

    if 'backend.pii_scanner' in sys.modules:
        del sys.modules['backend.pii_scanner']
    import backend.pii_scanner as ps
    importlib.reload(ps)

    res = ps._hf_ner_scan('Paris')
    assert any(f.get('type') == 'loc' for f in res)


def test_hf_ner_falsy_branch():
    """Test HF NER behavior when _HF_NER is falsy."""
    ps._HF_NER = 0  # falsy
    res = ps._hf_ner_scan('text')
    assert res == []


def test_comprehensive_spacy_and_hf_reload(monkeypatch):
    """Test comprehensive reload with both spaCy and HuggingFace mocked."""
    # Prepare fake spacy module
    fake_spacy = ModuleType('spacy')

    class FakeNLP:
        def __call__(self, text):
            class Ent:
                def __init__(self):
                    self.label_ = 'PERSON'
                    self.text = 'Alice'
                    self.start_char = 0
                    self.end_char = 5

            class Doc:
                ents = [Ent()]

            return Doc()

    def fake_load(name):
        return FakeNLP()

    fake_spacy.load = fake_load

    # Prepare fake transformers module with pipeline
    fake_transformers = ModuleType('transformers')

    def fake_pipeline(task, model=None, grouped_entities=None):
        if task == 'ner':
            def ner_fn(text):
                return [{'entity_group': 'PER', 'word': 'Alice', 'start': 0, 'end': 5, 'score': 0.99}]
            return ner_fn
        if task == 'zero-shot-classification':
            def cls_fn(text, candidate_labels=None):
                return {'labels': ['privacy'], 'scores': [0.9]}
            return cls_fn

    fake_transformers.pipeline = fake_pipeline

    # Insert fakes into sys.modules and reload backend.pii_scanner
    monkeypatch.setitem(sys.modules, 'spacy', fake_spacy)
    monkeypatch.setitem(sys.modules, 'transformers', fake_transformers)

    # Remove backend.pii_scanner so import executes with our fakes
    if 'backend.pii_scanner' in sys.modules:
        del sys.modules['backend.pii_scanner']

    import backend.pii_scanner as ps
    importlib.reload(ps)

    # Now call scan_text with spacy and hf enabled
    res = ps.scan_text('Alice', use_spacy=True, use_hf=True, use_regex=False)
    assert any('alice' in (f.get('value') or '').lower() for f in res)


def test_init_hf_models_fallbacks(monkeypatch):
    """Exercise _init_hf_models fallback from first HF model to second and classifier branch."""
    # Create a fake transformers module where the first NER model raises,
    # the second returns a callable, and classifier returns a callable.
    fake_transformers = ModuleType('transformers')

    def fake_pipeline(task, model=None, grouped_entities=None):
        # Simulate dbmdz failing, dslim succeeding
        if task == 'ner':
            if model and 'dbmdz' in model:
                raise RuntimeError('first model missing')
            def ner_fn(text):
                return [{'entity_group': 'PER', 'word': 'Sam', 'start': 0, 'end': 3, 'score': 0.99}]
            return ner_fn
        if task == 'zero-shot-classification':
            def cls_fn(text, candidate_labels=None):
                return {'labels': ['privacy'], 'scores': [0.99]}
            return cls_fn
        return None

    fake_transformers.pipeline = fake_pipeline
    monkeypatch.setitem(sys.modules, 'transformers', fake_transformers)

    # Reload module so _init_hf_models picks up our fake
    if 'backend.pii_scanner' in sys.modules:
        del sys.modules['backend.pii_scanner']
    import backend.pii_scanner as ps
    importlib.reload(ps)

    # Call init and confirm HF_NER and HF_CLASSIFIER are set
    ps._HF_NER = None
    ps._HF_CLASSIFIER = None
    ps._init_hf_models()
    assert callable(ps._HF_NER)
    assert callable(ps._HF_CLASSIFIER)


def test_hf_ner_scan_handles_exceptions(monkeypatch):
    """Ensure _hf_ner_scan swallows exceptions from the HF pipeline and returns []."""
    import backend.pii_scanner as ps

    # Set _HF_NER to a function that raises
    def raising_hf(text):
        raise RuntimeError('boom')

    monkeypatch.setattr(ps, '_HF_NER', raising_hf, raising=False)
    out = ps._hf_ner_scan('text that causes hf to blow up')
    assert out == []


def test_redact_text_merges_overlapping_spans(monkeypatch):
    """Test redact_text merges overlapping spans returned by scan_text."""
    import backend.pii_scanner as ps

    sample = 'ABCDEFGHIJ12345'

    # Create overlapping spans: [0,10] and [5,15]
    fake_findings = [
        {'type': 'email', 'value': 'X', 'start': 0, 'end': 10},
        {'type': 'phone', 'value': 'Y', 'start': 5, 'end': 15},
    ]

    monkeypatch.setattr(ps, 'scan_text', lambda text: fake_findings)
    redacted = ps.redact_text(sample, placeholder='[X]')
    # Since the spans overlap and cover [0,15], we should see one placeholder
    assert redacted == '[X]'


def test_init_hf_models_dbmdz_fallback(monkeypatch):
    """Test _init_hf_models handles dbmdz failure and falls back to dslim model."""
    import backend.pii_scanner as ps
    from types import ModuleType

    fake_transformers = ModuleType('transformers')
    call_count = 0

    def fake_pipeline(task, model=None, grouped_entities=None):
        nonlocal call_count
        call_count += 1
        if task == 'ner':
            if model and 'dbmdz' in str(model):
                raise RuntimeError('dbmdz unavailable')
            # second call should succeed (dslim)
            return lambda text: [{'entity_group': 'PER', 'word': 'test', 'start': 0, 'end': 4, 'score': 0.9}]
        if task == 'zero-shot-classification':
            return lambda text, candidate_labels=None: {'labels': ['test'], 'scores': [0.8]}
        return None

    fake_transformers.pipeline = fake_pipeline
    monkeypatch.setitem(sys.modules, 'transformers', fake_transformers)

    # Clear existing globals and call init
    ps._HF_NER = None
    ps._HF_CLASSIFIER = None
    
    # Patch the pipeline function in the module
    monkeypatch.setattr(ps, 'pipeline', fake_pipeline, raising=False)
    
    ps._init_hf_models()
    
    # Should have successfully fallen back to dslim
    assert callable(ps._HF_NER)
    assert callable(ps._HF_CLASSIFIER)


def test_init_hf_models_both_ner_fail(monkeypatch):
    """Test _init_hf_models when both NER models fail, HF_NER becomes None."""
    import backend.pii_scanner as ps

    def fake_pipeline(task, model=None, grouped_entities=None):
        if task == 'ner':
            raise RuntimeError('no ner models available')
        if task == 'zero-shot-classification':
            return lambda text, candidate_labels=None: {'labels': ['test'], 'scores': [0.8]}
        return None

    monkeypatch.setattr(ps, 'pipeline', fake_pipeline, raising=False)
    ps._HF_NER = None
    ps._HF_CLASSIFIER = None
    
    ps._init_hf_models()
    
    # NER should be None, classifier should work
    assert ps._HF_NER is None
    assert callable(ps._HF_CLASSIFIER)


def test_init_hf_models_classifier_fails(monkeypatch):
    """Test _init_hf_models when classifier fails, HF_CLASSIFIER becomes None."""
    import backend.pii_scanner as ps

    def fake_pipeline(task, model=None, grouped_entities=None):
        if task == 'ner':
            return lambda text: [{'entity_group': 'PER', 'word': 'test', 'start': 0, 'end': 4, 'score': 0.9}]
        if task == 'zero-shot-classification':
            raise RuntimeError('no classifier available')
        return None

    monkeypatch.setattr(ps, 'pipeline', fake_pipeline, raising=False)
    ps._HF_NER = None
    ps._HF_CLASSIFIER = None
    
    ps._init_hf_models()
    
    # NER should work, classifier should be None
    assert callable(ps._HF_NER)
    assert ps._HF_CLASSIFIER is None


def test_spacy_load_fails_on_reload(monkeypatch):
    """Test module reload when spacy.load raises exception."""
    fake_spacy = ModuleType('spacy')
    
    def fake_load(model_name):
        raise RuntimeError('spacy model not available')
    
    fake_spacy.load = fake_load
    monkeypatch.setitem(sys.modules, 'spacy', fake_spacy)
    
    # Remove and reimport module to trigger spacy.load call
    if 'backend.pii_scanner' in sys.modules:
        del sys.modules['backend.pii_scanner']
    
    import backend.pii_scanner as ps
    importlib.reload(ps)
    
    # _SPACY_NLP should be None due to exception
    assert ps._SPACY_NLP is None


def test_scan_text_hf_classifier_init_exception(monkeypatch):
    """Test scan_text when _init_hf_models raises during HF_CLASSIFIER check."""
    import backend.pii_scanner as ps
    
    # Set up state where HF_CLASSIFIER is None
    ps._HF_CLASSIFIER = None
    
    # Make _init_hf_models raise
    def raise_init():
        raise RuntimeError('init failed')
    
    monkeypatch.setattr(ps, '_init_hf_models', raise_init)
    
    # Should still return deduplicated findings despite exception
    result = ps.scan_text('test@example.com', use_spacy=False, use_hf=False, use_regex=True)
    assert len(result) > 0  # Should find email
    assert any(f['type'] == 'email' for f in result)
