import argparse
from collections.abc import Sequence


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", metavar="INPUT.md")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="gpt-5.6-terra")
    parser.add_argument("--batch-size", type=_positive_integer, default=10)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    build_parser().parse_args(argv)
