from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.worker import _chunk_response


class WorkerTestCase(unittest.TestCase):
    def test_chunks_response_with_fixed_width(self) -> None:
        self.assertEqual(
            _chunk_response("abcdefghij", 4),
            ["abcd", "efgh", "ij"],
        )


if __name__ == "__main__":
    unittest.main()
