import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import auth


class LoadEnvFileTest(unittest.TestCase):
    def load(self, text: str | None, env: dict[str, str]) -> dict[str, str | None]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.env"
            if text is not None:
                path.write_text(text, encoding="utf-8")
            with mock.patch.dict(os.environ, {**env, "TASKFLOW_ENV_FILE": str(path)}, clear=True):
                auth.load_env_file()
                return {k: os.environ.get(k) for k in ("A_KEY", "B_KEY", "C_KEY")}

    def test_env_file_value_overrides_existing_environment_variable(self) -> None:
        got = self.load("A_KEY=from-file\n", {"A_KEY": "stale-env"})
        self.assertEqual(got["A_KEY"], "from-file")

    def test_key_missing_from_file_keeps_environment_variable(self) -> None:
        got = self.load("A_KEY=from-file\n", {"B_KEY": "from-env"})
        self.assertEqual((got["A_KEY"], got["B_KEY"]), ("from-file", "from-env"))

    def test_blank_value_does_not_erase_environment_variable(self) -> None:
        got = self.load("A_KEY=\nB_KEY=''\n", {"A_KEY": "from-env", "B_KEY": "from-env"})
        self.assertEqual((got["A_KEY"], got["B_KEY"]), ("from-env", "from-env"))

    def test_comments_quotes_and_spaces(self) -> None:
        got = self.load('# c\n\nA_KEY = "quoted"\nB_KEY=plain\nnot a pair\n', {})
        self.assertEqual((got["A_KEY"], got["B_KEY"]), ("quoted", "plain"))

    def test_missing_file_changes_nothing(self) -> None:
        self.assertEqual(self.load(None, {"A_KEY": "from-env"})["A_KEY"], "from-env")


if __name__ == "__main__":
    unittest.main()
