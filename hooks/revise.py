"""Collect every bullet inside an `!!! question` callout and publish it as
assets/revise.json, which the home page uses for its "Revise one" panel.
Runs on every build, so new chapters are picked up automatically."""
import json
import os
import re

_points = []


def on_pre_build(config):
    _points.clear()


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri == "index.md":
        count = sum(1 for f in files if f.src_uri.startswith("linux/") and f.src_uri.endswith(".md") and f.src_uri != "linux/index.md")
        markdown = markdown.replace("{{ linux_chapters }}", str(count))
    in_block = False
    for line in markdown.splitlines():
        if line.startswith("!!! question"):
            in_block = True
            continue
        if in_block:
            if line.strip() and not line.startswith("    "):
                in_block = False
                continue
            if re.match(r"^ {6,}\S", line) and _points and _points[-1]["url"] == page.url:
                _points[-1]["text"] += " " + line.strip()
                continue
            m = re.match(r"^    [*-] (.+)$", line)
            if m:
                _points.append({"text": m.group(1).strip(), "title": page.title, "url": page.url})
    return markdown


def on_post_build(config):
    out = os.path.join(config["site_dir"], "assets", "revise.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(_points, f, ensure_ascii=False)
