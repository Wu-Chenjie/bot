from ncatbot.utils import get_log
from .config import (
    POETRY_API_LIST,
    API_TIMEOUT,
    RETRY_TIMES,
    CLASSIC_POETRY_API,
    MODERN_POETRY_API,
    FOREIGN_BILINGUAL_POETRY_API,
)
from .utils import format_poetry
import aiohttp
import random
import json
import re
from html import unescape
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote_plus

LOG = get_log("PoetryPlugin-API")

MODERN_POETRY_FALLBACK_APIS = [
    MODERN_POETRY_API,
    "https://international.v1.hitokoto.cn/?encode=json",
]

FOREIGN_POETRY_FALLBACK_APIS = [
    FOREIGN_BILINGUAL_POETRY_API,
]

SEARCH_ENGINE_URLS = [
    "https://duckduckgo.com/html/?q={query}",
    "https://www.bing.com/search?q={query}",
]

POETRY_LIBRARY_DIR = Path(__file__).resolve().parent / "data" / "poetry_library"
CLASSIC_LIBRARY_FILE = POETRY_LIBRARY_DIR / "classic_poems.json"
MODERN_LIBRARY_FILE = POETRY_LIBRARY_DIR / "modern_poems.json"
FOREIGN_LIBRARY_FILE = POETRY_LIBRARY_DIR / "foreign_poems.json"


def _load_library_file(path: Path, expected_item_type: type, fallback: List) -> List:
    try:
        if not path.exists():
            return fallback
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            LOG.warning(f"诗歌库文件格式错误（非列表）: {path}")
            return fallback
        cleaned = [item for item in raw if isinstance(item, expected_item_type)]
        if not cleaned:
            LOG.warning(f"诗歌库文件为空或类型不匹配: {path}")
            return fallback
        return cleaned
    except Exception as e:
        LOG.error(f"加载诗歌库失败 {path}: {e}")
        return fallback


def _split_clean_lines(text: str) -> List[str]:
    normalized = (text or "").replace("\r", "\n").replace("\u3000", " ").replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in normalized.split("\n")]
    return [line for line in lines if line]

