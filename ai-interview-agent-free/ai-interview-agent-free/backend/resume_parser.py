"""
=============================================================
  resume_parser.py  —  Extract text from uploaded resumes
=============================================================
  Supports:
    • PDF  →  uses PyMuPDF (fast, reliable)
    • DOCX →  uses python-docx
    • TXT  →  plain file read

  Used by: app.py  →  extract_text(filepath)
=============================================================
"""

import os


def extract_text(filepath: str) -> str:
    """
    Main entry point.
    Detects the file type and delegates to the right reader.

    Args:
        filepath  Full path to the uploaded resume file

    Returns:
        All text from the resume as one string
    """
    ext = filepath.rsplit('.', 1)[-1].lower()

    readers = {
        'pdf' : _read_pdf,
        'docx': _read_docx,
        'txt' : _read_txt,
    }

    reader = readers.get(ext)
    if not reader:
        raise ValueError(f"Unsupported file type: .{ext}")

    return reader(filepath)


# ─── PDF reader ───────────────────────────────────────────────

def _read_pdf(filepath: str) -> str:
    """
    Reads a PDF file page by page using PyMuPDF.
    PyMuPDF (imported as 'fitz') is the most reliable PDF reader.
    """
    try:
        import fitz  # pip install pymupdf

        text = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                # get_text() returns the plain text of one page
                text += page.get_text() + "\n"

        return text.strip()

    except ImportError:
        # Fallback to pdfplumber if pymupdf is not installed
        return _read_pdf_fallback(filepath)
    except Exception as e:
        raise Exception(f"PDF read error: {e}")


def _read_pdf_fallback(filepath: str) -> str:
    """Fallback PDF reader using pdfplumber."""
    try:
        import pdfplumber  # pip install pdfplumber

        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()

    except ImportError:
        raise Exception(
            "No PDF library found.\n"
            "Fix: pip install pymupdf"
        )


# ─── DOCX reader ──────────────────────────────────────────────

def _read_docx(filepath: str) -> str:
    """
    Reads a Word document paragraph by paragraph.
    Each paragraph becomes one line of text.
    """
    try:
        from docx import Document  # pip install python-docx

        doc   = Document(filepath)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)

    except ImportError:
        raise Exception(
            "python-docx not installed.\n"
            "Fix: pip install python-docx"
        )
    except Exception as e:
        raise Exception(f"DOCX read error: {e}")


# ─── TXT reader ───────────────────────────────────────────────

def _read_txt(filepath: str) -> str:
    """Reads a plain .txt file with UTF-8 encoding."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    except Exception as e:
        raise Exception(f"TXT read error: {e}")
