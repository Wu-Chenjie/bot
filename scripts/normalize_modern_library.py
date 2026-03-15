import json
import re
import subprocess
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "data" / "poetry_library" / "modern_poems.json"
TARGET = 120

NOISE = {
    "中国诗歌库", "中华诗库", "中国诗典", "中国诗人", "中国诗坛", "首页",
    "上一首", "下一首", "返回", "目录"
}
NOISE_LINE_RE = re.compile(r"^(中国诗歌库|中华诗库|中国诗典|中国诗人|中国诗坛|首页)$")


def clean_line(text: str) -> str:
    text = (text or "").replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_item(item: str):
    lines = [clean_line(x) for x in re.split(r"[\r\n]+", item or "")]
    lines = [x for x in lines if x and x not in NOISE]
    if len(lines) < 3:
        return None

    title = lines[0].strip()
    if not title.startswith("《"):
        title = f"《{title.strip('《》')}》"
    author = lines[1]
    content = lines[2:]

    if content and content[0].endswith("诗集") and len(content[0]) <= 20:
        if author == "未知作者":
            author = content[0].replace("诗集", "").strip("《》 ") or "未知作者"
        content = content[1:]

    if author.endswith("诗集") and len(author) <= 20:
        author = author.replace("诗集", "").strip("《》 ") or "未知作者"

    content = [x for x in content if x not in NOISE and not NOISE_LINE_RE.search(x)]
    if len(content) < 2:
        return None

    key = (title.strip("《》"), author)
    text = "\n".join([title, author] + content)
    return key, text


def load_git_head_items() -> list[str]:
    try:
        raw = subprocess.check_output(
            ["git", "show", "HEAD:data/poetry_library/modern_poems.json"],
            text=True,
            encoding="utf-8",
        )
        data = json.loads(raw)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, str)]
    except Exception:
        pass
    return []


def load_local_items() -> list[str]:
    if not FILE.exists():
        return []
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, str)]


def main():
    current = load_local_items()
    base = load_git_head_items()

    merged = []
    seen = set()
    unknown_count = 0

    for source in (current, base):
        for item in source:
            parsed = parse_item(item)
            if not parsed:
                continue
            key, normalized = parsed
            if key in seen:
                continue
            seen.add(key)
            if "\n未知作者\n" in normalized:
                unknown_count += 1
            merged.append(normalized)
            if len(merged) >= TARGET:
                break
        if len(merged) >= TARGET:
            break

    FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] total={len(merged)}")
    print(f"[DONE] unknown_author={unknown_count}")


if __name__ == "__main__":
    main()
