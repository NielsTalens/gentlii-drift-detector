import json
from pathlib import Path

import pytest

from gentlii_drift_detector.models import (
    AnalysisResult,
    IssueObservation,
    SupportedClaim,
    Synthesis,
    Usage,
)
from gentlii_drift_detector.render import render_json, render_markdown, write_outputs


def make_result(*, empty: bool = False) -> AnalysisResult:
    claim = SupportedClaim(
        statement="Serve café operators without exposing https://example.test",
        issue_numbers=[12, 34],
        confidence="low",
    )
    claims = [] if empty else [claim]
    return AnalysisResult(
        schema_version="1.0",
        model="gpt-test",
        source_file="issues-é.md",
        parsing_warnings=["Sparse issue #99"],
        observations=[
            IssueObservation(
                issue_number=12,
                title="Unicode café",
                delivery_status="delivered",
                user_needs=["Fast setup"],
                capabilities=["Import"],
                strategic_goals=["Adoption"],
                investment_themes=["Onboarding"],
                direction_signals=["Self-service"],
                evidence_summary="Delivered setup flow",
                confidence="high",
            )
        ],
        synthesis=Synthesis(
            observed_strategy=claims,
            observed_strategic_goals=claims,
            observed_product_vision=claims,
            user_needs=claims,
            capabilities=claims,
            investment_themes=claims,
            uncertainties=claims,
        ),
        usage=Usage(input_tokens=100, output_tokens=20, total_tokens=120),
    )


def test_render_json_contains_complete_serialized_result_and_preserves_unicode():
    rendered = render_json(make_result())
    payload = json.loads(rendered)

    assert rendered.endswith("\n")
    assert "café" in rendered
    assert payload["schema_version"] == "1.0"
    assert payload["model"] == "gpt-test"
    assert payload["source_file"] == "issues-é.md"
    assert payload["parsing_warnings"] == ["Sparse issue #99"]
    assert payload["observations"][0]["issue_number"] == 12
    assert payload["synthesis"]["observed_strategy"][0]["issue_numbers"] == [12, 34]
    assert payload["usage"] == {
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
    }


def test_render_markdown_has_all_sections_claim_evidence_and_metadata():
    rendered = render_markdown(make_result())

    for heading in (
        "# Drift Detection Analysis",
        "## Observed Strategy",
        "## Observed Strategic Goals",
        "## Observed Product Vision",
        "## Customer/User Needs",
        "## Strengthened Product Capabilities",
        "## Investment Themes",
        "## Uncertainties/Evidence Gaps",
    ):
        assert heading in rendered
    assert "Confidence: low" in rendered
    assert "Issues: #12, #34" in rendered
    assert "https://" not in rendered
    assert "Model: gpt-test" in rendered
    assert "Source: issues-é.md" in rendered
    assert "Sparse issue \\#99" in rendered
    assert "Input tokens: 100" in rendered


def test_render_markdown_keeps_empty_sections_readable():
    rendered = render_markdown(make_result(empty=True))

    assert rendered.count("No supported claims.") == 7


def test_render_markdown_renders_hostile_metadata_as_inert_text():
    result = make_result()
    result.model = "model\r\n## Injected `code` [link]"
    result.source_file = "issues\n- injected-list.md"
    result.parsing_warnings = ["warning\n# Fake heading `tick` [label]"]

    rendered = render_markdown(result)

    assert "\n## Injected" not in rendered
    assert "\n- injected-list.md" not in rendered
    assert "\n# Fake heading" not in rendered
    assert "Model: model  \\#\\# Injected \\`code\\` \\[link\\]" in rendered
    assert "Source: issues - injected-list.md" in rendered
    assert "warning \\# Fake heading \\`tick\\` \\[label\\]" in rendered


def test_write_outputs_publishes_both_artifacts(tmp_path: Path):
    paths = write_outputs(make_result(), tmp_path / "results")

    assert paths == (tmp_path / "results" / "analysis.json", tmp_path / "results" / "report.md")
    assert json.loads(paths[0].read_text())["model"] == "gpt-test"
    assert "## Observed Strategy" in paths[1].read_text()


def test_write_outputs_cleans_temps_and_publishes_nothing_when_second_write_fails(
    tmp_path: Path,
):
    calls = 0

    def failing_second_writer(directory: Path, content: str, suffix: str) -> Path:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        path = directory / f"first{suffix}.tmp"
        path.write_text(content)
        return path

    output_dir = tmp_path / "results"
    output_dir.mkdir()
    analysis_path = output_dir / "analysis.json"
    report_path = output_dir / "report.md"
    analysis_path.write_bytes(b"existing-json\n")
    report_path.write_bytes(b"existing-report\n")
    with pytest.raises(OSError, match="disk full"):
        write_outputs(make_result(), output_dir, _temp_writer=failing_second_writer)

    assert analysis_path.read_bytes() == b"existing-json\n"
    assert report_path.read_bytes() == b"existing-report\n"
    assert list(output_dir.glob("*.tmp")) == []
