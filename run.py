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
    from bot.main import PoetryPlugin
except ImportError as e:
    print("⚠️  导入失败，正在尝试兼容模式...")
    # 如果文件夹名不是 bot，可能会失败。
    # 这里是一个 fallback，如果用户改了文件夹名，可能需要手动调整代码中的相对导入
    try:
        # 下策：直接添加当前目录，但这可能导致 relative import 报错
        sys.path.insert(0, str(current_dir))
        from main import PoetryPlugin
    except ImportError as e2:
        print(f"❌ 启动失败。请确保文件夹名为 'bot'。\n错误详情: {e}")
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
