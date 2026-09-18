# CLI Progress Output Design

The CLI will report non-sensitive progress to stderr so stdout remains suitable for final output paths and automation. It will show parsing and issue counts, warnings, extraction batch progress, synthesis, and output publication. Messages will never include issue bodies, prompts, generated claims, API keys, or other secret values.

Progress is enabled by default and can be disabled with `--quiet`. Existing exit codes, output files, and analysis behavior remain unchanged. Extraction receives a callback for batch progress rather than writing directly to the analysis layer, keeping the OpenAI adapter reusable and testable.
