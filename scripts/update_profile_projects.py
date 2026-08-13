#!/usr/bin/env python3
import html
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

OWNER = "Zhenxiangai"
LIMIT = 6
START = "<!--START_SECTION:current_projects-->"
END = "<!--END_SECTION:current_projects-->"
README = Path(__file__).resolve().parents[1] / "README.md"


def repositories():
    request = Request(
        f"https://api.github.com/users/{OWNER}/repos?per_page=100&type=owner&sort=pushed",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "zhenxiangai-profile"},
    )
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=30) as response:
        repos = json.load(response)
    return [
        repo
        for repo in repos
        if not repo["private"]
        and not repo["fork"]
        and not repo["archived"]
        and repo["name"].lower() != OWNER.lower()
    ][:LIMIT]


def cell(repo):
    name = html.escape(repo["name"])
    url = html.escape(repo["html_url"], quote=True)
    description = html.escape(repo["description"] or "暂无项目简介")
    details = [repo["language"], f"最近更新 {repo['pushed_at'][:10]}"]
    meta = " · ".join(html.escape(value) for value in details if value)
    return (
        '    <td width="50%" valign="top">\n'
        f'      <a href="{url}"><strong>{name}</strong></a><br />\n'
        f"      {description}<br />\n"
        f"      <sub>{meta}</sub>\n"
        "    </td>"
    )


def render(repos):
    rows = []
    for index in range(0, len(repos), 2):
        cells = [cell(repo) for repo in repos[index : index + 2]]
        rows.append("  <tr>\n" + "\n".join(cells) + "\n  </tr>")
    return START + "\n<table>\n" + "\n".join(rows) + "\n</table>\n" + END


def main():
    current = README.read_text()
    before, separator, tail = current.partition(START)
    if not separator or END not in tail:
        raise SystemExit("current_projects markers are missing")
    _, _, after = tail.partition(END)
    README.write_text(before + render(repositories()) + after)


if __name__ == "__main__":
    main()
