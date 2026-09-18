import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

from openai import OpenAI, OpenAIError

from .models import AnalysisResult, ParseResult, Usage
from .openai_analysis import AnalysisClient, AnalysisError
from .parser import parse_issues
from .render import write_outputs
from .secrets import SecretLookupError, load_openai_api_key


@dataclass
class Dependencies:
    parse: Callable[[str], ParseResult] = parse_issues
    load_key: Callable[[], str] = load_openai_api_key
    openai_constructor: Callable[..., Any] = OpenAI
    analysis_client_constructor: Callable[[Any], Any] = AnalysisClient
    output_writer: Callable[..., tuple[Path, Path]] = write_outputs


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


def _redact(message: str, secret: str | None) -> str:
    if secret:
        return message.replace(secret, "[REDACTED]")
    return message


def run(
    argv: Sequence[str] | None = None, *, dependencies: Dependencies | None = None
) -> int:
    args = build_parser().parse_args(argv)
    dependencies = dependencies or Dependencies()
    secret: str | None = None

    try:
        source = Path(args.input)
        markdown = source.read_text(encoding="utf-8")
        parsed = dependencies.parse(markdown)
        for warning in parsed.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        if not parsed.issues:
            print("Error: no recognizable issues found.", file=sys.stderr)
            return 1

        secret = dependencies.load_key()
        client = dependencies.openai_constructor(api_key=secret, max_retries=2)
        analyzer = dependencies.analysis_client_constructor(client)
        extraction = analyzer.extract_issue_observations(
            parsed.issues, model=args.model, batch_size=args.batch_size
        )
        synthesis = analyzer.synthesize(extraction.observations, model=args.model)
        usage = Usage(
            input_tokens=extraction.usage.input_tokens + synthesis.usage.input_tokens,
            output_tokens=extraction.usage.output_tokens + synthesis.usage.output_tokens,
            total_tokens=extraction.usage.total_tokens + synthesis.usage.total_tokens,
        )
        result = AnalysisResult(
            schema_version="1",
            model=args.model,
            source_file=str(source),
            parsing_warnings=parsed.warnings,
            observations=extraction.observations,
            synthesis=synthesis.synthesis,
            usage=usage,
        )
        json_path, report_path = dependencies.output_writer(result, args.output)
        print(f"JSON: {json_path}")
        print(f"Report: {report_path}")
        print(f"Total tokens: {usage.total_tokens}")
        return 0
    except (OSError, UnicodeError, SecretLookupError, AnalysisError, OpenAIError) as error:
        print(f"Error: {_redact(str(error), secret)}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)
