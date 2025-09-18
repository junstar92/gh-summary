import fpdf
from datetime import datetime

from . import Commit, PullRequest


class PDF(fpdf.FPDF):
    def __init__(self, *, include_diffs: bool = False, max_diff_lines: int = 200, allowed_diff_exts: list[str] | None = None):
        super().__init__()
        self.set_font("Helvetica", size=11)
        self.set_auto_page_break(auto=True, margin=15)
        self.include_diffs = include_diffs
        self.max_diff_lines = max_diff_lines
        # Default extensions if none provided
        default_exts = [".py", ".c", ".cpp", ".md"]
        if allowed_diff_exts:
            # normalize to lowercase with leading dot
            norm: list[str] = []
            for e in allowed_diff_exts:
                e = e.strip().lower()
                if not e:
                    continue
                if not e.startswith('.'):
                    e = '.' + e
                norm.append(e)
            self.allowed_diff_exts = tuple(norm)
        else:
            self.allowed_diff_exts = tuple(default_exts)

    # --- Text safety helpers -------------------------------------------------
    def _to_pdf_safe(self, text: str) -> str:
        """Convert text to a Latin-1 compatible string for core PDF fonts.

        fpdf core fonts (Helvetica/Courier/Times) only support Latin-1. This
        replaces common Unicode punctuation/symbols and falls back to lossy
        replacement for anything else to avoid FPDFUnicodeEncodingException.
        """
        if not text:
            return ""

        repl = {
            "…": "...",
            "—": "--",
            "–": "-",
            "―": "-",
            "·": "*",
            "•": "*",
            "✓": "v",
            "✔": "v",
            "✗": "x",
            "×": "x",
            "→": "->",
            "←": "<-",
            "↔": "<->",
            "⇒": "=>",
            "⇐": "<=",
            "⇔": "<=>",
            "⟶": "->",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "′": "'",
            "″": '"',
            " ": " ",  # NBSP
            "	": "    ",
        }

        # Fast path: if it encodes, return as-is
        try:
            text.encode("latin-1")
            return text
        except Exception:
            pass

        # Apply simple replacements
        out = text
        for k, v in repl.items():
            if k in out:
                out = out.replace(k, v)

        # Final fallback: lossy conversion with replacement
        return out.encode("latin-1", "replace").decode("latin-1")

    def add_commits(self, commits: list[Commit]) -> None:
        """Add commits to the PDF document"""
        if not commits:
            return

        # Add title
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Commits Summary", ln=True, align="C")
        self.ln(5)

        # Add commit count
        self.set_font("Helvetica", "", 12)
        self.cell(0, 8, f"Total Commits: {len(commits)}", ln=True)
        self.ln(5)

        # Add each commit
        for i, commit in enumerate(commits, 1):
            self._add_single_commit(commit, i)

            # Add some space between commits
            if i < len(commits):
                self.ln(3)

    def _add_single_commit(self, commit: Commit, index: int) -> None:
        """Add a single commit to the PDF"""
        # Check if we need a new page
        if self.get_y() > self.h - 60:
            self.add_page()

        # Commit header
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, f"Commit #{index}", ln=True)

        # Repository
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, self._to_pdf_safe(f"Repository: {commit.repo_name}"), ln=True)

        # SHA
        self.set_font("Helvetica", "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Commit ID: {commit.sha}", ln=True)
        self.set_text_color(0, 0, 0)

        # Date
        self.set_font("Helvetica", "", 10)
        commit_date = datetime.fromisoformat(commit.date.replace("Z", "+00:00"))
        formatted_date = commit_date.strftime("%Y-%m-%d %H:%M:%S")
        self.cell(0, 6, f"Date: {formatted_date}", ln=True)

        # Author
        self.cell(0, 6, f"Author: {commit.author}", ln=True)

        # Message
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, "Message:", ln=True)
        self.set_font("Helvetica", "", 10)

        # Handle long commit messages by wrapping text
        message_lines = self._wrap_text(commit.message, 80)
        for line in message_lines:
            self.cell(0, 5, self._to_pdf_safe(line), ln=True)

        # URL (optional, can be long)
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 255)
        self.cell(0, 4, self._to_pdf_safe(f"URL: {commit.html_url}"), ln=True)
        self.set_text_color(0, 0, 0)

        # Add separator line
        self.ln(2)

        # Optional diff (GitHub-style)
        if self.include_diffs and commit.diff:
            self.set_font("Helvetica", "B", 10)
            self.cell(0, 6, "Diff:", ln=True)
            self._render_github_style_diff(commit.diff)

        self.line(10, self.get_y(), self.w - 10, self.get_y())

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        """Wrap text to fit within max_width characters, preserving line breaks"""
        if not text:
            return []

        # Split by actual line breaks first
        paragraphs = text.split("\n")
        lines = []

        for paragraph in paragraphs:
            # Handle carriage returns within paragraphs
            paragraph = paragraph.replace("\r", "")

            if not paragraph.strip():
                # Empty line - add as blank line
                lines.append("")
                continue

            # Split paragraph into words
            words = paragraph.split()
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "

            if current_line:
                lines.append(current_line.strip())

        return lines

    def add_prs(self, prs: list[PullRequest]) -> None:
        """Add pull requests to the PDF document"""
        if not prs:
            return

        # Add title
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Pull Requests Summary", ln=True, align="C")
        self.ln(5)

        # Add PR count
        self.set_font("Helvetica", "", 12)
        self.cell(0, 8, f"Total Pull Requests: {len(prs)}", ln=True)
        self.ln(5)

        # Add each PR
        for i, pr in enumerate(prs, 1):
            self._add_single_pr(pr, i)

            # Add some space between PRs
            if i < len(prs):
                self.ln(3)

    def _add_single_pr(self, pr: PullRequest, index: int) -> None:
        """Add a single pull request to the PDF"""
        # Check if we need a new page
        if self.get_y() > self.h - 80:
            self.add_page()

        # PR header
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, f"Pull Request #{index}", ln=True)

        # Repository URL (extract repo name)
        self.set_font("Helvetica", "B", 10)
        repo_name = pr.repo_url.split("/")[-2] + "/" + pr.repo_url.split("/")[-1]
        self.cell(0, 6, self._to_pdf_safe(f"Repository: {repo_name}"), ln=True)

        # Title
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "Title:", ln=True)
        self.set_font("Helvetica", "", 10)
        title_lines = self._wrap_text(pr.title, 80)
        for line in title_lines:
            self.cell(0, 5, self._to_pdf_safe(line), ln=True)

        # Merge date
        self.set_font("Helvetica", "", 10)
        if pr.merged_at:
            merge_date = datetime.fromisoformat(pr.merged_at.replace("Z", "+00:00"))
            formatted_date = merge_date.strftime("%Y-%m-%d %H:%M:%S")
            self.cell(0, 6, f"Merged: {formatted_date}", ln=True)

        # Body/Description
        if pr.body:
            self.ln(2)
            self.set_font("Helvetica", "B", 10)
            self.cell(0, 6, "Description:", ln=True)
            self.set_font("Helvetica", "", 10)

            # Handle long descriptions by wrapping text
            body_lines = self._wrap_text(pr.body, 80)
            for line in body_lines:
                self.cell(0, 5, self._to_pdf_safe(line), ln=True)

        # URLs
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 255)
        self.cell(0, 4, self._to_pdf_safe(f"PR URL: {pr.html_url}"), ln=True)
        self.cell(0, 4, self._to_pdf_safe(f"Diff URL: {pr.diff_url}"), ln=True)
        self.set_text_color(0, 0, 0)

        # Add separator line
        self.ln(2)

        # Optional diff (GitHub-style)
        if self.include_diffs and pr.diff:
            self.set_font("Helvetica", "B", 10)
            self.cell(0, 6, "Diff:", ln=True)
            self._render_github_style_diff(pr.diff)

        self.line(10, self.get_y(), self.w - 10, self.get_y())

    def _render_github_style_diff(self, diff_text: str) -> None:
        """Render unified diff similar to GitHub UI.

        - Per-file sections
        - Hunk headers
        - Inline rows with columns: sign | old | new | content
        - Colored backgrounds for additions/deletions
        - Line numbers
        - Truncation by max_diff_lines
        """
        if not diff_text:
            return

        files = self._parse_unified_diff(diff_text)

        # Filter: include only code and markdown files
        def _allowed(path: str) -> bool:
            if not path:
                return False
            p = path.lower()
            return any(p.endswith(ext) for ext in self.allowed_diff_exts)

        filtered = []
        for f in files:
            path = f.get("b_path") or f.get("a_path") or f.get("display") or ""
            if _allowed(path):
                filtered.append(f)
        files = filtered

        if not files:
            return

        # Layout constants
        self.set_font("Courier", size=8)
        row_h = 4
        col_sign = 5
        col_old = 12
        col_new = 12
        gap = 1
        start_x = self.l_margin
        usable_w = self.w - self.r_margin - start_x
        col_content = max(20, usable_w - (col_sign + col_old + col_new + gap * 3))

        processed_lines = 0
        line_limit = max(0, int(self.max_diff_lines))

        for f in files:
            # File header
            if self.get_y() > self.h - 40:
                self.add_page()
                self.set_font("Courier", size=8)

            self.set_font("Helvetica", "B", 9)
            self.set_text_color(0, 0, 0)
            display = f.get("display", f.get("b_path") or f.get("a_path") or f.get("name", ""))
            self.cell(0, 5, self._to_pdf_safe(display), ln=True)
            self.set_font("Courier", size=8)

            for h in f.get("hunks", []):
                if line_limit and processed_lines >= line_limit:
                    break

                # Hunk header
                if self.get_y() > self.h - 20:
                    self.add_page()
                    self.set_font("Courier", size=8)
                self.set_fill_color(246, 248, 250)  # light gray
                self.set_text_color(88, 96, 105)
                header = self._to_pdf_safe(h["header_raw"])  # may contain Unicode symbols
                # Full-width header
                self.cell(0, row_h, header, ln=True, fill=True)

                old_ln = h["old_start"]
                new_ln = h["new_start"]

                for kind, text in h["lines"]:
                    if line_limit and processed_lines >= line_limit:
                        break

                    # Page break handling
                    if self.get_y() > self.h - 20:
                        self.add_page()
                        self.set_font("Courier", size=8)

                    # Determine style
                    if kind == "+":
                        fill = (230, 255, 237)  # green bg
                        sign_color = (3, 102, 3)
                        old_str = ""
                        new_str = str(new_ln)
                        new_ln += 1
                    elif kind == "-":
                        fill = (255, 238, 240)  # red bg
                        sign_color = (158, 0, 6)
                        old_str = str(old_ln)
                        new_str = ""
                        old_ln += 1
                    else:  # context
                        fill = (255, 255, 255)
                        sign_color = (110, 119, 129)
                        old_str = str(old_ln)
                        new_str = str(new_ln)
                        old_ln += 1
                        new_ln += 1

                    # Draw row: sign | old | new | content
                    self.set_fill_color(*fill)
                    # sign
                    self.set_text_color(*sign_color)
                    self.cell(col_sign, row_h, kind if kind in "+-" else " ", border=0, ln=0, fill=True)

                    # line numbers
                    self.set_text_color(110, 119, 129)
                    self.cell(col_old, row_h, old_str, border=0, ln=0, fill=True, align="R")
                    self.cell(gap, row_h, "", ln=0)
                    self.cell(col_new, row_h, new_str, border=0, ln=0, fill=True, align="R")
                    self.cell(gap, row_h, "", ln=0)

                    # content (truncate to fit)
                    self.set_text_color(0, 0, 0)
                    content = self._truncate_to_width(text, col_content)
                    self.cell(col_content, row_h, content, border=0, ln=1, fill=True)

                    processed_lines += 1

            # small spacing between files
            self.ln(1)

        if line_limit and processed_lines >= line_limit:
            self.set_text_color(100, 100, 100)
            self.set_font("Helvetica", size=8)
            self.cell(0, 5, self._to_pdf_safe("... diff truncated (line limit)"), ln=True)

        # Restore body font
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", size=11)

    def _truncate_to_width(self, text: str, width: float) -> str:
        """Truncate text with ellipsis so it fits within width in current font."""
        text = self._to_pdf_safe(text)
        if self.get_string_width(text) <= width:
            return text
        lo, hi = 0, len(text)
        ell = "..."
        # Binary search longest prefix that fits with ellipsis
        while lo < hi:
            mid = (lo + hi + 1) // 2
            s = text[:mid] + ell
            if self.get_string_width(s) <= width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + ell

    def _parse_unified_diff(self, diff_text: str) -> list[dict]:
        """Parse unified diff text into a list of file dicts with hunks.

        Returns: [{display, a_path, b_path, hunks:[{header_raw, old_start, new_start, lines:[(kind, text), ...]}]}]
        """
        files: list[dict] = []
        cur: dict | None = None
        hunks: list | None = None
        lines = diff_text.splitlines()
        for ln in lines:
            if ln.startswith("diff --git "):
                # push previous
                if cur is not None:
                    cur["hunks"] = hunks or []
                    files.append(cur)
                parts = ln.split()
                a_path = parts[2][2:] if len(parts) > 2 else ""
                b_path = parts[3][2:] if len(parts) > 3 else a_path
                name = b_path or a_path
                cur = {"a_path": a_path, "b_path": b_path, "display": name}
                hunks = []
            elif ln.startswith("@@ ") and cur is not None:
                # parse hunk header
                header_raw = ln
                try:
                    # @@ -old_start,old_count +new_start,new_count @@
                    header = ln.split("@@")[1].strip()
                    left, right = header.split(" ")[:2]
                    old_start = int(left.split(",")[0].lstrip("-"))
                    new_start = int(right.split(",")[0].lstrip("+"))
                except Exception:
                    old_start = new_start = 0
                hunks.append({"header_raw": header_raw, "old_start": old_start, "new_start": new_start, "lines": []})
            elif hunks is not None and hunks:
                # lines within current hunk or headers before first hunk
                if ln.startswith(("+", "-", " ")):
                    kind = ln[0]
                    text = ln[1:]
                    hunks[-1]["lines"].append((kind, text))
                else:
                    # ignore misc headers like --- / +++ or index lines
                    continue

        # push last file
        if cur is not None:
            cur["hunks"] = hunks or []
            files.append(cur)

        return files
