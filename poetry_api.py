from ncatbot.utils import get_log
from .config import POETRY_API_LIST, API_TIMEOUT, RETRY_TIMES
from .utils import format_poetry
import aiohttp
import random
from typing import Optional, Dict

LOG = get_log("PoetryPlugin-API")

class PoetryAPI:
    """诗歌API请求类"""
    
    @staticmethod
    async def get_random_poetry() -> Optional[str]:
        """随机获取一首诗歌（自动重试）"""
        if not POETRY_API_LIST:
            LOG.warning("未配置可用诗歌API")
            return None

        candidate_urls = POETRY_API_LIST[:]
        random.shuffle(candidate_urls)
        max_attempts = max(RETRY_TIMES, len(candidate_urls))

        for attempt in range(max_attempts):
            api_url = candidate_urls[attempt % len(candidate_urls)]
            try:
                poetry_text = await PoetryAPI._request_api(api_url)
                if poetry_text:
                    return poetry_text
            except Exception as e:
                LOG.warning(f"API请求重试 {api_url}: {e}")
        return None
    
    @staticmethod
    async def get_poetry_by_type(poetry_type: str) -> Optional[str]:
        """按类型获取诗歌"""
        if poetry_type == "classic":
            api_url = "https://v1.jinrishici.com/rensheng.txt"
        elif poetry_type == "modern":
            api_url = "https://api.apiopen.top/singlePoetry"
        else:
            return None
        
        return await PoetryAPI._request_api(api_url)
    
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
            
            # 尝试通用解析结构 (result as string)
            if isinstance(data.get("result"), str):
                 return format_poetry(data["result"], "modern")
                 
            return None
        except Exception as e:
            LOG.error(f"解析JSON失败: {e}")
            return None