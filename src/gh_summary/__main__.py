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

    pdf = PDF()
    pdf.add_prs(prs)
    pdf.add_commits(commits)
    pdf.output(save_path)

    print(f"PDF generated successfully: {save_path}")
