import json
import random
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.gushici.net"
INDEX_URLS = [f"{BASE_URL}/"] + [f"{BASE_URL}/index_{i}.html" for i in range(2, 10)]
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "poetry_library" / "classic_poems.json"
TARGET_COUNT = 160

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

STYLE_POETS = {
    "婉约派": {"李清照", "柳永", "晏殊", "晏几道", "欧阳修", "秦观", "周邦彦", "纳兰性德"},
    "豪放派": {"苏轼", "辛弃疾", "岳飞", "陆游", "张孝祥", "陈亮"},
}

TAG_WHITELIST = ["思乡", "离别", "山水", "边塞", "爱情", "山河"]

KEYWORD_TAGS = {
    "思乡": ["思乡", "故乡", "乡", "归", "客", "家", "故园", "关山", "长安"],
    "离别": ["别", "离", "送", "相逢", "归期", "远行", "长亭"],
    "山水": ["山", "水", "江", "湖", "河", "泉", "云", "雨", "风", "月"],
    "边塞": ["边", "塞", "胡", "关", "戎", "战", "军", "烽火", "玉门"],
    "爱情": ["情", "爱", "相思", "红豆", "佳人", "伊人", "君", "妾"],
    "山河": ["山河", "江山", "天地", "万里", "河山", "乾坤"],
}


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=(6, 10), headers=HEADERS)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def normalize_text(text: str) -> str:
    text = (text or "").replace("\r", "").replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_tags(content: str, raw_tags: list[str]) -> list[str]:
    tags = [tag for tag in raw_tags if tag in TAG_WHITELIST]
    if tags:
        return list(dict.fromkeys(tags))[:3]

    guessed = []
    for tag, keywords in KEYWORD_TAGS.items():
        if any(keyword in content for keyword in keywords):
            guessed.append(tag)

    if not guessed:
        guessed = ["山水"]

    return guessed[:3]


def parse_style(author: str, raw_tags: list[str], content: str) -> str:
    if any("豪放" in tag for tag in raw_tags):
        return "豪放派"
    if any("婉约" in tag for tag in raw_tags):
        return "婉约派"

    if author in STYLE_POETS["豪放派"]:
        return "豪放派"
    if author in STYLE_POETS["婉约派"]:
        return "婉约派"

    if any(word in content for word in ["山河", "长风", "万里", "烽火", "边塞"]):
        return "豪放派"
    return "婉约派"


def extract_poem_links(index_html: str) -> list[str]:
    links = re.findall(r'href="(/shici/[0-9a-zA-Z]{2}/\d+\.html)"', index_html)
    result = []
    seen = set()
    for link in links:
        full = f"{BASE_URL}{link}"
        if full in seen:
            continue
        seen.add(full)
        result.append(full)
    return result


def parse_poem_page(html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")

    headers = soup.find_all("h1")
    title = ""
    for item in headers:
        text = normalize_text(item.get_text(" ", strip=True))
        if text and text != "古诗词网" and "古诗词网" not in text:
            title = text
            break

    source = soup.find("p", class_="source")
    author = ""
    if source:
        links = source.find_all("a")
        if links:
            author = normalize_text(links[-1].get_text(" ", strip=True))

    content_block = None
    if source:
        content_block = source.find_next("div", class_="cont")
    if content_block is None:
        content_block = soup.find("div", class_="cont")

    content = normalize_text(content_block.get_text("\n", strip=True) if content_block else "")

    if not title or not author or not content:
        return None

    raw_tags = []
    tag_node = content_block.find_next("p", class_="tag") if content_block else None
    if tag_node:
        raw_tags = [normalize_text(x.get_text(" ", strip=True)) for x in tag_node.find_all("a")]
        raw_tags = [x for x in raw_tags if x]

    tags = parse_tags(content, raw_tags)
    style = parse_style(author, raw_tags, content)

    return {
        "title": title,
        "author": author,
        "content": content,
        "style": style,
        "tags": tags,
    }


def main() -> None:
    poem_links = []
    for index_url in INDEX_URLS:
        try:
            html = fetch_html(index_url)
            poem_links.extend(extract_poem_links(html))
            time.sleep(0.1)
        except Exception as exc:
            print(f"[WARN] 索引抓取失败: {index_url} -> {exc}")

    # 去重保序
    dedup_links = []
    seen_links = set()
    for url in poem_links:
        if url in seen_links:
            continue
        seen_links.add(url)
        dedup_links.append(url)

    print(f"[INFO] 候选诗词链接: {len(dedup_links)}", flush=True)

    random.shuffle(dedup_links)
    records = []
    seen_key = set()

    for idx, url in enumerate(dedup_links, start=1):
        try:
            html = fetch_html(url)
            poem = parse_poem_page(html)
            time.sleep(0.08)
        except Exception:
            continue

        if not poem:
            continue

        key = (poem["title"], poem["author"])
        if key in seen_key:
            continue
        seen_key.add(key)
        records.append(poem)

        if len(records) % 20 == 0:
            print(f"[INFO] 已抓取 {len(records)} 条（扫描 {idx}/{len(dedup_links)}）", flush=True)

        if len(records) >= TARGET_COUNT:
            break

    existing_records = []
    if OUTPUT_FILE.exists():
        try:
            raw = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                existing_records = [x for x in raw if isinstance(x, dict)]
        except Exception:
            existing_records = []

    if len(records) < 20:
        print(f"[WARN] 本次抓取有效条目较少: {len(records)}，将与现有库合并保留", flush=True)

    merged = []
    merged_seen = set()
    for item in records + existing_records:
        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip()
        key = (title, author)
        if not title or not author or key in merged_seen:
            continue
        merged_seen.add(key)
        merged.append(item)
        if len(merged) >= TARGET_COUNT:
            break

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 已更新: {OUTPUT_FILE}")
    print(f"[OK] 本次抓取条目: {len(records)}")
    print(f"[OK] 合并后条目: {len(merged)}")


if __name__ == "__main__":
    main()
