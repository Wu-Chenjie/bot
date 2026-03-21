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

### 3）创建本地配置

首次使用请复制模板并填写你自己的连接信息：

```bash
cp config.example.yaml config.yaml
```

Windows PowerShell 可用：

```powershell
Copy-Item config.example.yaml config.yaml
```

`config.yaml` 已被 `.gitignore` 忽略，不会上传到 GitHub。

### 4）启用提交前安全检查（推荐）

首次克隆后执行：

```bash
git config core.hooksPath .githooks
```

启用后，提交前会自动拦截：`config.yaml`、`.env`、`*.local.yaml` 等本地敏感配置。

### 5）启动机器人

在本目录执行：

```bash
python run.py
```

看到启动日志后，到群里发送：

```text
/help
```

若返回提示，则部署成功。

---

## 常用命令

> 下面命令都支持中文别名，表中“主命令”与“别名”任选其一。

### 普通用户

| 功能 | 主命令 | 别名 | 示例 |
| :--- | :--- | :--- | :--- |
| 帮助菜单 | `/help` | `帮助` / `菜单` / `指令` | `/help` |
| 获取随机诗词 | `/poetry` | `诗词` / `诗歌` | `/poetry` |
| 按类型获取 | `/poetry_type <type>` | `诗词类型` | `/poetry_type 古诗词` |
| 按条件筛选 | `/poetry_filter <style> <content> <poet>` | `诗词筛选` / `诗歌筛选` / `诗词定制` | `/poetry_filter 宋词·婉约派 爱情 李清照` |
| 关键词搜索 | `/poetry_search <keyword> [type]` | `诗词搜索` / `诗歌搜索` / `搜诗` | `/poetry_search 月 现代诗` |

`type` 可选：

- `不限`（兼容 `all`，默认）
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
/poetry_search 月 古诗词
/poetry_search love 双语外国诗
```

搜索规则：

- 先检索本地诗歌库（古诗/现代/双语）
- 本地未命中时，再进行联网检索
- 命中多个候选时会随机返回，避免同关键词每次固定同一结果
- 为保证结果正确性，联网结果需与关键词相关，否则返回“未检索到匹配诗歌”

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

1. `POETRY_API_LIST`：诗词 API 列表
2. `COMMAND_ALIASES`：命令别名映射

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


> 注：若你已自行更新数据库，条目数量以本地文件实际内容为准。

字段格式：

- 古诗词：`title` / `author` / `content` / `style` / `tags`
- 现代诗：字符串列表（每项为完整文本）
- 双语：`title` / `author` / `translator` / `english` / `chinese`

### 本地数据库样例

`classic_poems.json`（对象数组）：

```json
[
  {
    "title": "静夜思",
    "author": "李白",
    "content": "床前明月光，疑是地上霜。举头望明月，低头思故乡。",
    "style": "古体诗",
    "tags": ["思乡"]
  }
]
```

`modern_poems.json`（两种格式都支持，推荐对象格式）：

```json
[
  "《回答》\n作者：北岛\n卑鄙是卑鄙者的通行证，高尚是高尚者的墓志铭。"
]
```

`foreign_poems.json`（对象数组）：

```json
[
{
    "title": "If",
    "author": "Rudyard Kipling",
    "translator": "译者名",
    "english": "If you can keep your head when all about you...",
    "chinese": "如果在众人六神无主时，你能镇定自若..."
  }
]
```

建议：

- JSON 顶层使用数组
- 文本统一 UTF-8 编码
- 同一首诗避免重复入库
- 现代诗推荐使用对象格式

---

## 快速样例

群聊里可直接发送：

```text
/help
/poetry
/poetry_type 现代诗
/poetry_search 海子 现代诗
/poetry_search moon 双语外国诗
/poetry_filter 不限 思乡 不限
```

预期行为：

- 优先检索本地库
- 本地未命中时自动联网回退
- 联网结果相关性不足时返回“未检索到匹配诗歌”

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

