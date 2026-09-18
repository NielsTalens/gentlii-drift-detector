# Gentlii Drift Detector

## Discover the strategy your backlog is actually executing

The work that has already been completed can reveal a great deal about the strategy and product vision that have actually been executed.

**Drift Detection** analyses completed work over a selectable period and derives the **Observed Strategy** and **Observed Product Vision** from what has actually been delivered.

It then compares these observed outcomes with the **Intended Strategy** and **Intended Product Vision** to identify where strategic drift has occurred.

## Process

### Step 1 — Retrieve completed work

- Retrieve all completed backlog items for the selected period.
- Group the completed work by year to make changes in direction visible over time.
- This provides an overview of how priorities, focus areas, and strategic direction may have shifted over the years.

### Step 2 — Extract the observed strategy and product vision

Analyse the completed work and determine:

- Which strategic goals the work appears to support
- Which customer or user needs are being addressed
- Which product capabilities are being strengthened
- Which themes consistently receive investment
- What product direction emerges from the delivered work

Based on this analysis, formulate:

- **Observed Strategy**
- **Observed Strategic Goals**
- **Observed Product Vision**\

### Step 3 — Compare intended and observed strategy

Compare the extracted **Observed Strategy** and **Observed Product Vision** against the documented **Intended Strategy** and **Intended Product Vision**

Identify where the actual execution:

- Aligns with the intended direction
- Partially supports the intended direction
- Introduces a different direction
- No longer supports previously defined strategic goals

### Step 4 — Identify strategic drift

Determine where the intended and observed strategy diverge.

The result should describe:

- **Strategic Drift** — where execution differs from the intended strategy
- **Vision Drift** — where the delivered product differs from the intended product vision
- **Drift Signals** — specific completed backlog items or recurring patterns that demonstrate the divergence
- **Direction of Change** — how the observed strategy has shifted over time

The goal is not only to determine whether drift exists, but to make visible **which strategy the organisation has actually been executing through its delivered work**.

## Step 2 proof of concept

The current CLI implements **Step 2 only**. It analyzes one user-prepared Markdown file as a single period; it does not retrieve GitHub issues, compare years, or perform Steps 3 and 4. The parser is intentionally best-effort for this proof of concept, so imperfect and sparse issue sections may produce warnings rather than stop the run.

### Install and run

Python 3.11 or newer is required:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/drift-detector issues-2026.md --output results/
```

The default model is `gpt-5.6-terra`. Use `--model MODEL` to select another model and `--batch-size SIZE` to change the number of issues sent in each extraction request (the default is 10):

```bash
.venv/bin/drift-detector issues-2026.md --output results/ \
  --model gpt-5.6-terra --batch-size 10
```

Progress is printed to stderr while parsing, extracting batches, synthesizing, and writing outputs. Use `--quiet` to suppress progress while retaining warnings and errors.

### Store the API key

The CLI loads the OpenAI API key from the desktop keyring with the exact command `secret-tool lookup key GNTL_DD app gentlii-drift-detection`. It keeps the returned key in memory and never logs or persists it.

Store the key through standard input so it does not appear in the command itself or shell history:

```bash
bash -c 'read -r -s -p "OpenAI API key: " key
printf "\n"
printf "%s" "$key" | secret-tool store \
  --label="Gentlii Drift Detector OpenAI API key" \
  key GNTL_DD app gentlii-drift-detection'
```

Press Enter after typing the key. Your keyring may ask you to unlock it. Avoid placing the key directly in a command, environment file, or committed file.

### Input format

Use one level-two issue heading per issue. The issue number, title, and body are the useful evidence; `Closed` and `Labels` are optional metadata.

```markdown
## Issue #123: Short issue title

- Closed: 2026-03-14T10:32:00Z
- Labels: enhancement, customer-request

### Body

Full issue body here.

---
```

A sanitized two-issue example is available at [`tests/fixtures/issues.md`](tests/fixtures/issues.md).

### Data sent to OpenAI and outputs

Analysis uses two stages. First, the issue title, body, and available metadata are sent to OpenAI in batches to derive compact observations. Second, those derived observations are sent back to OpenAI for synthesis. Requests set `store: false`. Issue content is therefore disclosed to OpenAI for analysis even though it is not copied into the reports.

The output directory contains:

- `analysis.json`: structured per-issue observations, synthesis, evidence issue numbers, warnings, and token usage for reuse in later steps.
- `report.md`: a human-readable synthesis with issue-number evidence.

The program does not directly copy raw issue bodies into either file. Model-generated output may nevertheless quote or closely reproduce submitted content, so treat both outputs as potentially sensitive. Review them as model-generated analysis rather than a statement of organizational intent.
