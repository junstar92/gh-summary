gh-summary
=========

Generate a concise PDF summarizing your GitHub activity — merged pull requests and commits — for a given author and date range. Optionally include unified diffs with simple, GitHub‑style rendering.

Features
-
- Collects merged PRs and commits for a GitHub user
- Filters by date range and repository (include or exclude)
- Exports a single, shareable PDF
- Optional diffs with GitHub‑like formatting
- Private repo support when authenticated
- Diff file filtering by extension (defaults to .py, .c, .cpp, .md)

Requirements
-
- Python 3.10+
- A GitHub token with appropriate scopes
  - Private repos: token should include the `repo` scope and be SSO‑authorized if required by your org
- Optional but recommended: GitHub CLI (`gh`) for seamless auth

Install
-
Install from the project root:

```
pip install .
```

This installs the `gh-summary` command.

Authentication
-
`gh-summary` accepts a token via `--token`. If omitted, it tries `gh auth token` from the GitHub CLI.

- Use `--token <YOUR_TOKEN>` to pass a token explicitly
- Or run `gh auth login` once, then rely on `gh auth token`

The tool uses GitHub’s REST API for search and for fetching diffs. API endpoints honor `Authorization: Bearer <token>`, which is required to access private repositories.

Usage
-
Basic example (author is required):

```
gh-summary -a your-github-username -s 2024-07-01 -e 2024-07-31 -d
```

This creates `./summary.pdf` containing merged PRs and commits in July 2024, including diffs for selected file types.

Key options
-
- `--author, -a` (required): GitHub username to query
- `--start-date, -s` / `--end-date, -e`: Date range (YYYY-MM-DD)
- `--filename, -f`: Output base name (default: `summary`)
- `--filepath, -p`: Output directory (default: `./`)
- `--include-diff, -d`: Fetch and embed diffs
- `--max-diff-lines`: Limit diff rows per item (default: 200)
- `--diff-extensions, -D`: File extensions to include in diffs (default: `.py .c .cpp .md`)
- `--include-repo, -i`: Only include these repos (space‑separated)
- `--exclude-repo, -x`: Exclude these repos (space‑separated)

Repository filters `--include-repo` and `--exclude-repo` are mutually exclusive.

Examples
-
Only public data, no diffs:

```
gh-summary -a octocat -s 2024-01-01 -e 2024-03-31
```

Include diffs for Python and Markdown only:

```
gh-summary -a yourname -s 2024-07-01 -e 2024-07-31 -d -D .py .md
```

Comma‑separated extension input also works:

```
gh-summary -a yourname -d -D py,md,c,cpp
```

Include only specific repositories:

```
gh-summary -a yourname -s 2024-07-01 -e 2024-07-31 \
  -i yourorg/service-a yourorg/tooling
```

Exclude some repositories:

```
gh-summary -a yourname -s 2024-07-01 -e 2024-07-31 \
  -x yourorg/scratch yourorg/experimental
```

Output location and name:

```
gh-summary -a yourname -s 2024-07-01 -e 2024-07-31 \
  -f july-summary -p ./reports
```

How it works
-
- Queries GitHub Search API for:
  - Commits: `author:<user>` with optional `author-date:<range>`
  - PRs: `type:pr is:merged author:<user>` with optional `merged:<range>`
- Generates a PDF with sections for PRs and commits
- If `-d/--include-diff` is set:
  - Fetches unified diffs via API endpoints using `Accept: application/vnd.github.v3.diff`
  - Renders diffs with GitHub‑style visuals (line numbers, +/- markers, colored rows)
  - Applies a per‑item line limit (`--max-diff-lines`)
  - Includes only files matching the configured extensions (`--diff-extensions`)

Notes on fonts and Unicode
-
The PDF uses core fonts for portability. These fonts are Latin‑1 only. The renderer converts common Unicode symbols (e.g., smart quotes, arrows, ellipses) to ASCII equivalents to avoid font errors. If you need full Unicode rendering (e.g., emoji), contribute a font setup using a Unicode TTF and `fpdf2`’s `add_font(..., uni=True)`.

Permissions and rate limits
-
- Private repos require a token with `repo` scope and, if applicable, SSO authorization
- Search API has rate limits; using a token increases limits

Troubleshooting
-
- 404 when fetching diffs for private repos
  - Ensure you’re authenticated (via `--token` or `gh auth login`)
  - Token must have `repo` scope and be SSO‑authorized
- PDF generation fails with a Unicode font error
  - This project converts common symbols to ASCII; if you still see issues, please open an issue with an example diff or consider adding a Unicode font
- Empty PDF or missing items
  - Confirm the date range and author
  - Check repo include/exclude filters

Development
-
Create a virtual environment and install in editable mode:

```
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run from source (after editable install):

```
gh-summary -h
```

Project Structure
-
- `src/gh_summary/__main__.py` — CLI, argument parsing, orchestration
- `src/gh_summary/commit.py` — commit model and fetch helpers
- `src/gh_summary/pr.py` — PR model and fetch helpers
- `src/gh_summary/pdf.py` — PDF generation and diff rendering

License
-
MIT. See `LICENSE`.
