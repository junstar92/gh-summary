import json
import requests
from typing import Any
from pydantic import BaseModel


class Commit(BaseModel):
    sha: str
    html_url: str
    repo_url: str
    repo_name: str
    author: str
    committer: str
    date: str
    message: str

    @classmethod
    def from_json(cls, json_data: dict[str, Any]) -> "Commit":
        return cls(
            sha=json_data["sha"],
            html_url=json_data["html_url"],
            repo_url=json_data["repository"]["html_url"],
            repo_name=json_data["repository"]["full_name"],
            author=json_data["commit"]["author"]["name"],
            committer=json_data["commit"]["committer"]["name"],
            date=json_data["commit"]["committer"]["date"],
            message=json_data["commit"]["message"],
        )

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        include_repos: tuple[str, ...] | None = None,
        exclude_repos: tuple[str, ...] | None = None,
    ) -> "list[Commit]":
        res = requests.get(url, headers=headers)
        data = json.loads(res.text)

        def should_include_repo(repo_name: str) -> bool:
            if include_repos:
                return repo_name in include_repos
            if exclude_repos:
                return repo_name not in exclude_repos
            return True

        return sorted(
            [cls.from_json(item) for item in data["items"] if should_include_repo(item["repository"]["full_name"])],
            key=lambda x: x.date,
        )
