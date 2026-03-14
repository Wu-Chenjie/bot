from ncatbot.utils import get_log
from .config import DEFAULT_SCHEDULE_TIMES, DEFAULT_SCHEDULE_GROUPS, SCHEDULE_CHECK_INTERVAL, SCHEDULE_SEND_DELAY
from .utils import parse_schedule_time, validate_group_id
from .poetry_api import PoetryAPI
import asyncio
import json
import os
from datetime import datetime, time
from typing import List, Set

LOG = get_log("PoetryPlugin-Schedule")

class ScheduleManager:
    """定时任务管理器"""
    
    def __init__(self):
        self.schedule_times: List[time] = [parse_schedule_time(t) for t in DEFAULT_SCHEDULE_TIMES]
        self.schedule_groups: Set[int] = set(DEFAULT_SCHEDULE_GROUPS)
        self.bot = None  # 由插件注入
        
        # 数据持久化路径
        self.data_file = os.path.join(os.path.dirname(__file__), "data", "groups.json")
        self._load_groups()
    
    def set_bot(self, bot):
        """注入机器人实例"""
        self.bot = bot

    def _load_groups(self):
        """加载定时群聊列表"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    groups = json.load(f)
                    if isinstance(groups, list):
                        self.schedule_groups.update(groups)
            except Exception as e:
                LOG.error(f"加载群聊配置失败: {e}")

    def _save_groups(self):
        """保存定时群聊列表"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(list(self.schedule_groups), f)
        except Exception as e:
            LOG.error(f"保存群聊配置失败: {e}")
    
    def add_schedule_group(self, group_id: int) -> bool:
        """添加定时发送群聊"""
        if validate_group_id(group_id):
            if group_id not in self.schedule_groups:
                self.schedule_groups.add(group_id)
                self._save_groups()
                LOG.info(f"添加定时群聊: {group_id}")
            return True
        return False
    
    def remove_schedule_group(self, group_id: int) -> bool:
        """移除定时发送群聊"""
        if group_id in self.schedule_groups:
            self.schedule_groups.remove(group_id)
            self._save_groups()
            LOG.info(f"移除定时群聊: {group_id}")
            return True
        return False
    
    def start_schedule_task(self):
        """启动定时任务"""
        async def schedule_job():
            LOG.info("定时任务监视器已启动")
            while True:
                try:
                    now = datetime.now()
                    current_time = (now.hour, now.minute)
                    
                    # 检查是否到达定时时间
                    for target_time in self.schedule_times:
                        if (target_time.hour, target_time.minute) == current_time:
                            LOG.info(f"触发定时任务时间点: {target_time}")
                            await self._send_schedule_poetry()
                            break  # 避免同一分钟重复触发

                    # 对齐到下一分钟，避免频繁轮询
                    now = datetime.now()
                    sleep_seconds = 60 - now.second
                    await asyncio.sleep(sleep_seconds + 1)
                except Exception as e:
                    LOG.error(f"定时任务循环发生错误: {e}")
                    await asyncio.sleep(30)  # 错误后等待一段时间重试
        
        asyncio.create_task(schedule_job())
    
    async def _send_schedule_poetry(self):
        """执行定时发送"""
        if not self.schedule_groups or not self.bot:
            LOG.warning("定时发送条件不满足：无群聊/无机器人实例")
            return
        
        poetry_text = await PoetryAPI.get_random_poetry()
        if not poetry_text:
            LOG.error("定时发送失败：获取诗歌为空")
            return
        
        # 发送到所有定时群聊
        for group_id in self.schedule_groups:
            try:
                from ncatbot.core import MessageChain, Plain
                await self.bot.send_group_message(
                    group_id=group_id,
                    message_chain=MessageChain([Plain(poetry_text)])
                )
                LOG.info(f"定时发送诗歌到群聊 {group_id} 成功")
                await asyncio.sleep(SCHEDULE_SEND_DELAY)
            except Exception as e:
                LOG.error(f"定时发送到群聊 {group_id} 失败: {e}")