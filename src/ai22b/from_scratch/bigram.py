from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def train_model(text: str) -> dict[str, Any]:
    if len(text) < 2:
        raise ValueError("Training text must contain at least two characters.")

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for current_char, next_char in zip(text, text[1:]):
        counts[current_char][next_char] += 1

    return {
        "model_type": "character_bigram",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "vocab": sorted(set(text)),
        "counts": {char: dict(next_counts) for char, next_counts in counts.items()},
    }


def save_model(model: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)


def load_model(model_path: Path) -> dict[str, Any]:
    with model_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _weighted_choice(next_counts: dict[str, int], rng: random.Random) -> str:
    total = sum(next_counts.values())
    threshold = rng.randint(1, total)
    running = 0
    for char, count in next_counts.items():
        running += count
        if running >= threshold:
            return char
    return next(iter(next_counts))


def generate_text(
    model: dict[str, Any],
    seed: str = "",
    length: int = 300,
    random_seed: int | None = None,
) -> str:
    if length < 1:
        raise ValueError("Length must be positive.")

    rng = random.Random(random_seed)
    counts: dict[str, dict[str, int]] = model["counts"]
    vocab: list[str] = model["vocab"]

    if seed:
        output = list(seed)
        current = seed[-1]
    else:
        current = rng.choice(vocab)
        output = [current]

    for _ in range(length):
        next_counts = counts.get(current)
        if not next_counts:
            current = rng.choice(vocab)
            output.append(current)
            continue
        current = _weighted_choice(next_counts, rng)
        output.append(current)

    return "".join(output)


def train_command(args: argparse.Namespace) -> int:
    text = Path(args.input).read_text(encoding="utf-8")
    model = train_model(text)
    save_model(model, Path(args.output))
    print(f"Saved tiny bigram model: {args.output}")
    print(f"Vocabulary size: {len(model['vocab'])}")
    return 0


def generate_command(args: argparse.Namespace) -> int:
    model = load_model(Path(args.model))
    print(generate_text(model, seed=args.seed, length=args.length, random_seed=args.random_seed))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and sample a tiny character bigram model.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train", help="Train a tiny model from a text file.")
    train.add_argument("--input", required=True, help="UTF-8 training corpus path.")
    train.add_argument("--output", required=True, help="Output JSON model path.")
    train.set_defaults(func=train_command)

    generate = subparsers.add_parser("generate", help="Generate text from a saved tiny model.")
    generate.add_argument("--model", required=True, help="Saved JSON model path.")
    generate.add_argument("--seed", default="", help="Starting text.")
    generate.add_argument("--length", type=int, default=300, help="Number of new characters.")
    generate.add_argument("--random-seed", type=int, default=22, help="Deterministic sampling seed.")
    generate.set_defaults(func=generate_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