class PoetryAPI:
    """诗歌API请求类"""

    LOCAL_MODERN_POEMS = [
        "《远和近》\n顾城\n你，一会看我，一会看云。\n我觉得，你看我时很远，你看云时很近。",
        "《断章》\n卞之琳\n你站在桥上看风景，\n看风景的人在楼上看你。\n明月装饰了你的窗子，\n你装饰了别人的梦。",
        "《一代人》\n顾城\n黑夜给了我黑色的眼睛，\n我却用它寻找光明。",
    ]

    LOCAL_FOREIGN_POEMS = [
        {
            "title": "Stopping by Woods on a Snowy Evening",
            "author": "Robert Frost",
            "translator": "未知",
            "english": "Whose woods these are I think I know.\nHis house is in the village though.",
            "chinese": "我想我认得这片树林。\n树林主人的房子在村中。",
        },
        {
            "title": "Hope is the thing with feathers",
            "author": "Emily Dickinson",
            "translator": "未知",
            "english": "Hope is the thing with feathers\nThat perches in the soul,",
            "chinese": "希望是有羽毛的东西，\n它栖息在灵魂之中。",
        },
    ]

    LOCAL_POEM_LIBRARY = [
        {
            "title": "如梦令·昨夜雨疏风骤",
            "author": "李清照",
            "content": "昨夜雨疏风骤，浓睡不消残酒。\n试问卷帘人，却道海棠依旧。\n知否，知否？应是绿肥红瘦。",
            "style": "婉约派",
            "tags": ["爱情", "离别", "山水"],
        },
        {
            "title": "声声慢·寻寻觅觅",
            "author": "李清照",
            "content": "寻寻觅觅，冷冷清清，凄凄惨惨戚戚。\n乍暖还寒时候，最难将息。",
            "style": "婉约派",
            "tags": ["爱情", "离别"],
        },
        {
            "title": "江城子·密州出猎",
            "author": "苏轼",
            "content": "老夫聊发少年狂，左牵黄，右擎苍。\n会挽雕弓如满月，西北望，射天狼。",
            "style": "豪放派",
            "tags": ["边塞", "山河"],
        },
        {
            "title": "破阵子·为陈同甫赋壮词以寄之",
            "author": "辛弃疾",
            "content": "醉里挑灯看剑，梦回吹角连营。\n马作的卢飞快，弓如霹雳弦惊。",
            "style": "豪放派",
            "tags": ["边塞", "山河"],
        },
        {
            "title": "静夜思",
            "author": "李白",
            "content": "床前明月光，疑是地上霜。\n举头望明月，低头思故乡。",
            "style": "豪放派",
            "tags": ["思乡"],
        },
        {
            "title": "春望",
            "author": "杜甫",
            "content": "国破山河在，城春草木深。\n感时花溅泪，恨别鸟惊心。",
            "style": "豪放派",
            "tags": ["山河", "离别"],
        },
        {
            "title": "送友人",
            "author": "李白",
            "content": "青山横北郭，白水绕东城。\n此地一为别，孤蓬万里征。",
            "style": "豪放派",
            "tags": ["离别", "山水"],
        },
        {
            "title": "蝶恋花·伫倚危楼风细细",
            "author": "柳永",
            "content": "伫倚危楼风细细，望极春愁，黯黯生天际。\n衣带渐宽终不悔，为伊消得人憔悴。",
            "style": "婉约派",
            "tags": ["爱情", "思乡"],
        },
    ]

    STYLE_ALIAS = {
        "婉约": "婉约派",
        "婉约派": "婉约派",
        "豪放": "豪放派",
        "豪放派": "豪放派",
    }

    STYLE_POETS = {
        "婉约派": {"李清照", "柳永", "晏殊", "晏几道", "欧阳修", "秦观", "周邦彦", "纳兰性德"},
        "豪放派": {"苏轼", "辛弃疾", "岳飞", "陆游", "张孝祥", "陈亮"},
    }

    TOPIC_KEYWORDS = {
        "思乡": ["思乡", "故乡", "乡", "归", "客", "家", "故园", "关山", "长安"],
        "离别": ["别", "离", "送", "相逢", "归期", "远行", "长亭"],
        "山水": ["山", "水", "江", "湖", "河", "泉", "云", "雨", "风", "月"],
        "边塞": ["边", "塞", "胡", "关", "戎", "战", "军", "烽火", "玉门"],
        "爱情": ["情", "爱", "相思", "红豆", "佳人", "伊人", "君", "妾"],
    }

    MODERN_NOISE_LINES = {
        "中国诗歌库",
        "中华诗库",
        "中国诗典",
        "中国诗人",
        "中国诗坛",
        "首页",
        "上一首",
        "下一首",
        "返回",
        "目录",
    }

    @staticmethod
    def _load_external_libraries() -> None:
        loaded_classic = _load_library_file(
            CLASSIC_LIBRARY_FILE,
            dict,
            PoetryAPI.LOCAL_POEM_LIBRARY,
        )
        loaded_modern = _load_library_file(
            MODERN_LIBRARY_FILE,
            str,
            PoetryAPI.LOCAL_MODERN_POEMS,
        )
        loaded_foreign = _load_library_file(
            FOREIGN_LIBRARY_FILE,
            dict,
            PoetryAPI.LOCAL_FOREIGN_POEMS,
        )

        PoetryAPI.LOCAL_POEM_LIBRARY = PoetryAPI._normalize_classic_library(loaded_classic)
        PoetryAPI.LOCAL_MODERN_POEMS = PoetryAPI._normalize_modern_library(loaded_modern)
        PoetryAPI.LOCAL_FOREIGN_POEMS = PoetryAPI._normalize_foreign_library(loaded_foreign)

        LOG.info(
            "本地诗歌库已加载: classic=%d, modern=%d, foreign=%d",
            len(PoetryAPI.LOCAL_POEM_LIBRARY),
            len(PoetryAPI.LOCAL_MODERN_POEMS),
            len(PoetryAPI.LOCAL_FOREIGN_POEMS),
        )

    @staticmethod
    def _normalize_classic_library(items: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        seen = set()

        for item in items:
            title = str(item.get("title", "")).strip()
            author = str(item.get("author", "")).strip()
            content = "\n".join(_split_clean_lines(str(item.get("content", ""))))
            if not title or not author or not content:
                continue

            style_raw = str(item.get("style", "")).strip()
            style = PoetryAPI.STYLE_ALIAS.get(style_raw, style_raw)
            if style not in {"婉约派", "豪放派"}:
                style = "豪放派" if author in PoetryAPI.STYLE_POETS["豪放派"] else "婉约派"

            tags_raw = item.get("tags")
            tags = [str(x).strip() for x in tags_raw] if isinstance(tags_raw, list) else []
            tags = [t for t in tags if t in PoetryAPI.TOPIC_KEYWORDS]
            if not tags:
                target = f"{title}\n{content}"
                for k, words in PoetryAPI.TOPIC_KEYWORDS.items():
                    if any(w in target for w in words):
                        tags.append(k)
                if not tags:
                    tags = ["山水"]

            key = (title, author)
            if key in seen:
                continue
            seen.add(key)

            normalized.append(
                {
                    "title": title,
                    "author": author,
                    "content": content,
                    "style": style,
                    "tags": tags[:3],
                }
            )

        return normalized or PoetryAPI.LOCAL_POEM_LIBRARY

    @staticmethod
    def _normalize_modern_library(items: List[str]) -> List[str]:
        normalized: List[str] = []
        seen = set()

        for raw in items:
            lines = _split_clean_lines(raw)
            if len(lines) < 3:
                continue

            title = lines[0].strip()
            if "中华诗库" in title:
                continue
            if not title.startswith("《"):
                title = f"《{title.strip('《》')}》"

            author = lines[1].strip()
            content_lines = lines[2:]

            if content_lines and content_lines[0].endswith("诗集") and len(content_lines[0]) <= 20:
                if author in {"", "未知作者"}:
                    guessed = content_lines[0].replace("诗集", "").strip("《》 ")
                    author = guessed or "未知作者"
                content_lines = content_lines[1:]

            if author.endswith("诗集") and len(author) <= 20:
                author = author.replace("诗集", "").strip("《》 ") or "未知作者"

            filtered = []
            for line in content_lines:
                if line in PoetryAPI.MODERN_NOISE_LINES:
                    continue
                if line.endswith("诗集") and len(line) <= 20:
                    continue
                if re.search(r"^(中国诗歌库|中华诗库|中国诗典|中国诗人|中国诗坛|首页)$", line):
                    continue
                if re.search(r"^[①②③④⑤⑥⑦⑧⑨⑩\d]+[、.．]\s*", line):
                    continue
                filtered.append(line)

            if len(filtered) < 1:
                continue

            text_block = "\n".join([title, author] + filtered)
            if text_block in seen:
                continue
            seen.add(text_block)

            normalized.append(text_block)

        if not normalized:
            return PoetryAPI.LOCAL_MODERN_POEMS

        min_expected = max(20, len(items) // 2)
        if len(items) >= 20 and len(normalized) < min_expected:
            LOG.warning(
                "现代诗库标准化后数量异常下降（raw=%d, normalized=%d），回退原始数据",
                len(items),
                len(normalized),
            )
            return items

        return normalized

    @staticmethod
    def _normalize_foreign_library(items: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        seen = set()

        for item in items:
            title = str(item.get("title", "")).strip() or "未知标题"
            author = str(item.get("author", "")).strip() or "未知作者"
            translator = str(item.get("translator", "")).strip() or "未知"
            english = "\n".join(_split_clean_lines(str(item.get("english", ""))))
            chinese = "\n".join(_split_clean_lines(str(item.get("chinese", ""))))

            if not english and not chinese:
                continue

            key = (title, author)
            if key in seen:
                continue
            seen.add(key)

            normalized.append(
                {
                    "title": title,
                    "author": author,
                    "translator": translator,
                    "english": english or "（无）",
                    "chinese": chinese or "（无）",
                }
            )

        return normalized or PoetryAPI.LOCAL_FOREIGN_POEMS
    
    @staticmethod
    async def get_random_poetry() -> Optional[str]:
        """随机获取一首诗歌（自动重试）"""
        if not POETRY_API_LIST:
            LOG.warning("未配置可用诗歌API")
            return None

        candidate_urls = POETRY_API_LIST[:]
        random.shuffle(candidate_urls)
        max_attempts = max(RETRY_TIMES, len(candidate_urls))
        fallback_text = None

        for attempt in range(max_attempts):
            api_url = candidate_urls[attempt % len(candidate_urls)]
            try:
                poetry_text = await PoetryAPI._request_api(api_url)
                if poetry_text:
                    return poetry_text
                if poetry_text:
                    fallback_text = fallback_text or poetry_text
                    LOG.info(f"返回内容过短，重试其他API: {api_url}")
            except Exception as e:
                LOG.warning(f"API请求重试 {api_url}: {e}")
        if fallback_text:
            return fallback_text

        for poetry_type, keyword in [("classic", "古诗词"), ("modern", "现代诗"), ("foreign", "英文诗")]:
            search_engine_result = await PoetryAPI._search_via_search_engine(keyword, poetry_type)
            if search_engine_result:
                return search_engine_result

        local_candidates = [
            PoetryAPI._get_local_classic_poetry(),
            format_poetry(random.choice(PoetryAPI.LOCAL_MODERN_POEMS), "modern"),
            PoetryAPI._get_local_foreign_poetry(),
        ]
        available = [item for item in local_candidates if item]
        return random.choice(available) if available else None
    
    @staticmethod
    async def get_poetry_by_type(poetry_type: str) -> Optional[str]:
        """按类型获取诗歌"""
        if poetry_type == "classic":
            poetry_text = await PoetryAPI._request_api(CLASSIC_POETRY_API)
            if poetry_text:
                return poetry_text

            search_engine_result = await PoetryAPI._search_via_search_engine("古诗词", "classic")
            if search_engine_result:
                return search_engine_result

            return PoetryAPI._get_local_classic_poetry()
        elif poetry_type == "modern":
            for api_url in MODERN_POETRY_FALLBACK_APIS:
                poetry_text = await PoetryAPI._request_api(api_url)
                if poetry_text:
                    return poetry_text

            search_engine_result = await PoetryAPI._search_via_search_engine("现代诗", "modern")
            if search_engine_result:
                return search_engine_result

            return format_poetry(random.choice(PoetryAPI.LOCAL_MODERN_POEMS), "modern")
        elif poetry_type == "foreign":
            for api_url in FOREIGN_POETRY_FALLBACK_APIS:
                poetry_text = await PoetryAPI._request_api(api_url)
                if poetry_text:
                    return poetry_text

            search_engine_result = await PoetryAPI._search_via_search_engine("英文诗", "foreign")
            if search_engine_result:
                return search_engine_result

            return PoetryAPI._get_local_foreign_poetry()
        else:
            return None

    @staticmethod
    def _get_local_classic_poetry() -> Optional[str]:
        if not PoetryAPI.LOCAL_POEM_LIBRARY:
            return None

        selected = random.choice(PoetryAPI.LOCAL_POEM_LIBRARY)
        title = str(selected.get("title", "未知标题")).strip() or "未知标题"
        author = str(selected.get("author", "未知作者")).strip() or "未知作者"
        poem_content = str(selected.get("content", "")).strip()
        return format_poetry(f"{title}\n{author}\n{poem_content}", "classic")

    @staticmethod
    def _get_local_foreign_poetry() -> Optional[str]:
        if not PoetryAPI.LOCAL_FOREIGN_POEMS:
            return None

        selected = random.choice(PoetryAPI.LOCAL_FOREIGN_POEMS)
        title = str(selected.get("title", "未知标题")).strip() or "未知标题"
        author = str(selected.get("author", "未知作者")).strip() or "未知作者"
        translator = str(selected.get("translator", "未知")).strip() or "未知"
        english = str(selected.get("english", "（无）")).strip() or "（无）"
        chinese = str(selected.get("chinese", "（无）")).strip() or "（无）"
        block = f"{title}\n作者：{author}\n译者：{translator}\n\n英文：\n{english}\n\n中文：\n{chinese}"
        return format_poetry(block, "foreign")

    @staticmethod
    async def get_filtered_poetry(style: str = "不限", content: str = "不限", poet: str = "不限") -> Optional[str]:
        """按风格/描写内容/诗人筛选诗词（中文输入）"""
        normalized_style = PoetryAPI._normalize_filter_value(style)
        normalized_content = PoetryAPI._normalize_filter_value(content)
        normalized_poet = PoetryAPI._normalize_filter_value(poet)

        candidates = await PoetryAPI._fetch_poetry_candidates()
        if not candidates:
            candidates = PoetryAPI.LOCAL_POEM_LIBRARY[:]

        matched = []
        for poem in candidates:
            title = str(poem.get("title", "")).strip()
            author = str(poem.get("author", "")).strip()
            poem_content = str(poem.get("content", "")).strip()
            if not title and not author and not poem_content:
                continue

            if normalized_poet and normalized_poet not in author:
                continue
            if normalized_style and not PoetryAPI._match_style(normalized_style, author, poem_content, str(poem.get("style", ""))):
                continue
            if normalized_content and not PoetryAPI._match_content(normalized_content, title, poem_content, poem.get("tags")):
                continue

            matched.append(poem)

        if not matched:
            return None

        selected = random.choice(matched)
        title = str(selected.get("title", "未知标题")).strip() or "未知标题"
        author = str(selected.get("author", "未知作者")).strip() or "未知作者"
        poem_content = str(selected.get("content", "")).strip()
        return format_poetry(f"{title}\n{author}\n{poem_content}", "classic")

    @staticmethod
    async def search_poetry(keyword: str, poetry_type: str = "all") -> Optional[str]:
        """关键词检索诗歌：先 API 联网，再搜索引擎，最后本地检索"""
        normalized_keyword = (keyword or "").strip()
        normalized_type = (poetry_type or "all").strip().lower() or "all"
        if not normalized_keyword:
            return None

        online_result = await PoetryAPI._search_online_poetry(normalized_keyword, normalized_type)
        if online_result:
            return online_result

        return PoetryAPI._search_local_poetry(normalized_keyword, normalized_type)

    @staticmethod
    def _search_local_poetry(keyword: str, poetry_type: str) -> Optional[str]:
        if poetry_type in {"all", "classic"}:
            classic_matches = []
            for item in PoetryAPI.LOCAL_POEM_LIBRARY:
                title = str(item.get("title", "")).strip()
                author = str(item.get("author", "")).strip()
                poem_content = str(item.get("content", "")).strip()
                tags = item.get("tags")
                tags_text = " ".join(tags) if isinstance(tags, list) else ""
                searchable = f"{title}\n{author}\n{poem_content}\n{tags_text}"
                if not PoetryAPI._contains_keyword(searchable, keyword):
                    continue
                classic_matches.append(format_poetry(f"{title}\n{author}\n{poem_content}", "classic"))

            if classic_matches:
                return random.choice(classic_matches)

        if poetry_type in {"all", "modern"}:
            modern_matches = []
            for poem_text in PoetryAPI.LOCAL_MODERN_POEMS:
                if PoetryAPI._contains_keyword(poem_text, keyword):
                    modern_matches.append(format_poetry(poem_text, "modern"))

            if modern_matches:
                return random.choice(modern_matches)

        if poetry_type in {"all", "foreign"}:
            foreign_matches = []
            for item in PoetryAPI.LOCAL_FOREIGN_POEMS:
                title = str(item.get("title", "未知标题")).strip() or "未知标题"
                author = str(item.get("author", "未知作者")).strip() or "未知作者"
                translator = str(item.get("translator", "未知")).strip() or "未知"
                english = str(item.get("english", "（无）")).strip() or "（无）"
                chinese = str(item.get("chinese", "（无）")).strip() or "（无）"
                searchable = f"{title}\n{author}\n{translator}\n{english}\n{chinese}"
                if not PoetryAPI._contains_keyword(searchable, keyword):
                    continue
                block = f"{title}\n作者：{author}\n译者：{translator}\n\n英文：\n{english}\n\n中文：\n{chinese}"
                foreign_matches.append(format_poetry(block, "foreign"))

            if foreign_matches:
                return random.choice(foreign_matches)

        return None

    @staticmethod
    async def _search_online_poetry(keyword: str, poetry_type: str) -> Optional[str]:
        if poetry_type in {"all", "classic"}:
            classic_result = await PoetryAPI._search_online_classic_poetry(keyword)
            if classic_result:
                return classic_result

        if poetry_type in {"all", "modern"}:
            modern_result = await PoetryAPI._search_online_modern_poetry(keyword)
            if modern_result:
                return modern_result

        if poetry_type in {"all", "foreign"}:
            foreign_result = await PoetryAPI._search_online_foreign_poetry(keyword)
            if foreign_result:
                return foreign_result

        search_engine_result = await PoetryAPI._search_via_search_engine(keyword, poetry_type)
        if search_engine_result:
            return search_engine_result

        return None

    @staticmethod
    async def _search_online_classic_poetry(keyword: str) -> Optional[str]:
        candidates = await PoetryAPI._fetch_poetry_candidates()
        classic_matches = []
        for item in candidates:
            title = str(item.get("title", "")).strip()
            author = str(item.get("author", "")).strip()
            poem_content = str(item.get("content", "")).strip()
            searchable = f"{title}\n{author}\n{poem_content}"
            formatted = format_poetry(f"{title}\n{author}\n{poem_content}", "classic")
            if not PoetryAPI._contains_keyword(searchable, keyword):
                continue
            classic_matches.append(formatted)

        if classic_matches:
            return random.choice(classic_matches)

        for _ in range(max(RETRY_TIMES, 2)):
            poetry_text = await PoetryAPI._request_api(CLASSIC_POETRY_API)
            if not poetry_text:
                continue
            if PoetryAPI._contains_keyword(PoetryAPI._strip_poetry_prefix(poetry_text), keyword):
                return poetry_text

        return None

    @staticmethod
    async def _search_online_modern_poetry(keyword: str) -> Optional[str]:
        if not MODERN_POETRY_FALLBACK_APIS:
            return None

        max_attempts = max(8, len(MODERN_POETRY_FALLBACK_APIS) * 2)
        for attempt in range(max_attempts):
            api_url = MODERN_POETRY_FALLBACK_APIS[attempt % len(MODERN_POETRY_FALLBACK_APIS)]
            poetry_text = await PoetryAPI._request_api(api_url)
            if not poetry_text:
                continue
            if PoetryAPI._contains_keyword(PoetryAPI._strip_poetry_prefix(poetry_text), keyword):
                return poetry_text

        return None

    @staticmethod
    async def _search_online_foreign_poetry(keyword: str) -> Optional[str]:
        if not FOREIGN_POETRY_FALLBACK_APIS:
            return None

        max_attempts = max(8, len(FOREIGN_POETRY_FALLBACK_APIS) * 2)
        for attempt in range(max_attempts):
            api_url = FOREIGN_POETRY_FALLBACK_APIS[attempt % len(FOREIGN_POETRY_FALLBACK_APIS)]
            poetry_text = await PoetryAPI._request_api(api_url)
            if not poetry_text:
                continue
            if PoetryAPI._contains_keyword(PoetryAPI._strip_poetry_prefix(poetry_text), keyword):
                return poetry_text

        return None

    @staticmethod
    async def _search_via_search_engine(keyword: str, poetry_type: str) -> Optional[str]:
        """通过搜索引擎结果页提取诗句内容作为最终兜底"""
        query_type = {
            "classic": "古诗词",
            "modern": "现代诗",
            "foreign": "英文诗 译文",
            "all": "诗歌",
        }.get(poetry_type, "诗歌")
        query = quote_plus(f"{keyword} {query_type} 原文")

        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                request_timeout = max(3, API_TIMEOUT // 2)
                for template in SEARCH_ENGINE_URLS:
                    url = template.format(query=query)
                    try:
                        async with session.get(url, timeout=request_timeout) as response:
                            if response.status != 200:
                                continue
                            html_text = await response.text(errors="ignore")
                    except Exception:
                        continue

                    extracted = PoetryAPI._extract_poetry_from_search_html(html_text, keyword, poetry_type)
                    if not extracted:
                        continue

                    return format_poetry(extracted, PoetryAPI._normalize_poetry_type(poetry_type))
        except Exception as e:
            LOG.warning(f"搜索引擎兜底失败: {e}")

        return None

    @staticmethod
    def _extract_poetry_from_search_html(html_text: str, keyword: str, poetry_type: str) -> Optional[str]:
        if not html_text:
            return None

        text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html_text)
        text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
        text = re.sub(r"(?is)<[^>]+>", "\n", text)
        text = unescape(text)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        blacklist_tokens = [
            "www.",
            "http",
            "cookie",
            "privacy",
            "登录",
            "注册",
            "下一页",
            "上一页",
            "搜索",
            "百度",
            "bing",
            "duckduckgo",
            "知乎",
            "zhihu",
            "课文",
            "教材",
            "下载",
            "视频",
            "广告",
            "百科",
        ]

        candidates = []
        for line in lines:
            lowered = line.lower()
            if any(token in lowered for token in blacklist_tokens):
                continue
            if len(line) < 8 or len(line) > 120:
                continue
            if re.fullmatch(r"[a-z0-9.-]+\.(com|cn|org|net)", lowered):
                continue
            if re.search(r"(19|20)\d{2}\s*年", line):
                continue
            if "·" in line and re.search(r"\d", line):
                continue
            if " - " in line or "—" in line:
                continue
            if re.search(r"第\s*[一二三四五六七八九十0-9]+\s*课", line):
                continue
            if any(flag in line for flag in ["讨论话题", "如何理解", "是什么", "为什么", "怎么办", "怎么理解"]):
                continue
            if not re.search(r"[\u4e00-\u9fffA-Za-z]{4,}", line):
                continue
            if poetry_type in {"classic", "modern", "all"} and not re.search(r"[\u4e00-\u9fff]{2,}", line):
                continue
            if re.search(r"[，。！？；：,.!?;:]", line):
                candidates.append(line)

        if not candidates:
            return None

        keyword_matches = [line for line in candidates if PoetryAPI._contains_keyword(line, keyword)]
        if not keyword_matches:
            return None
        picked = keyword_matches[:4]
        if len(picked) < 2 and len(candidates) >= 2:
            picked = (keyword_matches + [line for line in candidates if line not in keyword_matches])[:2]
        if len(picked) < 2:
            return None
        return "\n".join(picked)

    @staticmethod
    def _normalize_poetry_type(poetry_type: str) -> str:
        return poetry_type if poetry_type in {"classic", "modern", "foreign"} else "classic"

    @staticmethod
    def _contains_keyword(content: str, keyword: str) -> bool:
        if not content or not keyword:
            return False
        return keyword.casefold() in content.casefold()

    @staticmethod
    async def _fetch_poetry_candidates() -> List[Dict]:
        """获取可筛选的诗词候选列表"""
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        def parse_items(payload: Dict) -> List[Dict]:
            if not isinstance(payload, dict):
                return []
            result = payload.get("result")
            if isinstance(result, list):
                return [item for item in result if isinstance(item, dict)]
            if isinstance(result, dict):
                return [result]
            return []

        async def load_payload(session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                try:
                    return await response.json(content_type=None)
                except Exception:
                    text = await response.text()
                    try:
                        return json.loads(text)
                    except Exception:
                        return None

        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # 优先尝试批量拉取
                bulk_payload = await load_payload(session, "https://api.apiopen.top/getPoetry?page=1&count=20")
                bulk_items = parse_items(bulk_payload or {})
                if bulk_items:
                    return bulk_items

                # 批量失败时，退化为多次小批量采样
                sampled_items: List[Dict] = []
                seen = set()
                for _ in range(12):
                    one_payload = await load_payload(session, "https://api.apiopen.top/getPoetry?page=1&count=1")
                    for item in parse_items(one_payload or {}):
                        key = (
                            str(item.get("title", "")).strip(),
                            str(item.get("author", "")).strip(),
                            str(item.get("content", "")).strip(),
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        sampled_items.append(item)

                return sampled_items
        except Exception as e:
            LOG.error(f"获取筛选候选失败: {e}")
            return []

    @staticmethod
    def _normalize_filter_value(value: str) -> str:
        normalized = (value or "").strip()
        if normalized in {"", "不限", "全部", "任意", "无"}:
            return ""
        return normalized

    @staticmethod
    def _match_style(style: str, author: str, content: str, style_tag: str = "") -> bool:
        style_name = PoetryAPI.STYLE_ALIAS.get(style, style)
        if style_name not in PoetryAPI.STYLE_POETS:
            return True

        if style_tag == style_name:
            return True

        if author in PoetryAPI.STYLE_POETS[style_name]:
            return True

        if style_name == "婉约派":
            keywords = ["愁", "相思", "梦", "雨", "花", "月", "伊人", "泪"]
        else:
            keywords = ["山河", "江山", "长风", "万里", "壮", "豪", "战", "塞", "关"]

        return any(keyword in content for keyword in keywords)

    @staticmethod
    def _match_content(content: str, title: str, poem_content: str, tags=None) -> bool:
        target = f"{title}\n{poem_content}"
        if isinstance(tags, list) and content in tags:
            return True
        keywords = PoetryAPI.TOPIC_KEYWORDS.get(content)
        if keywords:
            return any(keyword in target for keyword in keywords)

        # 非预设类别时按关键词模糊匹配
        return content in target
    
    @staticmethod
    async def _request_api(api_url: str) -> Optional[str]:
        """核心API请求逻辑"""
        try:
            timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        LOG.warning(f"API状态码错误 {api_url}: {response.status}")
                        return None
                    
                    # 处理不同返回格式
                    if api_url.endswith(".txt"):
                        text = await response.text(encoding="utf-8")
                        if not text.strip():
                            return None
                        return format_poetry(text, "classic")
                    else:
                        try:
                            data = await response.json()
                            return PoetryAPI._parse_json_poetry(data, api_url)
                        except Exception:
                            # 某些API虽然不是.txt结尾，但可能返回纯文本，尝试作为文本解析
                            text = await response.text()
                            return PoetryAPI._parse_plain_text_poetry(text, api_url)
        except Exception as e:
            LOG.error(f"API请求异常 {api_url}: {e}")
            return None

    @staticmethod
    def _parse_plain_text_poetry(text: str, api_url: str) -> Optional[str]:
        """解析纯文本返回，过滤HTML等非诗词内容"""
        stripped_text = (text or "").strip()
        if not stripped_text:
            return None

        lowered = stripped_text.lower()
        if lowered.startswith("<") or "<html" in lowered or "<!doctype" in lowered:
            if PoetryAPI._is_html_shell_page(stripped_text):
                LOG.warning(f"检测到HTML壳页面，跳过该接口: {api_url}")
                return None
            return PoetryAPI._extract_poetry_from_html(stripped_text, api_url)

        if len(stripped_text) >= 500:
            return None

        if "hitokoto" in api_url:
            poetry_type = "modern"
        elif "zenquotes.io" in api_url:
            poetry_type = "foreign"
        else:
            poetry_type = "classic"
        return format_poetry(stripped_text, poetry_type)

    @staticmethod
    def _is_html_shell_page(html_text: str) -> bool:
        lowered = html_text.lower()
        shell_markers = [
            '<div id="root"',
            "<div id=root",
            "type=\"module\"",
            "type=module",
            "modulepreload",
            "crossorigin",
            "<script",
            "<link rel=\"stylesheet\"",
            "<link rel=stylesheet",
        ]
        poem_markers = [
            "hitokoto",
            "poetry",
            "content",
            "sentence",
            "诗",
        ]
        has_shell = sum(marker in lowered for marker in shell_markers) >= 3
        has_poem_hint = any(marker in lowered for marker in poem_markers)
        return has_shell and not has_poem_hint

    @staticmethod
    def _extract_poetry_from_html(html_text: str, api_url: str) -> Optional[str]:
        """从HTML页面中尽量提取诗歌内容"""
        if not html_text:
            return None

        embedded_poetry = PoetryAPI._extract_poetry_from_embedded_json(html_text, api_url)
        if embedded_poetry:
            return embedded_poetry

        text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html_text)
        text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
        text = re.sub(r"(?i)</?(br|p|div|li|h[1-6])[^>]*>", "\n", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        text = unescape(text)

        raw_lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in raw_lines if line]
        if not lines:
            return None

        blacklist = {
            "api 开放平台",
            "napcat webui",
            "charset",
            "viewport",
            "module",
            "crossorigin",
            "favicon",
            "root",
            "title",
            "description",
        }

        poetry_lines = []
        for line in lines:
            lowered = line.lower()
            if any(token in lowered for token in blacklist):
                continue
            if len(line) < 4 or len(line) > 80:
                continue
            if re.search(r"[，。！？；：,.!?;:]", line) or re.search(r"[\u4e00-\u9fff]{2,}", line):
                poetry_lines.append(line)

        if len(poetry_lines) < 2:
            return None

        poetry_type = PoetryAPI._infer_poetry_type_from_url(api_url)

        poem = "\n".join(poetry_lines[:8])
        return format_poetry(poem, poetry_type)

    @staticmethod
    def _extract_poetry_from_embedded_json(html_text: str, api_url: str) -> Optional[str]:
        """从HTML中的script内嵌JSON里提取诗歌"""
        script_blocks = re.findall(r"(?is)<script[^>]*>(.*?)</script>", html_text)
        if not script_blocks:
            return None

        for script in script_blocks:
            candidates = []

            stripped = script.strip()
            if stripped and (stripped.startswith("{") or stripped.startswith("[")):
                candidates.append(stripped)

            for marker in [
                "window.__INITIAL_STATE__",
                "window.__NEXT_DATA__",
                "window.__NUXT__",
                "globalThis.__INITIAL_STATE__",
            ]:
                assigned = PoetryAPI._extract_assigned_json(script, marker)
                if assigned:
                    candidates.append(assigned)

            for candidate in candidates:
                try:
                    payload = json.loads(candidate)
                except Exception:
                    continue

                content = PoetryAPI._extract_text_from_unknown_json(payload)
                if not content:
                    continue

                poetry_type = PoetryAPI._infer_poetry_type_from_url(api_url)
                return format_poetry(content, poetry_type)

            quick_matches = re.findall(
                r'"(?:content|text|poetry|sentence)"\s*:\s*"((?:\\.|[^"\\]){8,2000})"',
                script,
                re.DOTALL,
            )
            for raw_value in quick_matches:
                try:
                    decoded = json.loads(f'"{raw_value}"')
                except Exception:
                    decoded = raw_value
                cleaned = (decoded or "").strip()
                if not cleaned:
                    continue
                poetry_type = PoetryAPI._infer_poetry_type_from_url(api_url)
                return format_poetry(cleaned, poetry_type)

        return None

    @staticmethod
    def _extract_assigned_json(script: str, marker: str) -> Optional[str]:
        marker_index = script.find(marker)
        if marker_index < 0:
            return None

        assign_index = script.find("=", marker_index)
        if assign_index < 0:
            return None

        for start_char in ("{", "["):
            start_index = script.find(start_char, assign_index)
            if start_index < 0:
                continue
            balanced = PoetryAPI._extract_balanced_json(script, start_index)
            if balanced:
                return balanced
        return None

    @staticmethod
    def _extract_balanced_json(text: str, start_index: int) -> Optional[str]:
        if start_index < 0 or start_index >= len(text):
            return None

        opening = text[start_index]
        closing = "}" if opening == "{" else "]"

        depth = 0
        in_string = False
        escaped = False

        for index in range(start_index, len(text)):
            char = text[index]

            if in_string:
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    return text[start_index:index + 1]

        return None

    @staticmethod
    def _infer_poetry_type_from_url(api_url: str) -> str:
        if "hitokoto" in api_url:
            return "modern"
        if "zenquotes.io" in api_url:
            return "foreign"
        return "classic"

    @staticmethod
    def _is_sufficient_poetry(poetry_text: str) -> bool:
        """判断返回文本是否足够完整，避免只返回一句话"""
        if not poetry_text:
            return False

        content = poetry_text.strip()
        if content.startswith("【") and "】\n" in content:
            content = content.split("\n", 1)[1].strip()

        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if len(lines) >= 2:
            return True

        return len(content) >= 24

    @staticmethod
    def _strip_poetry_prefix(poetry_text: str) -> str:
        """去掉已格式化前缀，便于按新类型重新格式化"""
        if not poetry_text:
            return ""

        content = poetry_text.strip()
        if content.startswith("【") and "】\n" in content:
            return content.split("\n", 1)[1].strip()
        return content
    
    @staticmethod
    def _parse_json_poetry(data: Dict, api_url: str) -> Optional[str]:
        """解析JSON格式诗歌"""
        try:
            if "zenquotes.io" in api_url and isinstance(data, list) and data:
                quote = data[0] if isinstance(data[0], dict) else {}
                english = str(quote.get("q", "")).strip()
                author = str(quote.get("a", "未知作者")).strip() or "未知作者"
                if english:
                    block = f"Random English Verse\n作者：{author}\n译者：未知\n\n英文：\n{english}\n\n中文：\n（暂无在线中文译文）"
                    return format_poetry(block, "foreign")

            if not isinstance(data, dict):
                return None

            if isinstance(data.get("code"), int) and data.get("code") not in {0, 200}:
                LOG.warning(f"API返回错误信息: {data.get('message')}")
                return None

            if "hitokoto" in api_url:
                hitokoto = str(data.get("hitokoto", "")).strip()
                source = str(data.get("from", "未知来源")).strip() or "未知来源"
                author = str(data.get("from_who", "")).strip()
                if hitokoto:
                    if author:
                        return format_poetry(f"{hitokoto}\n—— {author}《{source}》", "modern")
                    return format_poetry(f"{hitokoto}\n—— 《{source}》", "modern")

            # 尝试常见现代诗结构
            extracted_content = PoetryAPI._extract_text_from_unknown_json(data)
            if extracted_content:
                return format_poetry(extracted_content, "modern")
            
            # 尝试通用解析结构 (result as string)
            if isinstance(data.get("result"), str):
                 return format_poetry(data["result"], "modern")
                 
            return None
        except Exception as e:
            LOG.error(f"解析JSON失败: {e}")
            return None

    @staticmethod
    def _extract_text_from_unknown_json(data: Dict) -> Optional[str]:
        """从常见JSON结构中提取文本内容"""
        if not isinstance(data, dict):
            return None

        direct_keys = ["content", "text", "poetry", "sentence", "data"]
        for key in direct_keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        result = data.get("result")
        if isinstance(result, dict):
            for key in ["content", "text", "poetry", "sentence"]:
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                for key in ["content", "text", "poetry", "sentence"]:
                    value = first.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        return None

    @staticmethod
    def _extract_modern_poetry_text(data: Dict) -> Optional[str]:
        """提取现代诗接口中的文本"""
        if not isinstance(data, dict):
            return None

        result = data.get("data") if isinstance(data.get("data"), dict) else data
        title = str(result.get("title", "")).strip() if isinstance(result, dict) else ""
        author = str(result.get("author", "")).strip() if isinstance(result, dict) else ""
        content = str(result.get("content", "")).strip() if isinstance(result, dict) else ""

        if content and (title or author):
            return f"{title}\n{author}\n{content}".strip()
        if content:
            return content
        return None

    @staticmethod
    def _extract_foreign_bilingual_payload(data: Dict) -> Optional[Tuple[str, str, str, str, str]]:
        """提取双语外国诗字段"""
        if not isinstance(data, dict):
            return None

        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(payload, dict):
            return None

        title = str(payload.get("title", "未知标题")).strip() or "未知标题"
        author = str(payload.get("author", "未知作者")).strip() or "未知作者"
        translator = str(payload.get("translator", "未知")).strip() or "未知"
        english = str(payload.get("english", "")).strip()
        chinese = str(payload.get("chinese", "")).strip()

        if not english and not chinese:
            return None

        return title, author, translator, english or "（无）", chinese or "（无）"


PoetryAPI._load_external_libraries()