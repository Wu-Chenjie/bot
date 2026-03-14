from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.plugin_system import admin_filter
from ncatbot.plugin_system import param
from ncatbot.core import BaseMessageEvent, GroupMessageEvent, MessageChain, Text
from ncatbot.utils import get_log
from .config import COMMAND_ALIASES
from .poetry_api import PoetryAPI
from .schedule_manager import ScheduleManager

LOG = get_log("PoetryPlugin")

class PoetryPlugin(NcatBotPlugin):
    name = "PoetryPlugin"
    version = "1.3.1"
    author = "Developer"
    description = "自动/手动发送古诗词/现代诗的插件，支持定时发送"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化定时管理器
        self.schedule_manager = ScheduleManager()
    
    async def on_load(self):
        """插件加载回调"""
        # 注入Bot实例
        if hasattr(self, "bot"):
            self.schedule_manager.set_bot(self.bot)
            
        LOG.info(f"{self.name} 插件已加载（版本：{self.version}）")
        # 启动定时任务
        self.schedule_manager.start_schedule_task()
    
    # ========== 普通用户命令 ==========
    @command_registry.command("poetry", aliases=COMMAND_ALIASES["poetry"], description="获取随机诗歌")
    async def poetry_cmd(self, event: BaseMessageEvent):
        """获取随机诗歌"""
        poetry_text = await PoetryAPI.get_random_poetry()
        if not poetry_text:
            await event.reply(MessageChain([Text("获取诗歌失败，请稍后重试~")]))
            return
        await event.reply(MessageChain([Text(poetry_text)]))

    @command_registry.command("help", aliases=COMMAND_ALIASES["help"], description="查看诗歌插件帮助")
    async def help_cmd(self, event: BaseMessageEvent):
        """输出插件可用命令帮助"""
        help_text = (
            "📘 诗歌插件命令帮助\n"
            "- /help：查看本帮助\n"
            "- /poetry：随机诗歌\n"
            "- /poetry_type <type>：按类型获取（古诗词/现代诗/双语外国诗）\n"
            "- /poetry_filter <style> <content> <poet>：按条件筛选\n"
            "- /poetry_search <keyword> [type]：关键词搜索（本地→联网）\n"
            "\n"
            "示例：\n"
            "/poetry_search 李白 古诗词\n"
            "/poetry_search moon 双语外国诗"
        )
        await event.reply(MessageChain([Text(help_text)]))
    
    @command_registry.command("poetry_type", aliases=COMMAND_ALIASES["poetry_type"], description="指定类型获取诗歌（古诗词/现代诗/双语外国诗）")
    @param(name="type", default="古诗词", help="诗歌类型：古诗词/现代诗/双语外国诗")
    async def poetry_type_cmd(self, event: BaseMessageEvent, type: str = "古诗词"):
        """指定类型获取诗歌"""
        type_mapping = {
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
        normalized_type = type_mapping.get((type or "").strip())
        if not normalized_type:
            await event.reply(MessageChain([Text("类型错误！支持：古诗词 / 现代诗 / 双语外国诗")]))
            return
        
        poetry_text = await PoetryAPI.get_poetry_by_type(normalized_type)
        if not poetry_text:
            await event.reply(MessageChain([Text(f"获取{type}类型诗歌失败，请稍后重试~")]))
            return
        await event.reply(MessageChain([Text(poetry_text)]))

    @command_registry.command("poetry_filter", aliases=COMMAND_ALIASES["poetry_filter"], description="按风格/内容/诗人筛选诗词（中文输入）")
    @param(name="style", default="不限", help="风格：婉约派/豪放派/不限")
    @param(name="content", default="不限", help="描写内容：思乡/离别/山水/边塞/爱情/不限")
    @param(name="poet", default="不限", help="诗人：如李白、杜甫、苏轼；不限可留空")
    async def poetry_filter_cmd(self, event: BaseMessageEvent, style: str = "不限", content: str = "不限", poet: str = "不限"):
        """按风格、内容、诗人筛选诗词（中文输入）"""
        poetry_text = await PoetryAPI.get_filtered_poetry(style=style, content=content, poet=poet)
        if not poetry_text:
            tip = "未筛选到匹配诗词，可尝试放宽条件。例如：/poetry_filter 婉约派 不限 李清照"
            await event.reply(MessageChain([Text(tip)]))
            return
        await event.reply(MessageChain([Text(poetry_text)]))

    @command_registry.command("poetry_search", aliases=COMMAND_ALIASES["poetry_search"], description="关键词检索诗歌（未命中本地时自动联网搜索）")
    @param(name="keyword", help="检索关键词，如：月、李白、乡愁")
    @param(name="type", default="不限", help="类型：古诗词/现代诗/双语外国诗/不限")
    async def poetry_search_cmd(self, event: BaseMessageEvent, keyword: str, type: str = "不限"):
        """关键词检索诗歌，本地未命中时自动联网搜索"""
        normalized_keyword = (keyword or "").strip()
        if not normalized_keyword:
            await event.reply(MessageChain([Text("请提供检索关键词，例如：/poetry_search 月 现代诗")] ))
            return

        type_mapping = {
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
        normalized_type = type_mapping.get((type or "").strip())
        if not normalized_type:
            await event.reply(MessageChain([Text("类型错误！支持：不限 / 古诗词 / 现代诗 / 双语外国诗")]))
            return

        poetry_text = await PoetryAPI.search_poetry(normalized_keyword, normalized_type)
        if not poetry_text:
            await event.reply(MessageChain([Text("未检索到匹配诗歌（已尝试联网搜索），可更换关键词重试~")]))
            return
        await event.reply(MessageChain([Text(poetry_text)]))
    
    # ========== 管理员命令 ==========
    @admin_filter
    @command_registry.command("poetry_schedule", aliases=COMMAND_ALIASES["poetry_schedule"], description="配置定时发送群聊（管理员）")
    @param(name="action", default="add", help="操作：add/remove")
    @param(name="group_id", help="群聊ID")
    async def poetry_schedule_cmd(self, event: BaseMessageEvent, action: str = "add", group_id: int = None):
        """配置定时发送群聊"""
        # 仅群聊管理员可操作
        if not isinstance(event, GroupMessageEvent):
            await event.reply(MessageChain([Text("该命令仅支持群聊使用~")]))
            return

        action = (action or "").strip().lower()
        
        # 未指定群聊则使用当前群聊
        if group_id is None:
            target_group = event.group_id
        else:
            try:
                target_group = int(group_id)
            except (TypeError, ValueError):
                await event.reply(MessageChain([Text("群聊ID格式错误，请输入纯数字群号~")]))
                return
        
        if action == "add":
            success = self.schedule_manager.add_schedule_group(target_group)
            msg = f"已添加群聊 {target_group} 到定时发送列表✅" if success else f"添加失败：群聊ID不合法"
        elif action == "remove":
            success = self.schedule_manager.remove_schedule_group(target_group)
            msg = f"已移除群聊 {target_group} 定时发送❌" if success else f"移除失败：群聊不在定时列表中"
        else:
            msg = "用法错误！示例：\n/poetry_schedule add 123456789\n/poetry_schedule remove 123456789"
        
        await event.reply(MessageChain([Text(msg)]))
    
    @admin_filter
    @command_registry.command("poetry_status", aliases=COMMAND_ALIASES["poetry_status"], description="查看诗歌插件状态")
    async def poetry_status_cmd(self, event: BaseMessageEvent):
        """查看插件状态"""
        # 统计定时群聊数量
        group_count = len(self.schedule_manager.schedule_groups)
        # 拼接定时时间
        time_text = ", ".join([f"{t.hour}:{t.minute:02d}" for t in self.schedule_manager.schedule_times])
        
        status_text = "📜 诗歌插件状态:\n"
        status_text += f"定时发送群聊数: {group_count} 个\n"
        status_text += f"定时发送时间: {time_text}\n"
        
        # 检查API状态
        api_status = await self._check_api_status()
        status_text += f"API接口状态: {api_status}"
        
        await event.reply(MessageChain([Text(status_text)]))
    
    async def _check_api_status(self) -> str:
        """检查API可用性"""
        try:
            # 快速请求第一个API测试
            import aiohttp
            from .config import POETRY_API_LIST
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(POETRY_API_LIST[0]) as response:
                    if response.status == 200:
                        return "✅ 正常"
                    else:
                        return f"❌ 异常（状态码：{response.status}）"
        except Exception as e:
            return f"❌ 连接失败：{str(e)[:20]}..."