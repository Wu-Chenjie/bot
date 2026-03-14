import json
import re
import subprocess
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.shiku.org"
XS_INDEX = f"{BASE}/shiku/xs/index.htm"
OUT = Path(__file__).resolve().parents[1] / "data" / "poetry_library" / "modern_poems.json"
TARGET_COUNT = 120

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

NOISE_TOKENS = {
    "中国诗歌库", "中华诗库", "中国诗典", "中国诗人", "中国诗坛", "首页",
    "上一首", "下一首", "返回", "目录", "诗人简介", "电子书库"
}


def fetch(url: str) -> str:
    resp = requests.get(url, timeout=(6, 12), headers=HEADERS)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def clean_line(line: str) -> str:
    line = (line or "").replace("\u3000", " ").replace("\xa0", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def extract_poet_dirs(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "lxml")
    dirs = []
    seen = set()
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if href.startswith("/"):
            full = f"{BASE}{href}"
        elif href.startswith("http"):
            full = href
        else:
            full = f"{BASE}/shiku/xs/{href}"

        m = re.search(r"/shiku/xs/([a-z0-9_-]+)/index\.htm$", full, flags=re.I)
        if not m:
            continue
        folder = m.group(1).lower()
        if folder in {"xz"}:
            continue
        if folder.startswith("index"):
            continue
        if full in seen:
            continue
        seen.add(full)
        dirs.append(full)
    return dirs


def extract_poem_links(poet_index_url: str, html: str) -> list[str]:
    # 相对链接如 100.htm / 001.htm
    rels = re.findall(r'href="((?:\d{2,3})\.htm)"', html, flags=re.I)
    root = poet_index_url.rsplit("/", 1)[0]
    links = []
    seen = set()
    for rel in rels:
        if rel.lower() == "000.htm":
            continue
        full = f"{root}/{rel}"
        if full in seen:
            continue
        seen.add(full)
        links.append(full)
    return links


def parse_poem_page(html: str) -> tuple[str, str, str] | None:
    soup = BeautifulSoup(html, "lxml")
    page_title = clean_line(soup.title.get_text(" ", strip=True) if soup.title else "")

    # title 形如：中华诗库::北岛诗集
    m = re.search(r"中华诗库::(.+?)诗集", page_title)
    author = clean_line(m.group(1)) if m else ""

    lines = [clean_line(x) for x in soup.get_text("\n").splitlines()]
    lines = [x for x in lines if x]
    if not lines:
        return None

    filtered = []
    for line in lines:
        if any(token == line for token in NOISE_TOKENS):
            continue
        if "中华诗库::" in line:
            continue
        if "诗集::" in line:
            continue
        if line in {"（", "）", "(", ")"}:
            continue
        filtered.append(line)

    if len(filtered) < 4:
        return None

    # 第一行通常是诗题
    title = filtered[0]
    if not title or len(title) > 40:
        return None

    # 回退作者识别：正文头部常见“徐志摩诗集”等
    for line in filtered[1:6]:
        if line.endswith("诗集") and len(line) <= 18:
            guessed = line.replace("诗集", "").strip("《》 ")
            if guessed:
                author = guessed
            break

    content_lines = []
    for line in filtered[1:]:
        if line in NOISE_TOKENS:
            continue
        if line.endswith("诗集") and len(line) <= 18:
            continue
        if re.search(r"^(中国诗歌库|中华诗库|中国诗典|中国诗人|中国诗坛|首页)$", line):
            continue
        if re.search(r"^\d+\s*[:：].*", line):
            continue
        content_lines.append(line)

    content_lines = [x for x in content_lines if x and len(x) <= 80]
    if len(content_lines) < 3:
        return None

    content = "\n".join(content_lines[:24]).strip()
    if len(content) < 20:
        return None

    if not author:
        author = "未知作者"

    return title, author, content


def poem_key_from_text(item: str) -> tuple[str, str] | None:
    parts = item.split("\n")
    if len(parts) < 3:
        return None
    title = clean_line(parts[0]).strip("《》")
    author = clean_line(parts[1])
    if not title or not author:
        return None
    return title, author


def build_text(title: str, author: str, content: str) -> str:
    return f"《{title}》\n{author}\n{content}"


def main() -> None:
    index_html = fetch(XS_INDEX)
    poet_indexes = extract_poet_dirs(index_html)

    # 取前60位诗人目录，提升覆盖率
    poet_indexes = poet_indexes[:60]

    new_items: list[str] = []
    seen_keys: set[tuple[str, str]] = set()

    for poet_idx, poet_url in enumerate(poet_indexes, start=1):
        try:
            poet_html = fetch(poet_url)
        except Exception as e:
            print(f"[WARN] 诗人目录失败: {poet_url} -> {e}")
            continue

        poem_links = extract_poem_links(poet_url, poet_html)
        # 每位诗人最多抓12首
        for poem_url in poem_links[:12]:
            try:
                html = fetch(poem_url)
                parsed = parse_poem_page(html)
            except Exception:
                continue

            if not parsed:
                continue
            title, author, content = parsed
            key = (title, author)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            new_items.append(build_text(title, author, content))

            if len(new_items) % 20 == 0:
                print(f"[INFO] 已抓取现代诗 {len(new_items)} 条", flush=True)

        if len(new_items) >= TARGET_COUNT:
            break

    old_items: list[str] = []
    if OUT.exists():
        try:
            raw = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                old_items = [x for x in raw if isinstance(x, str)]
        except Exception:
            old_items = []

    # 回退到git中的基线，避免本地文件因抓取失败被缩减
    git_base_items: list[str] = []
    try:
        text = subprocess.check_output(
            ["git", "show", "HEAD:data/poetry_library/modern_poems.json"],
            text=True,
            encoding="utf-8",
        )
        parsed = json.loads(text)
        if isinstance(parsed, list):
            git_base_items = [x for x in parsed if isinstance(x, str)]
    except Exception:
        git_base_items = []

    base_items = old_items if len(old_items) >= len(git_base_items) else git_base_items

    merged: list[str] = []
    merged_seen: set[tuple[str, str]] = set()

    for item in new_items + base_items:
        key = poem_key_from_text(item)
        if not key:
            continue
        if key in merged_seen:
            continue
        merged_seen.add(key)
        merged.append(item)
        if len(merged) >= TARGET_COUNT:
            break

    if len(merged) < TARGET_COUNT:
        for item in base_items:
            if len(merged) >= TARGET_COUNT:
                break
            key = poem_key_from_text(item)
            if not key or key in merged_seen:
                continue
            merged_seen.add(key)
            merged.append(item)

    if len(new_items) < 20:
        print(f"[WARN] 本次抓取到的现代诗较少: {len(new_items)}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[DONE] 来源站点: {BASE}")
    print(f"[DONE] 本次新增候选: {len(new_items)}")
    print(f"[DONE] 合并后总数: {len(merged)}")


if __name__ == "__main__":
    main()
