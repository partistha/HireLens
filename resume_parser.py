
from pathlib import Path
from PyPDF2 import PdfReader


def extract_pdf_text(pdf_path):
    """
    Extract selectable text from a PDF resume.
    Scanned/image-only PDFs require OCR and are not supported here.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError("Resume PDF was not found.")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    try:
        reader = PdfReader(str(pdf_path), strict=False)

        if reader.is_encrypted:
            try:
                result = reader.decrypt("")
                if result == 0:
                    raise ValueError("Password-protected PDF.")
            except Exception:
                raise ValueError("Password-protected PDF.")

        extracted_pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                extracted_pages.append(text)

        extracted_text = "\n".join(extracted_pages)
        extracted_text = " ".join(extracted_text.split())

        if not extracted_text:
            raise ValueError(
                "No selectable text found in this PDF."
            )

        return extracted_text

    except ValueError:
        raise

    except Exception as exc:
        raise ValueError(
            f"Could not read PDF: {str(exc)}"
        ) from exc
