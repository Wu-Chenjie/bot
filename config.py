# 诗歌API配置
CLASSIC_POETRY_API = "https://v1.jinrishici.com/rensheng.txt"
MODERN_POETRY_API = "https://v1.hitokoto.cn/?encode=json"
FOREIGN_BILINGUAL_POETRY_API = "https://zenquotes.io/api/random"

POETRY_API_LIST = [
    CLASSIC_POETRY_API,
    MODERN_POETRY_API,
    FOREIGN_BILINGUAL_POETRY_API,
]

# 定时任务配置
DEFAULT_SCHEDULE_TIMES = [
    {"hour": 8, "minute": 0},   # 早8点
    {"hour": 20, "minute": 0}   # 晚8点
]
DEFAULT_SCHEDULE_GROUPS = []    # 默认空，建议从config.yaml读取
SCHEDULE_CHECK_INTERVAL = 10    # 定时检查间隔（秒）
SCHEDULE_SEND_DELAY = 1        # 群聊间发送延迟（秒）

# 网络请求配置
API_TIMEOUT = 10                # API请求超时（秒）
RETRY_TIMES = 2                 # API重试次数

# 命令配置
COMMAND_ALIASES = {
    "poetry": ["诗词", "诗歌"],
    "help": ["帮助", "菜单", "指令"],
    "poetry_schedule": ["诗词定时"],
    "poetry_type": ["诗词类型"],
    "poetry_status": ["诗词状态"],
    "poetry_filter": ["诗词筛选", "诗歌筛选", "诗词定制"],
    "poetry_search": ["诗词搜索", "诗歌搜索", "搜诗"]
}

POETRY_TYPE_ALIASES = {
    "不限": "all",
    "全部": "all",
    "all": "all",
    "古诗词": "classic",
    "古诗": "classic",
    "classic": "classic",
    "现代诗": "modern",
    "现代": "modern",
    "modern": "modern",
    "双语外国诗": "foreign",
    "双语": "foreign",
    "中英": "foreign",
    "外国诗": "foreign",
    "foreign": "foreign",
}