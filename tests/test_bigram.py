from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai22b.from_scratch.bigram import generate_text, load_model, save_model, train_model


class BigramTests(unittest.TestCase):
    def test_train_save_load_and_generate(self) -> None:
        model = train_model("보스와 줄리아는 함께 만든다.")
        self.assertEqual(model["model_type"], "character_bigram")
        self.assertIn("보", model["vocab"])

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            save_model(model, model_path)
            loaded = load_model(model_path)

        generated = generate_text(loaded, seed="보스", length=20, random_seed=22)
        self.assertTrue(generated.startswith("보스"))
        self.assertGreaterEqual(len(generated), 22)


if __name__ == "__main__":
    unittest.main()
