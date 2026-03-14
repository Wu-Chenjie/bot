from ncatbot.utils import get_log
from .config import POETRY_API_LIST, API_TIMEOUT, RETRY_TIMES
from .utils import format_poetry
import aiohttp
import random
import json
from typing import Optional, Dict, List

LOG = get_log("PoetryPlugin-API")

class PoetryAPI:
    """诗歌API请求类"""

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
                if poetry_text and PoetryAPI._is_sufficient_poetry(poetry_text):
                    return poetry_text
                if poetry_text:
                    fallback_text = fallback_text or poetry_text
                    LOG.info(f"返回内容过短，重试其他API: {api_url}")
            except Exception as e:
                LOG.warning(f"API请求重试 {api_url}: {e}")
        return fallback_text
    
    @staticmethod
    async def get_poetry_by_type(poetry_type: str) -> Optional[str]:
        """按类型获取诗歌"""
        if poetry_type == "classic":
            # 优先返回结构更完整的古诗词
            primary_url = "https://api.apiopen.top/getPoetry?page=1&count=1"
            fallback_url = "https://v1.jinrishici.com/rensheng.txt"
            primary_text = await PoetryAPI._request_api(primary_url)
            if primary_text and PoetryAPI._is_sufficient_poetry(primary_text):
                return primary_text
            fallback_text = await PoetryAPI._request_api(fallback_url)
            if fallback_text and PoetryAPI._is_sufficient_poetry(fallback_text):
                return fallback_text
            return primary_text or fallback_text
        elif poetry_type == "modern":
            modern_candidates = [
                "https://api.apiopen.top/singlePoetry",
                "https://api.apiopen.top/getPoetry?page=1&count=1",
            ]

            fallback_text = None
            for api_url in modern_candidates:
                poetry_text = await PoetryAPI._request_api(api_url)
                if poetry_text and PoetryAPI._is_sufficient_poetry(poetry_text):
                    return poetry_text
                if poetry_text:
                    fallback_text = fallback_text or poetry_text

            if fallback_text:
                return fallback_text

            random_text = await PoetryAPI.get_random_poetry()
            if random_text:
                normalized_text = PoetryAPI._strip_poetry_prefix(random_text)
                return format_poetry(normalized_text, "modern")

            return None
        else:
            return None

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
            return None

        if len(stripped_text) >= 500:
            return None

        poetry_type = "modern" if "singlePoetry" in api_url else "classic"
        return format_poetry(stripped_text, poetry_type)

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
            # 通用处理：检查code字段（许多API都有）
            if data.get("code", 200) != 200:
                LOG.warning(f"API返回错误信息: {data.get('message')}")
                return None

            if "apiopen.top/getPoetry" in api_url:
                # 古诗词JSON
                result = data.get("result")
                if isinstance(result, list) and result:
                    poetry = result[0]
                    content = poetry.get("content", "")
                    author = poetry.get("author", "未知")
                    title = poetry.get("title", "未知")
                    return format_poetry(f"{title}\n{author}\n{content}", "classic")
            elif "apiopen.top/singlePoetry" in api_url:
                # 现代诗
                content = data.get("result", "")
                if content:
                    return format_poetry(content, "modern")

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