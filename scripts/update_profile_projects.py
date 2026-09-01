#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "Zhenxiangai"
LIMIT = 6
README = Path(__file__).resolve().parents[1] / "README.md"
PROJECT_CARD_DIR = README.parent / "assets" / "projects"
RADAR_CARD_DIR = README.parent / "assets" / "cards"

CURRENT_START = "<!--START_SECTION:current_projects-->"
CURRENT_END = "<!--END_SECTION:current_projects-->"
RADAR_START = "<!--START_SECTION:radar_projects-->"
RADAR_END = "<!--END_SECTION:radar_projects-->"
STATS_START = "<!--START_SECTION:profile_stats-->"
STATS_END = "<!--END_SECTION:profile_stats-->"

# GitHub marks KanWanLe as a fork because it preserves its MIT-licensed upstream
# history. It is independently maintained and intentionally featured here.
FEATURED_FORKS = {"kanwanle"}

PROJECT_OVERRIDES = {
    "kanwanle": {
        "title": "看完了 · KanWanLe",
        "subtitle": "Zhenxiangai/kanwanle · 基于上游持续开发",
        "description": (
            "面向 YouTube 与 B 站的本地优先 AI 视频学习扩展，提供时间戳字幕、"
            "双语阅读、章节金句、选文解释与笔记。"
        ),
    },
    "link-video-downloader-zhenxiangai": {
        "description": (
            "把视频号、B 站、小红书或抖音链接交给 Hermes，在 Mac 本地完成下载、"
            "整理与逐字稿，并支持博主批量抓取。"
        ),
    },
    "zhenxiang-hermes-knowme": {
        "description": (
            "Hermes Agent 的自适应 onboarding 技能：通过访谈建立协作档案，"
            "并在授权后写入记忆、推荐官方集成。"
        ),
        "language": "Markdown",
    },
}

RADAR_PROJECTS = [
    {
        "repository": "NousResearch/hermes-agent",
        "slug": "hermes-agent",
        "title": "Hermes Agent",
        "description": "能够持续成长并积累记忆的个人 AI Agent。",
    },
    {
        "repository": "qxcnm/Codex-Manager",
        "slug": "codex-manager",
        "title": "Codex Manager",
        "description": "Codex CLI 账号管理、切换与本地网关转发工具。",
    },
    {
        "repository": "larksuite/cli",
        "slug": "lark-cli",
        "title": "Lark / Feishu CLI",
        "description": "面向人类与 AI Agent 的官方飞书 CLI，覆盖 200+ 命令与核心业务域。",
    },
    {
        "repository": "Tencent/WeKnora",
        "slug": "weknora",
        "title": "WeKnora",
        "description": "把原始文档转成可查询的 RAG、推理 Agent 与自维护 Wiki。",
    },
    {
        "repository": "vectorize-io/hindsight",
        "slug": "hindsight",
        "title": "Hindsight",
        "description": "会学习并持续改进的 Agent 长期记忆系统。",
    },
    {
        "repository": "microsoft/markitdown",
        "slug": "markitdown",
        "title": "MarkItDown",
        "description": "把 Office、PDF 等文件转换为 Markdown，便于知识摄取与 Agent 工作流。",
    },
]

LANGUAGE_COLORS = {
    "C": "#555555",
    "C++": "#f34b7d",
    "CSS": "#663399",
    "Go": "#00add8",
    "HTML": "#e34c26",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Markdown": "#519aba",
    "Python": "#3572a5",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "TypeScript": "#3178c6",
}


def github_json(path: str):
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "zhenxiangai-profile",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def repositories():
    repos = github_json(
        f"/users/{OWNER}/repos?per_page=100&type=owner&sort=pushed&direction=desc"
    )
    return select_repositories(repos)


def select_repositories(repos):
    selected = [
        repo
        for repo in repos
        if not repo["private"]
        and not repo["archived"]
        and repo["name"].lower() != OWNER.lower()
        and (not repo["fork"] or repo["name"] in FEATURED_FORKS)
    ]
    selected.sort(key=lambda repo: repo.get("pushed_at") or "", reverse=True)
    return selected[:LIMIT]


def radar_repositories():
    projects = []
    for config in RADAR_PROJECTS:
        repo = github_json(f"/repos/{quote(config['repository'], safe='/')}")
        projects.append((config, repo))
    return projects


def display_units(value: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
        for character in value
    )


def truncate(value: str, max_units: int) -> str:
    if display_units(value) <= max_units:
        return value
    kept = []
    width = 0
    for character in value:
        character_width = display_units(character)
        if width + character_width > max_units - 1:
            break
        kept.append(character)
        width += character_width
    return "".join(kept).rstrip() + "…"


