"""Collect every bullet inside an `!!! question` callout and publish it as
assets/revise.json, which the home page uses for its "Revise one" panel.
Also replaces {{ <section>_chapters }} on the home page with the number of
chapters in docs/<section>/ (index.md excluded), e.g. {{ linux_chapters }},
{{ bash_chapters }}. Runs on every build, so new chapters and new sections
are picked up automatically."""
import json
import os
import re

_points = []
_COUNT = re.compile(r"\{\{ (\w+)_chapters \}\}")


def on_pre_build(config):
    _points.clear()


def _chapter_count(section, files):
    prefix = section.replace("_", "-") + "/"
    return sum(
        1
        for f in files
        if f.src_uri.startswith(prefix)
        and f.src_uri.endswith(".md")
        and f.src_uri != prefix + "index.md"
    )


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri == "index.md":
        markdown = _COUNT.sub(lambda m: str(_chapter_count(m.group(1), files)), markdown)
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
