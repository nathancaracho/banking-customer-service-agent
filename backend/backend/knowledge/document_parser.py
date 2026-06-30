from io import BytesIO

from pypdf import PdfReader


class InvalidDocumentError(ValueError):
    pass


def parse_document(content: bytes, content_type: str) -> str:
    parsers = {
        "text/plain": _parse_txt,
        "application/pdf": _parse_pdf,
    }
    parser = parsers.get(content_type)

    if parser is None:
        raise InvalidDocumentError("Unsupported document type")

    text = parser(content).strip()

    if not text:
        raise InvalidDocumentError("Document has no extractable text")

    return text


def _parse_txt(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InvalidDocumentError("TXT document must use UTF-8") from error


def _parse_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise InvalidDocumentError("Invalid PDF document") from error
