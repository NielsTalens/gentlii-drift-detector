  gh issue list \
    --repo OWNER/REPOSITORY
     \
    --state closed \
    --search 'closed:>=2026-01-01' \
    --limit 1000 \
    --json number,title,body,labels,closedAt \
    --jq '.[] | "## Issue #\(.number): \(.title)\n\n- Closed: \(.closedAt)\n- Labels:
    \([.labels[].name] | join(", "))\n\n### Body\n\n\(.body)\n\n---\n"' \
    > issues-2026.md
    