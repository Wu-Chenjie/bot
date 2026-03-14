# 诗歌API配置
POETRY_API_LIST = [
    # 古诗词大全（文本格式）
    "https://v1.jinrishici.com/rensheng.txt",
    # 随机诗词（JSON格式）
    "https://api.apiopen.top/getPoetry?page=1&count=1",
    # 现代诗（JSON格式）
    "https://api.apiopen.top/singlePoetry"
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
    "poetry_schedule": ["诗词定时"],
    "poetry_type": ["诗词类型"],
    "poetry_status": ["诗词状态"],
    "poetry_filter": ["诗词筛选", "诗歌筛选", "诗词定制"]
}