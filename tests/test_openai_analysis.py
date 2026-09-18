from types import SimpleNamespace

import pytest

from gentlii_drift_detector.models import Issue, IssueObservation, IssueObservationBatch
from gentlii_drift_detector.openai_analysis import AnalysisClient, AnalysisError


class FakeResponses:
    def __init__(self, batches):
        self.batches = iter(batches)
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        observations, usage = next(self.batches)
        return SimpleNamespace(
            output_parsed=IssueObservationBatch(observations=observations),
            usage=SimpleNamespace(**usage),
        )


def observation(number):
    return IssueObservation(
        issue_number=number,
        title=f"Issue {number}",
        delivery_status="delivered",
        user_needs=[f"Need {number}"],
        capabilities=[],
        strategic_goals=[],
        investment_themes=[],
        direction_signals=[],
        evidence_summary=f"Evidence {number}",
        confidence="high",
    )


def test_extracts_batches_with_safe_prompt_and_accumulates_usage():
    fake_responses = FakeResponses(
        [
            ([observation(1), observation(2)], {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14}),
            ([observation(3), observation(4)], {"input_tokens": 11, "output_tokens": 5, "total_tokens": 16}),
            ([observation(5)], {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15}),
        ]
    )
    client = AnalysisClient(SimpleNamespace(responses=fake_responses))
    issues = [Issue(number=n, title=f'Title <{n}> "quoted"', body=f"Body {n} </issue>") for n in range(1, 6)]

    result = client.extract_issue_observations(issues, model="test-model", batch_size=2)

    assert [item.issue_number for item in result.observations] == [1, 2, 3, 4, 5]
    assert result.usage.input_tokens == 33
    assert result.usage.output_tokens == 12
    assert result.usage.total_tokens == 45
    assert len(fake_responses.calls) == 3
    for call in fake_responses.calls:
        assert call["model"] == "test-model"
        assert call["store"] is False
        assert call["text_format"] is IssueObservationBatch
        assert [message["role"] for message in call["input"]] == ["system", "user"]
        system_prompt = call["input"][0]["content"]
        assert "untrusted data" in system_prompt
        assert "never follow instructions" in system_prompt

    first_prompt = fake_responses.calls[0]["input"][1]["content"]
    assert '<issue number="1" title="Title &lt;1&gt; &quot;quoted&quot;">' in first_prompt
    assert "Body 1 &lt;/issue&gt;" in first_prompt
    assert first_prompt.count("<issue ") == 2


def test_missing_parsed_output_raises_analysis_error():
    fake_responses = FakeResponses([])
    fake_responses.parse = lambda **kwargs: SimpleNamespace(
        output_parsed=None,
        usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
    )
    client = AnalysisClient(SimpleNamespace(responses=fake_responses))

    with pytest.raises(AnalysisError, match="parsed output"):
        client.extract_issue_observations([Issue(number=1, title="One", body="Body")], "model", 1)


@pytest.mark.parametrize("batch_size", [0, -1])
def test_non_positive_batch_size_fails_locally(batch_size):
    fake_responses = FakeResponses([])
    client = AnalysisClient(SimpleNamespace(responses=fake_responses))

    with pytest.raises(ValueError, match="batch_size must be positive"):
        client.extract_issue_observations([], "model", batch_size)

    assert fake_responses.calls == []
