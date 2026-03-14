import json
import re
from pathlib import Path

import requests

URLS = [
    "https://www.gushici.net/shici/52/41814.html",
    "https://www.gushici.net/shici/51/10719.html",
    "https://www.gushici.net/shici/38/61456.html",
    "https://www.gushici.net/shici/15/6883.html",
    "https://www.gushici.net/shici/41/41459.html",
    "https://www.gushici.net/shici/18/45942.html",
    "https://www.gushici.net/shici/05/59114.html",
    "https://www.gushici.net/shici/59/16208.html",
    "https://www.gushici.net/shici/39/5067.html",
    "https://www.gushici.net/shici/13/62215.html",
]

OUT = Path(__file__).resolve().parents[1] / "data" / "poetry_library" / "classic_poems.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

STYLE_POETS = {
    "婉约派": {"李清照", "柳永", "晏殊", "晏几道", "欧阳修", "秦观", "周邦彦", "纳兰性德"},
    "豪放派": {"苏轼", "辛弃疾", "岳飞", "陆游", "张孝祥", "陈亮"},
}

KEYWORD_TAGS = {
    "思乡": ["思乡", "故乡", "乡", "归", "客", "家", "故园", "关山", "长安"],
    "离别": ["别", "离", "送", "相逢", "归期", "远行", "长亭"],
    "山水": ["山", "水", "江", "湖", "河", "泉", "云", "雨", "风", "月"],
    "边塞": ["边", "塞", "胡", "关", "戎", "战", "军", "烽火", "玉门"],
    "爱情": ["情", "爱", "相思", "红豆", "佳人", "伊人", "君", "妾"],
    "山河": ["山河", "江山", "天地", "万里", "河山", "乾坤"],
}


def normalize(text: str) -> str:
    text = (text or "").replace("\r", "").replace("\n", " ").replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def infer_tags(content: str):
    found = []
    for tag, words in KEYWORD_TAGS.items():
        if any(w in content for w in words):
            found.append(tag)
    if not found:
        found = ["山水"]
    return found[:3]


def infer_style(author: str, content: str):
    if author in STYLE_POETS["豪放派"]:
        return "豪放派"
    if author in STYLE_POETS["婉约派"]:
        return "婉约派"
    if any(w in content for w in ["山河", "边", "塞", "战", "万里"]):
        return "豪放派"
    return "婉约派"


def parse_page(url: str):
    r = requests.get(url, timeout=(6, 10), headers=HEADERS)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    html = r.text

    title_tag = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if not title_tag:
        return None
    title_raw = normalize(title_tag.group(1))

    parts = title_raw.split("_")
    title = parts[0].replace("原文、翻译及赏析", "").replace("原文及翻译", "").replace("原文", "").strip()
    author = parts[1].strip() if len(parts) > 1 else "未知作者"

    desc = re.search(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', html, re.I | re.S)
    if not desc:
        return None
    content = normalize(desc.group(1).replace("<br/>", "\n"))

    if not title or not author or len(content) < 12:
        return None

    if "..." in content or "…" in content:
        return None

    return {
        "title": title,
        "author": author,
        "content": content,
        "style": infer_style(author, content),
        "tags": infer_tags(content),
    }


def main():
    new_items = []
    for url in URLS:
        try:
            item = parse_page(url)
            if item:
                new_items.append(item)
                print(f"[OK] {item['title']} - {item['author']}")
            else:
                print(f"[SKIP] {url}")
        except Exception as exc:
            print(f"[WARN] {url} -> {exc}")

    old_items = []
    if OUT.exists():
        try:
            raw = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                old_items = [x for x in raw if isinstance(x, dict)]
        except Exception:
            old_items = []

    merged = []
    seen = set()
    for row in new_items + old_items:
        title = str(row.get("title", "")).strip()
        author = str(row.get("author", "")).strip()
        key = (title, author)
        if not title or not author or key in seen:
            continue
        seen.add(key)
        merged.append(row)

    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] 新增/更新: {len(new_items)}")
    print(f"[DONE] 合并总数: {len(merged)}")


if __name__ == "__main__":
    main()
