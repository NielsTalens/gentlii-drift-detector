import re

from gentlii_drift_detector.models import Issue, ParseResult


ISSUE_HEADING = re.compile(
    r"(?m)^##[ \t]+Issue[ \t]+#(?P<number>\d+)(?::|[ \t]+[-—])[ \t]*(?P<title>.*)$"
)
BODY_HEADING = re.compile(r"(?m)^###[ \t]+Body[ \t]*$")
CLOSED_METADATA = re.compile(r"(?m)^-[ \t]+Closed:[ \t]*(?P<value>.*)$")
LABELS_METADATA = re.compile(
    r"(?m)^-[ \t]+Labels:[ \t]*(?P<inline>.*)(?P<continuations>(?:\n[ \t]+[^\n]*)*)"
)
FINAL_SEPARATOR = re.compile(r"(?:^|\n)[ \t]*---[ \t]*$")


def parse_issues(markdown: str) -> ParseResult:
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(ISSUE_HEADING.finditer(markdown))
    warnings: list[str] = []

    if not matches:
        if markdown.strip():
            warnings.append("Text outside recognizable issue sections was ignored.")
        return ParseResult(warnings=warnings)

    if markdown[: matches[0].start()].strip():
        warnings.append("Text outside recognizable issue sections was ignored.")

    issues: list[Issue] = []
    for index, match in enumerate(matches):
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        section = markdown[match.end() : section_end]
        number = int(match.group("number"))
        metadata, body, has_body_heading = _split_section(section)

        if not has_body_heading:
            warnings.append(f"Issue #{number} has no ### Body heading; remaining content was used.")
            body = _remove_metadata(body)

        body = _remove_final_separator(body).strip()
        if not body:
            warnings.append(f"Issue #{number} has an empty body.")

        issues.append(
            Issue(
                number=number,
                title=match.group("title").strip(),
                body=body,
                closed_at=_closed_at(metadata),
                labels=_labels(metadata),
            )
        )

    return ParseResult(issues=issues, warnings=warnings)


def _split_section(section: str) -> tuple[str, str, bool]:
    body_heading = BODY_HEADING.search(section)
    if body_heading is None:
        return section, section, False
    return section[: body_heading.start()], section[body_heading.end() :], True


def _closed_at(metadata: str) -> str | None:
    match = CLOSED_METADATA.search(metadata)
    if match is None:
        return None
    return match.group("value").strip() or None


def _labels(metadata: str) -> list[str]:
    match = LABELS_METADATA.search(metadata)
    if match is None:
        return []

    values = [match.group("inline")]
    values.extend(match.group("continuations").splitlines())
    return [label.strip() for value in values for label in value.split(",") if label.strip()]


def _remove_metadata(section: str) -> str:
    section = CLOSED_METADATA.sub("", section)
    return LABELS_METADATA.sub("", section)


def _remove_final_separator(body: str) -> str:
    return FINAL_SEPARATOR.sub("", body.rstrip())
