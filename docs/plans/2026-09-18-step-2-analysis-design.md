# Step 2 Analysis PoC Design

## Purpose

Build a Python command-line proof of concept that analyzes a user-provided Markdown file containing completed GitHub issues. The tool implements only Step 2 from the project scope: infer the observed strategy and product vision from delivered work.

GitHub retrieval is out of scope. The user prepares the Markdown input separately, using issues completed during the selected period. The first experiment covers only 2026 and does not analyze changes between years.

## Command-line interface

The primary interface is:

```text
drift-detector INPUT.md --output OUTPUT_DIR [--model MODEL] [--batch-size SIZE]
```

The default model is `gpt-5.6-terra`. The output directory contains:

```text
analysis.json
report.md
```

The CLI is intentionally permissive for this PoC. It parses issue sections on a best-effort basis, processes repeated issue numbers as supplied, retains sparse issues, and reports parsing warnings without enforcing strict input validation.

## Expected input

The Markdown should contain one issue per level-two heading. The preferred shape is:

```markdown
## Issue #123: Short issue title

- Closed: 2026-03-14T10:32:00Z
- Labels: enhancement, customer-request

### Body

Full issue body.

---
```

The issue number, title, and full body provide the useful evidence. Completion date and labels are optional context. Issue numbers are the only references shown in analysis results.

## Architecture and data flow

1. Read the Markdown locally and split it into issue sections.
2. Retrieve the OpenAI API key in memory with:

   ```bash
   secret-tool lookup key GNTL_DD app gentlii-drift-detection
   ```

3. Analyze issues in token-conscious batches using the OpenAI Responses API and Structured Outputs.
4. Produce compact, structured observations for each issue.
5. Send only those observations—not the original issue bodies—to a synthesis request.
6. Render the structured synthesis to JSON and Markdown.
7. Write final outputs atomically so a failed run does not leave misleading final reports.

OpenAI requests use `store: false`. The secret is never printed, logged, written to disk, or passed as a command-line argument.

## Stage 1: issue evidence extraction

For each issue, Stage 1 records:

- Issue number and title
- Delivery assessment: `delivered`, `not_delivered`, or `uncertain`
- Customer or user needs addressed
- Product capabilities strengthened
- Candidate strategic goals
- Investment themes
- Product-direction signals
- Short evidence summaries grounded in the issue body
- Confidence level

Rejected, duplicate, cancelled, or otherwise undelivered work does not influence synthesis when the available text makes that status clear. Sparse or ambiguous issues remain visible and are marked as uncertain or insufficient evidence.

Issue bodies are untrusted evidence. Prompts explicitly instruct the model not to follow instructions embedded in issue content.

## Stage 2: synthesis

Stage 2 consumes the compact Stage 1 observations and produces:

- Observed strategy
- Observed strategic goals
- Observed product vision
- Recurring customer or user needs
- Product capabilities receiving investment
- Recurring investment themes
- Important uncertainties and evidence gaps

Every synthesized claim includes supporting issue numbers such as `#123`. The result distinguishes evidence-supported observations from inference and does not claim intent unsupported by the completed work.

## Outputs

`analysis.json` is the reusable artifact for later Steps 3 and 4. It contains run metadata, parsing warnings, per-issue Stage 1 observations, the Stage 2 synthesis, issue-number evidence, and API token usage when available.

`report.md` is a human-readable rendering of the Stage 2 synthesis. It emphasizes the observed strategy, goals, and product vision, followed by supporting needs, capabilities, themes, issue evidence, and uncertainties.

## Failure handling

The CLI will:

- Fail clearly when the input cannot be read, the key is unavailable, or OpenAI returns a permanent error.
- Retry temporary network, rate-limit, and server failures with bounded backoff.
- Preserve useful parsing warnings rather than rejecting imperfect input.
- Avoid producing final output files when analysis does not complete.
- Never expose the API key in an exception or diagnostic message.

## Verification

Automated tests will use fakes rather than real OpenAI requests. They will cover:

- Best-effort Markdown parsing
- Sparse and repeated issue handling
- Batch construction
- Secret lookup success and failure
- Structured Stage 1 extraction
- Stage 2 synthesis
- Markdown and JSON rendering
- Temporary failure retries and permanent failure reporting
- Secret redaction and atomic output behavior

A manual smoke test with the user-provided Markdown will assess the main PoC goal: whether the resulting observed strategy and vision are useful and credibly supported by issue numbers.

## Out of scope

- GitHub authentication or issue retrieval
- Multi-year grouping or direction-of-change analysis
- Comparison against intended strategy or vision
- Drift scoring or Step 3/4 implementation
- Production-grade input normalization, resumability, caching, or cost optimization
