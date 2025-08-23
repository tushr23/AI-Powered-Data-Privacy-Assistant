"""File text extraction utilities."""
import io


def extract_text_from_file(content: bytes, filename: str) -> str:
    """Extract text from file content based on filename extension."""
    if not filename:
        return _decode_text(content)
    
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return _extract_pdf_text(content)
    elif filename_lower.endswith('.docx'):
        return _extract_docx_text(content)
    else:
        return _decode_text(content)


def _decode_text(content: bytes) -> str:
    """Decode bytes to text with fallback encodings."""
    for encoding in ['utf-8', 'latin1', 'cp1252']:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF content."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return '\n'.join(page.extract_text() for page in reader.pages)
    except Exception:
        return ""


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX content."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        
        text_parts = [p.text for p in doc.paragraphs]
        
        # Extract table text
        for table in doc.tables:
            for row in table.rows:
                text_parts.extend(cell.text for cell in row.cells)
        
        return '\n'.join(text_parts)
    except Exception:
        return ""