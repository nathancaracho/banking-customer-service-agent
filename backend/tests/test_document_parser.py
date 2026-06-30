import io
import unittest

from pypdf import PdfWriter

from backend.knowledge.document_parser import InvalidDocumentError, parse_document


class DocumentParserTestCase(unittest.TestCase):
    def test_rejects_empty_txt(self) -> None:
        with self.assertRaises(InvalidDocumentError):
            parse_document(b"  ", "text/plain")

    def test_rejects_pdf_without_extractable_text(self) -> None:
        output = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(output)

        with self.assertRaises(InvalidDocumentError):
            parse_document(output.getvalue(), "application/pdf")

    def test_decodes_utf8_txt(self) -> None:
        self.assertEqual(
            parse_document("Tarifas bancárias".encode(), "text/plain"),
            "Tarifas bancárias",
        )
