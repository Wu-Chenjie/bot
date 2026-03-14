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
    version = "1.0.0"
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
    
    @command_registry.command("poetry_type", aliases=COMMAND_ALIASES["poetry_type"], description="指定类型获取诗歌（古诗词/现代诗）")
    @param(name="type", default="classic", help="诗歌类型：classic(古诗词)/modern(现代诗)")
    async def poetry_type_cmd(self, event: BaseMessageEvent, type: str = "classic"):
        """指定类型获取诗歌"""
        if type not in ["classic", "modern"]:
            await event.reply(MessageChain([Text("类型错误！支持：classic(古诗词) / modern(现代诗)")]))
            return
        
        poetry_text = await PoetryAPI.get_poetry_by_type(type)
        if not poetry_text:
            await event.reply(MessageChain([Text(f"获取{type}类型诗歌失败，请稍后重试~")]))
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