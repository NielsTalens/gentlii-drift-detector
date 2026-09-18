from gentlii_drift_detector.parser import parse_issues


def test_parses_two_issue_sections() -> None:
    result = parse_issues(
        """# Completed issues

## Issue #12: First feature

### Body

First body.

---

## Issue #34: Second feature

### Body

Second body.
"""
    )

    assert [(issue.number, issue.title, issue.body) for issue in result.issues] == [
        (12, "First feature", "First body."),
        (34, "Second feature", "Second body."),
    ]


def test_extracts_closed_and_multiline_labels_metadata() -> None:
    result = parse_issues(
        """## Issue #7: Export reports

- Closed: 2026-08-20T12:30:00Z
- Labels:
  enhancement, customer-request

### Body

Export the report.
"""
    )

    issue = result.issues[0]
    assert issue.closed_at == "2026-08-20T12:30:00Z"
    assert issue.labels == ["enhancement", "customer-request"]


def test_preserves_markdown_headings_inside_body() -> None:
    result = parse_issues(
        """## Issue #8: Preserve structure

### Body

Intro.

#### Acceptance criteria

- Keep this heading.
"""
    )

    assert result.issues[0].body == (
        "Intro.\n\n#### Acceptance criteria\n\n- Keep this heading."
    )


def test_keeps_repeated_issue_numbers_as_separate_records() -> None:
    result = parse_issues(
        """## Issue #9: First occurrence

### Body

One.

## Issue #9: Second occurrence

### Body

Two.
"""
    )

    assert [issue.title for issue in result.issues] == [
        "First occurrence",
        "Second occurrence",
    ]


def test_empty_body_creates_record_and_warning() -> None:
    result = parse_issues("## Issue #10: Sparse issue\n\n### Body\n\n---\n")

    assert len(result.issues) == 1
    assert result.issues[0].body == ""
    assert any("#10" in warning and "empty body" in warning.lower() for warning in result.warnings)


def test_text_outside_issue_sections_creates_warning() -> None:
    result = parse_issues(
        """Unrecognized preface.

## Issue #11: Recognized issue

### Body

Useful content.

Trailing text cannot occur outside the final section.
"""
    )

    assert len(result.issues) == 1
    assert any("outside" in warning.lower() for warning in result.warnings)


def test_section_without_body_heading_is_kept_and_warned() -> None:
    result = parse_issues(
        """## Issue #13: Legacy export

- Closed: 2026-09-01T09:00:00Z

Body text without the expected heading.
"""
    )

    assert result.issues[0].body == "Body text without the expected heading."
    assert any("#13" in warning and "body heading" in warning.lower() for warning in result.warnings)
