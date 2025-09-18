import argparse
import os
import subprocess

from . import Commit, PullRequest, PDF


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", type=str, default="", help="GitHub API token")
    parser.add_argument("--author", "-a", type=str, required=True, help="Account name to query")
    parser.add_argument("--start-date", "-s", type=str, default=None, help="Start date to query (YYYY-MM-DD)")
    parser.add_argument("--end-date", "-e", type=str, default=None, help="End date to query (YYYY-MM-DD)")
    parser.add_argument("--filename", "-f", type=str, default="summary", help="Output file name")
    parser.add_argument("--filepath", "-p", type=str, default="./", help="Output file path")
    parser.add_argument("--include-diff", "-d", action="store_true", help="Fetch and include diff blocks in PDF")
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=200,
        help="Maximum diff lines to render per item",
    )
    parser.add_argument(
        "--diff-extensions",
        "-D",
        type=str,
        nargs="*",
        default=None,
        help="File extensions to include in diffs (e.g. .py .c .cpp .md). Defaults to .py .c .cpp .md if omitted",
    )

    repo = parser.add_mutually_exclusive_group()
    repo.add_argument("--include-repo", "-i", type=str, nargs="*", default=None, help="Repository name to include")
    repo.add_argument("--exclude-repo", "-x", type=str, nargs="*", default=None, help="Repository name to exclude")

    return parser.parse_args()


def get_gh_auth_token() -> str:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    except FileNotFoundError:
        raise FileNotFoundError("gh is not installed. Please install gh from https://cli.github.com or set --token")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error occurred while getting gh auth token.\nstderr: {e.strerr.strip()}")


def get_date_range(*, start_date: str = None, end_date: str = None) -> str | None:
    if not start_date and not end_date:
        return None

    if start_date and not end_date:
        return f">={start_date}"

    if not start_date and end_date:
        return f"<={end_date}"

    return f"{start_date}..{end_date}"


def get_save_path(filepath: str, filename: str) -> str:
    if not os.path.exists(filepath):
        os.makedirs(filepath, exist_ok=True)

    return os.path.abspath(os.path.join(filepath, f"{filename}.pdf"))


def main() -> None:
    args = parse_args()
    token = args.token or get_gh_auth_token()
    date_range = get_date_range(start_date=args.start_date, end_date=args.end_date)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-Github-Api-Version": "2022-11-28",
    }

    QUERY_COMMIT_URL = f"https://api.github.com/search/commits?q=author:{args.author}"
    if date_range:
        QUERY_COMMIT_URL += f"+author-date:{date_range}"

    commits = Commit.from_url(
        QUERY_COMMIT_URL, headers=headers, include_repos=args.include_repo, exclude_repos=args.exclude_repo
    )

    QUERY_PR_URL = f"https://api.github.com/search/issues?q=type:pr+is:merged+author:{args.author}"
    if date_range:
        QUERY_PR_URL += f"+merged:{date_range}"

    prs = PullRequest.from_url(
        QUERY_PR_URL, headers=headers, include_repos=args.include_repo, exclude_repos=args.exclude_repo
    )

    save_path = get_save_path(args.filepath, args.filename)

    # Optionally fetch diffs
    if args.include_diff:
        fetch_diffs_for_commits(commits, token)
        fetch_diffs_for_prs(prs, token)

    # Normalize diff extensions: ensure they start with '.' and are lowercase
    diff_exts = None
    if args.diff_extensions:
        tmp: list[str] = []
        for item in args.diff_extensions:
            # Allow comma-separated input as a convenience
            parts = [p.strip() for p in item.split(",") if p.strip()]
            for p in parts:
                if not p.startswith('.'):
                    p = '.' + p
                tmp.append(p.lower())
        diff_exts = tmp or None

    pdf = PDF(include_diffs=args.include_diff, max_diff_lines=args.max_diff_lines, allowed_diff_exts=diff_exts)
    pdf.add_prs(prs)
    pdf.add_commits(commits)
    pdf.output(save_path)

    print(f"PDF generated successfully: {save_path}")


def _auth_headers_for_diff(token: str) -> dict[str, str]:
    # Use diff-specific Accept; GitHub honors auth to avoid rate limits/private repos
    return {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"Bearer {token}",
        "X-Github-Api-Version": "2022-11-28",
    }


def fetch_diffs_for_commits(commits: list[Commit], token: str) -> None:
    import requests

    headers = _auth_headers_for_diff(token)
    for c in commits:
        try:
            # Use the API endpoint so Authorization works for private repos
            url = c.api_diff_url
            res = requests.get(url, headers=headers, timeout=30)
            if res.ok and res.text:
                c.diff = res.text
            elif not res.ok:
                # Fallback to .diff on HTML URL (may work for public repos)
                fallback = c.diff_url
                res2 = requests.get(fallback, headers=headers, timeout=30)
                if res2.ok and res2.text:
                    c.diff = res2.text
        except Exception:
            # Non-fatal; skip diff on error
            continue


def fetch_diffs_for_prs(prs: list[PullRequest], token: str) -> None:
    import requests

    headers = _auth_headers_for_diff(token)
    for pr in prs:
        try:
            # Use the API endpoint so Authorization works for private repos
            url = pr.api_url
            res = requests.get(url, headers=headers, timeout=30)
            if res.ok and res.text:
                pr.diff = res.text
            elif not res.ok:
                # Fallback to .diff on HTML URL in case repo is public
                res2 = requests.get(pr.diff_url, headers=headers, timeout=30)
                if res2.ok and res2.text:
                    pr.diff = res2.text
        except Exception:
            # Non-fatal; skip diff on error
            continue