def wrap_description(value: str, max_units: int = 70, max_lines: int = 2):
    tokens = re.findall(r"\S+\s*", " ".join(value.split()))
    lines = []
    current = ""

    for token in tokens:
        candidate = (current + token).rstrip()
        if current and display_units(candidate) > max_units:
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            current += token

        while display_units(current.rstrip()) > max_units:
            piece = truncate(current.rstrip(), max_units)
            if piece.endswith("…"):
                piece = piece[:-1]
            lines.append(piece)
            current = current[len(piece) :].lstrip()

        if len(lines) >= max_lines:
            break

    if len(lines) < max_lines and current.strip():
        lines.append(current.strip())

    if len(lines) > max_lines:
        lines = lines[:max_lines]
    rendered = "".join(lines).replace(" ", "")
    original = "".join(value.split())
    if rendered != original and lines:
        lines[-1] = truncate(lines[-1], max_units - 1).rstrip("…") + "…"
    return lines[:max_lines]


def format_count(value: int) -> str:
    if value < 1_000:
        return str(value)
    if value < 1_000_000:
        number = f"{value / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{number}k"
    number = f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".")
    return f"{number}m"


def language_for(repo, override=None) -> str:
    if override and override.get("language"):
        return override["language"]
    return repo.get("language") or "Other"


def language_color(language: str) -> str:
    return LANGUAGE_COLORS.get(language, "#8b949e")


def card_svg(
    *,
    title: str,
    subtitle: str,
    description: str,
    language: str,
    stars: int,
    forks: int,
    updated: str | None = None,
) -> str:
    title = truncate(title, 46)
    subtitle = truncate(subtitle, 70)
    description_lines = wrap_description(description)
    while len(description_lines) < 2:
        description_lines.append("")

    title_xml = html.escape(title)
    subtitle_xml = html.escape(subtitle)
    description_xml = html.escape(description)
    language_xml = html.escape(language)
    first_line = html.escape(description_lines[0])
    second_line = html.escape(description_lines[1])
    color = language_color(language)
    stars_text = html.escape(f"★ {format_count(stars)}")
    forks_text = html.escape(f"⑂ {format_count(forks)}")
    updated_text = html.escape(f"更新 {updated}") if updated else ""

    if updated:
        center_meta = (
            f'    <text x="188" y="166" fill="#8b949e" font-size="12">'
            f"{updated_text}</text>\n"
        )
        stars_x, forks_x = 382, 456
    else:
        center_meta = ""
        stars_x, forks_x = 360, 448

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="184" '
        'viewBox="0 0 520 184" role="img" aria-labelledby="title desc">\n'
        f'  <title id="title">{title_xml}</title>\n'
        f'  <desc id="desc">{description_xml}</desc>\n'
        '  <rect x="1" y="1" width="518" height="182" rx="12" '
        'fill="#111416" stroke="#30363d" />\n'
        "  <g font-family=\"-apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "'PingFang SC', 'Microsoft YaHei', sans-serif\">\n"
        f'    <text x="24" y="39" fill="#9bff18" font-size="20" '
        f'font-weight="700">{title_xml}</text>\n'
        f'    <text x="24" y="63" fill="#8b949e" font-size="12">'
        f"{subtitle_xml}</text>\n"
        f'    <text x="24" y="96" fill="#c6cac4" font-size="13">'
        f"{first_line}</text>\n"
        f'    <text x="24" y="116" fill="#c6cac4" font-size="13">'
        f"{second_line}</text>\n"
        f'    <circle cx="30" cy="161" r="5" fill="{color}" />\n'
        f'    <text x="42" y="166" fill="#c6cac4" font-size="12">'
        f"{language_xml}</text>\n"
        f"{center_meta}"
        f'    <text x="{stars_x}" y="166" fill="#f8d866" font-size="12">'
        f"{stars_text}</text>\n"
        f'    <text x="{forks_x}" y="166" fill="#c6cac4" font-size="12">'
        f"{forks_text}</text>\n"
        "  </g>\n"
        "</svg>\n"
    )


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:10]


