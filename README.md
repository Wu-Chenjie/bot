# 📜 PoetryPlugin - 每日诗词插件

基于 `ncatbot` 框架开发的诗词插件，支持群聊定时推送、随机获取古诗词/现代诗等功能。为您的群聊增添一份文艺气息。

## ✨ 功能特点

- **随机诗词**：随时获取一首随机诗歌，支持古诗词和现代诗。
- **分类获取**：支持指定获取「古诗词」或「现代诗」。
- **定时推送**：支持管理员配置群聊定时任务，每日准点发送（默认早8点/晚8点）。
- **持久化存储**：定时任务配置自动保存，重启不丢失。
- **自动重试**：内置多源 API 支持与自动重试机制，提高可用性。

## 🛠️ 安装与部署

### 1. 环境要求
- Python 3.8+
- [ncatbot](https://github.com/li-2004/ncatbot) 框架
- `aiohttp` 库

### 2. 安装依赖
在项目根目录下运行：
```bash
pip install ncatbot aiohttp
```

### 3. 此插件作为一个包被加载
确保本目录（`bot` 文件夹）放置在您的 `ncatbot` 机器人项目的插件目录下，或者在启动脚本中正确引用。

例如在您的机器人启动脚本中：
```python
from ncatbot.core import Bot
from bot import PoetryPlugin  # 假设文件夹名为 bot

bot = Bot(config_path="config.yaml")
bot.register_plugin(PoetryPlugin)
bot.run()
```

## 📖 命令使用指南

> **提示**：所有命令均支持中文别名。

### 👥 普通用户命令

| 命令 | 别名 | 参数 | 说明 | 示例 |
| :--- | :--- | :--- | :--- | :--- |
| `/poetry` | `诗词`, `诗歌` | 无 | 随机获取一首诗词 | `/poetry` |
| `/poetry_type` | `诗词类型` | `type` | 指定类型获取<br>`classic`: 古诗词 (默认)<br>`modern`: 现代诗 | `/poetry_type modern` |

### 👮 管理员命令 (仅限配置的管理员)

| 命令 | 别名 | 参数 | 说明 | 示例 |
| :--- | :--- | :--- | :--- | :--- |
| `/poetry_schedule` | `诗词定时` | `action`: `add`/`remove`<br>`group_id`: (可选) | **开启/关闭**当前群聊的定时推送 | `/poetry_schedule add`<br>`/poetry_schedule remove` |
| `/poetry_status` | `诗词状态` | 无 | 查看插件运行状态、定时任务数及API状态 | `/poetry_status` |

## ⚙️ 配置说明

核心配置位于 `config.py` 文件中，您可以根据需要修改：

- **`DEFAULT_SCHEDULE_TIMES`**: 设置定时推送的时间列表。
  ```python
  # 默认每天早8点和晚8点推送
  DEFAULT_SCHEDULE_TIMES = [
      {"hour": 8, "minute": 0},
      {"hour": 20, "minute": 0}
  ]
  ```
- **`POETRY_API_LIST`**: 诗词 API 源列表。
- **`COMMAND_ALIASES`**: 自定义命令的中文别名。

## 📂 文件结构

```
bot/
├── __init__.py          # 插件导出
├── main.py              # 插件核心逻辑与命令处理
├── config.py            # 配置文件
├── schedule_manager.py  # 定时任务管理器
├── poetry_api.py        # API 请求封装
├── utils.py             # 工具函数
└── data/                # (运行时生成) 数据存储目录
    └── groups.json      # 定时发送群聊列表
```

## 📝 更新日志

- **v1.0.0**: 初始版本发布，支持基本的诗词获取与定时任务。
