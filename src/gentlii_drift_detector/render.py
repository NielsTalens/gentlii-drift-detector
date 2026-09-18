import json
import os
import re
import tempfile
from html import escape
from collections.abc import Callable
from typing import IO, Any
from pathlib import Path

from .models import AnalysisResult, SupportedClaim


_SECTIONS = (
    ("Observed Strategy", "observed_strategy"),
    ("Observed Strategic Goals", "observed_strategic_goals"),
    ("Observed Product Vision", "observed_product_vision"),
    ("Customer/User Needs", "user_needs"),
    ("Strengthened Product Capabilities", "capabilities"),
    ("Investment Themes", "investment_themes"),
    ("Uncertainties/Evidence Gaps", "uncertainties"),
)
_URI = re.compile(
    r"(?:[a-z][a-z0-9+.-]*://|mailto:|data:|www\.)[^\s)\]]+", re.IGNORECASE
)
_MARKDOWN = re.compile(r"([`*_{}\[\]()#!|>])")
TempWriter = Callable[[Path, str, str], Path]
Replace = Callable[[Path, Path], None]


def _replace_path(source: Path, target: Path) -> None:
    source.replace(target)


def render_json(result: AnalysisResult) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"


def _render_claim(claim: SupportedClaim) -> str:
    statement = _inert_text(_URI.sub("", claim.statement)).strip()
    issues = ", ".join(f"#{number}" for number in claim.issue_numbers)
    return f"- {statement}\n  - Confidence: {claim.confidence}\n  - Issues: {issues}"


def _inert_text(value: str) -> str:
    normalized = value.replace("\r", " ").replace("\n", " ")
    return _MARKDOWN.sub(r"\\\1", escape(normalized, quote=True))


def _metadata_text(value: str) -> str:
    return _inert_text(value)


def render_markdown(result: AnalysisResult) -> str:
    lines = ["# Drift Detection Analysis", ""]
    for heading, attribute in _SECTIONS:
        lines.extend([f"## {heading}", ""])
        claims = getattr(result.synthesis, attribute)
        if claims:
            lines.extend(_render_claim(claim) for claim in claims)
        else:
            lines.append("No supported claims.")
        lines.append("")

    usage = result.usage
    lines.extend(
        [
            "## Run Metadata",
            "",
            f"- Model: {_metadata_text(result.model)}",
            f"- Source: {_metadata_text(result.source_file)}",
            f"- Input tokens: {usage.input_tokens}",
            f"- Output tokens: {usage.output_tokens}",
            f"- Total tokens: {usage.total_tokens}",
            "",
            "### Parsing Warnings",
            "",
        ]
    )
    lines.extend(
        f"- {_metadata_text(warning)}" for warning in result.parsing_warnings
    ) if result.parsing_warnings else lines.append("No parsing warnings.")
    return "\n".join(lines) + "\n"


def _write_temp(
    directory: Path,
    content: str,
    suffix: str,
    *,
    _mkstemp: Callable[..., tuple[int, str]] = tempfile.mkstemp,
    _fdopen: Callable[..., IO[Any]] = os.fdopen,
) -> Path:
    descriptor, name = _mkstemp(dir=directory, suffix=f"{suffix}.tmp")
    path = Path(name)
    try:
        stream = _fdopen(descriptor, "w", encoding="utf-8")
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    try:
        with stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def write_outputs(
    result: AnalysisResult,
    output_dir: str | Path,
    *,
    _temp_writer: TempWriter = _write_temp,
    _replace: Replace = _replace_path,
) -> tuple[Path, Path]:
    json_content = render_json(result)
    markdown_content = render_markdown(result)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    temporary_paths: list[Path] = []
    try:
        temporary_paths.append(_temp_writer(directory, json_content, ".json"))
        temporary_paths.append(_temp_writer(directory, markdown_content, ".md"))
    except BaseException:
        for path in temporary_paths:
            path.unlink(missing_ok=True)
        raise

    json_path = directory / "analysis.json"
    markdown_path = directory / "report.md"
    try:
        originals = {
            json_path: json_path.read_bytes() if json_path.exists() else None,
            markdown_path: markdown_path.read_bytes() if markdown_path.exists() else None,
        }
        try:
            _replace(temporary_paths[0], json_path)
            _replace(temporary_paths[1], markdown_path)
        except BaseException:
            for final_path, original in originals.items():
                if original is None:
                    final_path.unlink(missing_ok=True)
                else:
                    final_path.write_bytes(original)
            raise
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)
    return json_path, markdown_path
