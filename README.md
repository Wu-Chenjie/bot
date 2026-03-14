# 📜 PoetryPlugin（每日诗词插件）

一个给 QQ 群用的诗词插件：支持手动获取诗词、按类型获取、按条件筛选（风格/内容/诗人）、每天定时自动推送。

---

## 这是什么

本插件基于 `ncatbot`，核心能力：

- 随机获取诗词（古诗词/现代诗）
- 指定类型获取（支持中文输入：古诗词 / 现代诗 / 双语外国诗）
- 按条件筛选（风格、描写内容、诗人，支持中文输入）
- 管理员配置定时推送群聊
- 定时群聊持久化保存（重启后不丢失）
- 启动单实例保护（避免重复启动导致重复回复）
- 外置本地诗歌库（古诗/现代/双语均支持）

---

## 5 分钟快速开始（推荐按顺序）

### 1）准备环境

- Python 3.8+
- 已可运行的 `ncatbot` 环境

安装依赖：

```bash
pip install ncatbot aiohttp pyyaml
```

### 2）确认目录名

当前插件目录名应为：`bot`

因为代码中默认按 `bot` 包导入（`from bot.main import PoetryPlugin`）。

### 3）启动机器人

在本目录执行：

```bash
python run.py
```

看到启动日志后，到群里发送：

```text
/poetry
```

若返回诗词，说明部署成功。

---

## 常用命令

> 下面命令都支持中文别名，表中“主命令”与“别名”任选其一。

### 普通用户

| 功能 | 主命令 | 别名 | 示例 |
| :--- | :--- | :--- | :--- |
| 获取随机诗词 | `/poetry` | `诗词` / `诗歌` | `/poetry` |
| 按类型获取 | `/poetry_type <type>` | `诗词类型` | `/poetry_type 古诗词` |
| 按条件筛选 | `/poetry_filter <style> <content> <poet>` | `诗词筛选` / `诗歌筛选` / `诗词定制` | `/poetry_filter 婉约派 爱情 李清照` |

`type` 可选：

- `古诗词`（兼容 `classic`）
- `现代诗`（兼容 `modern`）
- `双语外国诗`（兼容 `foreign`）

筛选参数说明：

- `style`：`婉约派` / `豪放派` / `不限`
- `content`：`思乡` / `离别` / `山水` / `边塞` / `爱情` / `不限`
- `poet`：诗人名（如 `李白`、`杜甫`、`苏轼`），或 `不限`

筛选命令示例：

```text
/poetry_filter 婉约派 爱情 李清照
/poetry_filter 豪放派 边塞 辛弃疾
/poetry_filter 不限 思乡 不限
```

### 管理员

| 功能 | 主命令 | 别名 | 示例 |
| :--- | :--- | :--- | :--- |
| 添加定时群 | `/poetry_schedule add [group_id]` | `诗词定时` | `/poetry_schedule add` |
| 移除定时群 | `/poetry_schedule remove [group_id]` | `诗词定时` | `/poetry_schedule remove` |
| 查看插件状态 | `/poetry_status` | `诗词状态` | `/poetry_status` |

说明：

- `group_id` 不填时，默认使用“当前群号”
- 只有管理员命令可以改定时配置

---

## 配置项说明

### `config.py`

1. `DEFAULT_SCHEDULE_TIMES`：定时推送时间

```python
DEFAULT_SCHEDULE_TIMES = [
  {"hour": 8, "minute": 0},
  {"hour": 20, "minute": 0}
]
```

2. `POETRY_API_LIST`：诗词 API 列表（随机 + 重试）
3. `COMMAND_ALIASES`：命令别名映射

### `config.yaml`

机器人连接配置（由 `run.py` 读取），按你本机/服务器实际地址填写。

---

## 数据存储

- 定时群配置保存在：`data/groups.json`
- 文件由程序自动创建，无需手动新建

### 本地诗歌库（外置）

诗歌库已外置到以下文件，程序启动时会优先加载：

- `data/poetry_library/classic_poems.json`（古诗词）
- `data/poetry_library/modern_poems.json`（现代诗）
- `data/poetry_library/foreign_poems.json`（双语外国诗）

当前每个库均为 **120 条**（100+）。

字段格式：

- 古诗词：`title` / `author` / `content` / `style` / `tags`
- 现代诗：字符串列表（每项为完整文本）
- 双语：`title` / `author` / `translator` / `english` / `chinese`

---

## 常见问题（FAQ）

### 1）报错：`No module named 'bot.main'`

通常是目录名或运行路径问题：

- 确认目录名是 `bot`
- 从插件目录执行 `python run.py`

### 2）报错：`No module named 'ncatbot'`

依赖未安装到当前 Python 环境：

```bash
pip install ncatbot aiohttp pyyaml
```

如果你使用虚拟环境，请用该环境的 Python 执行安装和启动。

### 3）现代诗偶尔为空

这是上游接口波动导致的正常现象；插件已做多源回退、本地候选兜底，并支持从网页 HTML / 内嵌 JSON 尝试提取诗歌文本，通常会尽量返回可用结果。

### 5）为什么有些在线 API 被移除

已移除当前环境不可用或返回壳页面的接口（如 DNS 失败或仅返回前端 HTML）。

当前线上优先源：

- 古诗词：`v1.jinrishici.com`
- 现代诗：`v1.hitokoto.cn`（含国际镜像回退）
- 双语外国诗：`zenquotes.io`

若线上返回 HTML，程序会先识别壳页面并跳过，避免误判为诗歌内容。

### 4）提示“已检测到机器人实例正在运行”

这是正常保护机制：`run.py` 已启用单实例锁，避免重复启动造成同一命令回复两次。

若确认当前没有在运行，可关闭旧终端后重试。

---

## 项目结构

```text
bot/
├── __init__.py
├── main.py
├── config.py
├── config.yaml
├── poetry_api.py
├── schedule_manager.py
├── utils.py
├── run.py
└── data/
  ├── groups.json  # 运行后生成
  └── poetry_library/
      ├── classic_poems.json
      ├── modern_poems.json
      └── foreign_poems.json
```

---

## 版本

- `v1.2.0`：新增双语外国诗类型、现代诗 HTML/内嵌 JSON 提取回退、`run.py` 单实例启动保护
- `v1.3.0`：本地诗歌库外置化（三库均 100+）、移除不可用线上源、增强 HTML 壳页面识别
- `v1.3.1`：统一发布版本号为 `1.3.1`，补充运行产物忽略规则（`.bot_run.lock`、`napcat/`）
