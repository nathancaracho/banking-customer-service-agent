import unittest

from backend.knowledge.text_chunker import chunk_text


class TextChunkerTestCase(unittest.TestCase):
    def test_rejects_invalid_overlap(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("content", chunk_size=200, chunk_overlap=200)

    def test_small_text_produces_one_chunk(self) -> None:
        self.assertEqual(chunk_text("  short   text  ", 700, 200), ["short text"])

    def test_preserves_order_and_overlap(self) -> None:
        text = "".join(str(index % 10) for index in range(1_200))

        chunks = chunk_text(text, 700, 200)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][-200:], chunks[1][:200])
        self.assertEqual(chunks[0], text[:700])
        self.assertEqual(chunks[1], text[500:1_200])
