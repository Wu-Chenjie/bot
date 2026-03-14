import sys
import os
from pathlib import Path

# ----------------------------------------------------------------
# 技巧：将上级目录加入 sys.path，模拟包导入
# 这样就可以支持 plugin 内部的相对导入 (例如 from .config import ...)
# ----------------------------------------------------------------
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    # 尝试作为 bot 包导入
    # 假设当前文件夹名为 'bot'
    # 先尝试直接导入，如果文件夹名不是 bot，则下面会进入异常处理
    from bot.main import PoetryPlugin
except ImportError as e:
    # 如果错误是因为找不到 'bot' 模块，或者 'bot.main'
    if "No module named 'bot'" in str(e) or "No module named 'bot.main'" in str(e):
        print(f"⚠️  未找到名为 'bot' 的包，正在尝试使用当前目录名 '{current_dir.name}' ...")
        
        # 尝试动态导入，使用文件夹名作为包名
        try:
            import importlib
            # 确保父目录在 sys.path 中
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))
                
            bot_module = importlib.import_module(f"{current_dir.name}.main")
            PoetryPlugin = bot_module.PoetryPlugin
        except ImportError as e2:
            print(f"❌ 启动失败。请确保文件夹名是有效的 Python 包名 (例如 'bot')。\n错误详情: {e2}")
            # 如果还是失败，可能是依赖缺失而不是包名问题
            if "ncatbot" in str(e2):
                 print("\n💡 提示: 似乎缺少 'ncatbot' 依赖，请运行 'pip install ncatbot aiohttp'")
            exit(1)
    else:
        # 如果是其他导入错误（例如缺少 ncatbot 依赖），直接抛出，不进行 fallback
        print(f"❌ 依赖缺失或代码错误: {e}")
        print("💡 提示: 请确保已安装依赖: pip install ncatbot aiohttp")
        exit(1)

from ncatbot.core import Bot

# 创建机器人实例
# config_path: 指向当前目录下的 config.yaml
bot = Bot(config_path=str(current_dir / "config.yaml"))

# 注册插件
bot.register_plugin(PoetryPlugin)

if __name__ == "__main__":
    print(f"🚀 正在启动机器人...")
    print(f"📂 配置文件: {current_dir / 'config.yaml'}")
    bot.run()
