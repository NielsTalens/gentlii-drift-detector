from pathlib import Path
from types import SimpleNamespace

import pytest
from openai import OpenAIError

from gentlii_drift_detector.cli import Dependencies, main, run
from gentlii_drift_detector.models import Issue, IssueExtractionResult, IssueObservation, ParseResult, Synthesis, SynthesisResult, Usage
from gentlii_drift_detector.openai_analysis import AnalysisError
from gentlii_drift_detector.secrets import SecretLookupError


def _observation() -> IssueObservation:
    return IssueObservation(issue_number=7, title="Useful work", delivery_status="delivered", user_needs=["speed"], capabilities=["automation"], strategic_goals=["scale"], investment_themes=["workflow"], direction_signals=["self-service"], evidence_summary="Delivered automation.", confidence="high")


def _synthesis() -> Synthesis:
    return Synthesis(observed_strategy=[], observed_strategic_goals=[], observed_product_vision=[], user_needs=[], capabilities=[], investment_themes=[], uncertainties=[])


def _successful_dependencies(events: list[object], *, warnings=()) -> Dependencies:
    observation = _observation()

    class FakeAnalyzer:
        def extract_issue_observations(self, issues, model, batch_size):
            events.append(("extract", issues, model, batch_size))
            return IssueExtractionResult(observations=[observation], usage=Usage(input_tokens=10, output_tokens=4, total_tokens=14))

        def synthesize(self, observations, model):
            events.append(("synthesize", observations, model))
            return SynthesisResult(synthesis=_synthesis(), usage=Usage(input_tokens=5, output_tokens=3, total_tokens=8))

    def parse(markdown):
        events.append(("parse", markdown))
        return ParseResult(issues=[Issue(number=7, title="Useful work", body="Body")], warnings=list(warnings))

    def load_key():
        events.append("secret")
        return "fake-secret"

    def openai(**kwargs):
        events.append(("openai", kwargs))
        return object()

    def analyzer(client):
        events.append(("analyzer", client))
        return FakeAnalyzer()

    def write(result, output_dir):
        events.append(("write", result, output_dir))
        return Path(output_dir) / "analysis.json", Path(output_dir) / "report.md"

    return Dependencies(parse, load_key, openai, analyzer, write)


def test_help_describes_cli_interface(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "INPUT.md" in help_text
    assert "--output" in help_text
    assert "--model" in help_text
    assert "--batch-size" in help_text


@pytest.mark.parametrize("value", ["0", "-1"])
def test_batch_size_must_be_positive(value: str) -> None:
    with pytest.raises(SystemExit):
        main(["issues.md", "--output", "out", "--batch-size", value])


def test_run_wires_two_stage_analysis_and_aggregates_usage(tmp_path, capsys) -> None:
    source = tmp_path / "issues.md"
    source.write_text("issue markdown", encoding="utf-8")
    events: list[object] = []

    code = run([str(source), "--output", str(tmp_path / "results"), "--model", "chosen", "--batch-size", "3"], dependencies=_successful_dependencies(events))

    assert code == 0
    assert events[0] == ("parse", "issue markdown")
    assert events[1] == "secret"
    assert events[2] == ("openai", {"api_key": "fake-secret", "max_retries": 2})
    assert events[4][0] == "extract"
    assert events[4][2:] == ("chosen", 3)
    assert events[5] == ("synthesize", [_observation()], "chosen")
    written = events[6][1]
    assert written.schema_version == "1.0"
    assert written.model == "chosen"
    assert written.source_file == str(source)
    assert written.usage == Usage(input_tokens=15, output_tokens=7, total_tokens=22)
    output = capsys.readouterr().out
    assert str(tmp_path / "results" / "analysis.json") in output
    assert str(tmp_path / "results" / "report.md") in output
    assert "22" in output


def test_parser_warnings_go_to_stderr_but_run_succeeds(tmp_path, capsys) -> None:
    source = tmp_path / "issues.md"
    source.write_text("content", encoding="utf-8")
    events: list[object] = []

    assert run([str(source), "--output", str(tmp_path / "out")], dependencies=_successful_dependencies(events, warnings=["Sparse issue"])) == 0

    assert "Sparse issue" in capsys.readouterr().err
    assert events[6][1].parsing_warnings == ["Sparse issue"]


def test_no_issues_fails_before_secret_lookup(tmp_path, capsys) -> None:
    source = tmp_path / "issues.md"
    source.write_text("nothing useful", encoding="utf-8")
    events: list[object] = []
    dependencies = _successful_dependencies(events)
    dependencies.parse = lambda text: (events.append("parse") or ParseResult())

    assert run([str(source), "--output", str(tmp_path / "out")], dependencies=dependencies) != 0
    assert events == ["parse"]
    assert "no recognizable issues" in capsys.readouterr().err.lower()


def test_invalid_utf8_fails_before_secret_lookup_or_analysis(tmp_path, capsys) -> None:
    source = tmp_path / "issues.md"
    source.write_bytes(b"\xff")
    events: list[object] = []

    assert run(
        [str(source), "--output", str(tmp_path / "out")],
        dependencies=_successful_dependencies(events),
    ) != 0

    assert events == []
    error = capsys.readouterr().err
    assert "Error:" in error
    assert "utf-8" in error


@pytest.mark.parametrize(
    ("replacement", "message"),
    [("read", OSError("cannot read")), ("secret", SecretLookupError("no key")), ("extract", AnalysisError("bad analysis")), ("extract", OpenAIError("API unavailable")), ("write", OSError("disk full"))],
)
def test_expected_failures_are_concise(tmp_path, capsys, replacement, message) -> None:
    source = tmp_path / "issues.md"
    source.write_text("content", encoding="utf-8")
    events: list[object] = []
    dependencies = _successful_dependencies(events)

    if replacement == "read":
        source = tmp_path / "missing.md"
    elif replacement == "secret":
        dependencies.load_key = lambda: (_ for _ in ()).throw(message)
    elif replacement == "extract":
        dependencies.analysis_client_constructor = lambda client: SimpleNamespace(extract_issue_observations=lambda *args, **kwargs: (_ for _ in ()).throw(message))
    elif replacement == "write":
        dependencies.output_writer = lambda *args: (_ for _ in ()).throw(message)

    assert run([str(source), "--output", str(tmp_path / "out")], dependencies=dependencies) != 0
    error = capsys.readouterr().err
    assert "Error:" in error
    assert ("missing.md" if replacement == "read" else str(message)) in error


def test_downstream_error_redacts_loaded_secret(tmp_path, capsys) -> None:
    source = tmp_path / "issues.md"
    source.write_text("content", encoding="utf-8")
    events: list[object] = []
    dependencies = _successful_dependencies(events)
    dependencies.output_writer = lambda *args: (_ for _ in ()).throw(OSError("failed while handling fake-secret"))

    assert run([str(source), "--output", str(tmp_path / "out")], dependencies=dependencies) != 0
    captured = capsys.readouterr()
    assert "fake-secret" not in captured.out + captured.err
    assert "[REDACTED]" in captured.err
