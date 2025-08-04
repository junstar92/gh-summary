import fpdf
from datetime import datetime

from . import Commit, PullRequest


class PDF(fpdf.FPDF):
    def __init__(self):
        super().__init__()
        self.set_font("Helvetica", size=11)
        self.set_auto_page_break(auto=True, margin=15)

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
        self.cell(0, 6, f"Repository: {commit.repo_name}", ln=True)

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
            self.cell(0, 5, line, ln=True)

        # URL (optional, can be long)
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 255)
        self.cell(0, 4, f"URL: {commit.html_url}", ln=True)
        self.set_text_color(0, 0, 0)

        # Add separator line
        self.ln(2)
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
        self.cell(0, 6, f"Repository: {repo_name}", ln=True)

        # Title
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "Title:", ln=True)
        self.set_font("Helvetica", "", 10)
        title_lines = self._wrap_text(pr.title, 80)
        for line in title_lines:
            self.cell(0, 5, line, ln=True)

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
                self.cell(0, 5, line, ln=True)

        # URLs
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0, 0, 255)
        self.cell(0, 4, f"PR URL: {pr.html_url}", ln=True)
        self.cell(0, 4, f"Diff URL: {pr.diff_url}", ln=True)
        self.set_text_color(0, 0, 0)

        # Add separator line
        self.ln(2)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
