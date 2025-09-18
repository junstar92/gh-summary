import json
import requests
from typing import Any
from pydantic import BaseModel


class PullRequest(BaseModel):
    repo_url: str
    html_url: str
    diff_url: str
    api_url: str
    merged_at: str
    title: str
    body: str
    diff: str = ""

    @classmethod
    def from_json(cls, json_data: dict[str, Any]) -> "PullRequest":
        return cls(
            repo_url=json_data["repository_url"],
            html_url=json_data["pull_request"]["html_url"],
            diff_url=json_data["pull_request"]["diff_url"],
            api_url=json_data["pull_request"]["url"],
            merged_at=json_data["pull_request"]["merged_at"],
            title=json_data["title"],
            body=json_data["body"] or "",
        )

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        include_repos: tuple[str, ...] | None = None,
        exclude_repos: tuple[str, ...] | None = None,
    ) -> "list[PullRequest]":
        res = requests.get(url, headers=headers)
        data = json.loads(res.text)

        def should_include_repo(repo_url: str) -> bool:
            repo_name = "/".join(repo_url.split("/")[-2:])
            if include_repos:
                return repo_name in include_repos
            if exclude_repos:
                return repo_name not in exclude_repos
            return True

        return sorted(
            [
                cls.from_json(item)
                for item in data["items"]
                if item["state"] == "closed" and should_include_repo(item["repository_url"])
            ],
            key=lambda x: x.merged_at,
        )