def write_text(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != value:
        path.write_text(value)


def project_card(repo):
    override = PROJECT_OVERRIDES.get(repo["name"], {})
    title = override.get("title", repo["name"])
    subtitle = override.get("subtitle", repo["owner"]["login"])
    description = override.get("description", repo.get("description"))
    if not description:
        description = "项目说明正在整理中；点击卡片可查看仓库 README。"
    language = language_for(repo, override)
    svg = card_svg(
        title=title,
        subtitle=subtitle,
        description=description,
        language=language,
        stars=repo["stargazers_count"],
        forks=repo["forks_count"],
        updated=repo["pushed_at"][:10],
    )
    slug = re.sub(r"[^a-z0-9-]+", "-", repo["name"].lower()).strip("-")
    path = PROJECT_CARD_DIR / f"{slug}.svg"
    return repo, title, path, svg


def radar_card(config, repo):
    language = language_for(repo)
    svg = card_svg(
        title=config["title"],
        subtitle=repo["owner"]["login"],
        description=config["description"],
        language=language,
        stars=repo["stargazers_count"],
        forks=repo["forks_count"],
    )
    path = RADAR_CARD_DIR / f"{config['slug']}.svg"
    return config, repo, path, svg


def render_cards(cards, relative_dir: str, start: str, end: str) -> str:
    lines = [start, '  <p align="left">']
    for item, title, path, svg in cards:
        if "html_url" in item:
            url = item["html_url"]
            override = PROJECT_OVERRIDES.get(item["name"], {})
            description = override.get("description", item.get("description"))
        else:
            url = f"https://github.com/{item['repository']}"
            description = item["description"]
        description = description or "点击卡片查看项目说明"
        alt = f"{title}：{description}"
        src = f"./{relative_dir}/{path.name}?v={digest(svg)}"
        lines.extend(
            [
                f'    <a href="{html.escape(url, quote=True)}">',
                f'      <img width="372" alt="{html.escape(alt, quote=True)}" '
                f'src="{html.escape(src, quote=True)}" />',
                "    </a>",
            ]
        )
    lines.extend(["  </p>", end])
    return "\n".join(lines)


def render_current(cards) -> str:
    return render_cards(cards, "assets/projects", CURRENT_START, CURRENT_END)


def render_radar(cards, synced_on: str) -> str:
    normalized = [
        (config, config["title"], path, svg)
        for config, _repo, path, svg in cards
    ]
    rendered = render_cards(normalized, "assets/cards", RADAR_START, RADAR_END)
    sync_note = (
        f"  <sub>Star、Fork 与主要语言每 12 小时自动同步；最近同步 "
        f"{synced_on}（UTC+8）。</sub>"
    )
    return rendered.replace(
        f"\n{RADAR_END}",
        f"\n\n{sync_note}\n{RADAR_END}",
    )


def render_stats(project_count: int) -> str:
    return f'''{STATS_START}
  <div align="center">
    <img alt="Profile projects: {project_count}" src="https://img.shields.io/badge/PROFILE_PROJECTS-{project_count}-9BFF18?style=for-the-badge&amp;logo=github&amp;logoColor=080A0B&amp;labelColor=111416" />
    <img alt="Open Source Radar: {len(RADAR_PROJECTS)}" src="https://img.shields.io/badge/RADAR_PROJECTS-{len(RADAR_PROJECTS)}-9BFF18?style=for-the-badge&amp;logo=github&amp;logoColor=080A0B&amp;labelColor=111416" />
    <img alt="Profile sync enabled" src="https://img.shields.io/badge/AUTO_SYNC-EVERY_12_HOURS-9BFF18?style=for-the-badge&amp;logo=githubactions&amp;logoColor=080A0B&amp;labelColor=111416" />
  </div>
{STATS_END}'''


def replace_section(current: str, start: str, end: str, replacement: str) -> str:
    before, separator, tail = current.partition(start)
    if not separator or end not in tail:
        raise SystemExit(f"README markers are missing: {start} / {end}")
    _, _, after = tail.partition(end)
    return before + replacement + after


def main():
    repos = repositories()
    radar_repos = radar_repositories()
    project_cards = [project_card(repo) for repo in repos]
    radar_cards = [radar_card(config, repo) for config, repo in radar_repos]
    synced_on = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    current = README.read_text()
    current = replace_section(
        current,
        CURRENT_START,
        CURRENT_END,
        render_current(project_cards),
    )
    current = replace_section(
        current,
        RADAR_START,
        RADAR_END,
        render_radar(radar_cards, synced_on),
    )
    current = replace_section(
        current,
        STATS_START,
        STATS_END,
        render_stats(len(project_cards)),
    )

    for _repo, _title, path, svg in project_cards:
        write_text(path, svg)
    for _config, _repo, path, svg in radar_cards:
        write_text(path, svg)
    write_text(README, current)


if __name__ == "__main__":
    main()
