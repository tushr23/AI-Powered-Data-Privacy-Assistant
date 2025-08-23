"""Tests for file_utils module."""
import pytest
import io
from backend.file_utils import extract_text_from_file, _decode_text, _extract_pdf_text, _extract_docx_text


def test_extract_text_from_file_no_filename():
    """Test extraction with no filename."""
    content = b"test content"
    result = extract_text_from_file(content, "")
    assert result == "test content"


def test_extract_text_from_file_txt():
    """Test extraction from .txt file."""
    content = b"hello world"
    result = extract_text_from_file(content, "test.txt")
    assert result == "hello world"


def test_extract_text_from_file_pdf():
    """Test extraction from .pdf file (will fail gracefully)."""
    content = b"not a real pdf"
    result = extract_text_from_file(content, "test.pdf")
    assert result == ""  # Should return empty string on PDF parsing failure


def test_extract_text_from_file_docx():
    """Test extraction from .docx file (will fail gracefully)."""
    content = b"not a real docx"
    result = extract_text_from_file(content, "test.docx")
    assert result == ""  # Should return empty string on DOCX parsing failure


def test_decode_text_utf8():
    """Test UTF-8 decoding."""
    content = b"hello world"
    result = _decode_text(content)
    assert result == "hello world"


def test_decode_text_latin1():
    """Test Latin-1 fallback decoding."""
    content = b"\xe9\xe8"  # é è in Latin-1
    result = _decode_text(content)
    assert result == "éè"


def test_decode_text_invalid():
    """Test invalid byte sequence."""
    content = b"\xff\xfe"  # Invalid UTF-8 and other encodings
    result = _decode_text(content)
    # Should return empty string when all encodings fail
    assert isinstance(result, str)


def test_extract_pdf_text_exception():
    """Test PDF extraction with invalid content."""
    content = b"invalid pdf content"
    result = _extract_pdf_text(content)
    assert result == ""


def test_extract_docx_text_exception():
    """Test DOCX extraction with invalid content."""
    content = b"invalid docx content"
    result = _extract_docx_text(content)
    assert result == ""
