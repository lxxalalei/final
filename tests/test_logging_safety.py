#!/usr/bin/env python3
from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "resource-platforms/scripts"))
from shared.logger import SanitizingFilter


class TestLoggingSafety(unittest.TestCase):
    def test_sensitive_values_in_format_args_are_redacted(self) -> None:
        record = logging.LogRecord(
            "httpx", logging.INFO, __file__, 1,
            "GET %s", ("https://example.test/?msToken=secret&a_bogus=value",), None,
        )
        SanitizingFilter().filter(record)
        message = record.getMessage()
        self.assertNotIn("secret", message)
        self.assertIn("msToken=***REDACTED***", message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
