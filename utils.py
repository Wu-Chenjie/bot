from ncatbot.utils import get_log
from ncatbot.core import MessageChain, Text
from datetime import time

from .config import POETRY_TYPE_ALIASES

LOG = get_log("PoetryPlugin-Utils")

def format_poetry(text: str, poetry_type: str) -> str:
    """格式化诗歌文本"""
    if poetry_type == "classic":
        return f"【每日诗词】\n{text.strip()}"
    elif poetry_type == "modern":
        return f"【每日诗歌】\n{text.strip()}"
    elif poetry_type == "foreign":
        return f"【双语诗歌】\n{text.strip()}"
    else:
        return text.strip()

def parse_schedule_time(time_config: dict) -> time:
    """解析定时时间配置为time对象"""
    try:
        return time(
            hour=time_config.get("hour", 8),
            minute=time_config.get("minute", 0)
        )
    except Exception as e:
        LOG.error(f"解析定时时间失败: {e}")
        return time(hour=8, minute=0)

def validate_group_id(group_id: int) -> bool:
    """验证群聊ID合法性"""
    return isinstance(group_id, int) and group_id > 0


def normalize_poetry_type(value: str, default: str = "classic") -> str | None:
    """标准化诗歌类型输入。"""
    normalized = (value or "").strip()
    if not normalized:
        return default
    return POETRY_TYPE_ALIASES.get(normalized)


async def reply_text(event, text: str) -> None:
    """统一文本回复构造。"""
    await event.reply(MessageChain([Text(text)]))