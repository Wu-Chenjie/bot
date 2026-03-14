import asyncio
import sys
import os
from pathlib import Path

# Adjust path to allow importing from current directory as a package
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
# Add parent dir to sys.path so we can import 'bot' as a package
# This is crucial for relative imports within the package to work (e.g., inside main.py)
if str(parent_dir) not in sys.path:
    # Use insert(0) to prioritize parent dir
    sys.path.insert(0, str(parent_dir))

print(f"DEBUG: current_dir={current_dir}")
print(f"DEBUG: parent_dir={parent_dir}")
# print(f"DEBUG: sys.path[0]={sys.path[0]}")

# Try to import
try:
    print("DEBUG: 尝试 'from bot.poetry_api import PoetryAPI'...")
    from bot.poetry_api import PoetryAPI
    print("DEBUG: 尝试 'from bot.main import PoetryPlugin'...")
    from bot.main import PoetryPlugin
    print("✅  模块导入成功 (作为 'bot' 包)")
except ImportError as e:
    print(f"DEBUG: Base import failed: {e}")
    # Handle folder name mismatch
    folder_name = current_dir.name
    if folder_name != "bot":
         try:
             print(f"DEBUG: 尝试 'from {folder_name}.main import ...' (文件夹名为: {folder_name})")
             # Dynamic import using importlib or exec
             import importlib
             api_mod = importlib.import_module(f"{folder_name}.poetry_api")
             main_mod = importlib.import_module(f"{folder_name}.main")
             PoetryAPI = api_mod.PoetryAPI
             PoetryPlugin = main_mod.PoetryPlugin
             print(f"✅  模块导入成功 (作为 '{folder_name}' 包)")
         except Exception as e2:
             print(f"DEBUG: 第二次导入失败: {e2}")
             print("❌ 无法导入模块。请确保在 'bot' 上一级目录运行，或者确认文件夹名。")
             sys.exit(1)
    else:
        # If folder is 'bot' and imports fail, it's likely dependency or path issue
        print("❌ 导入失败，尽管文件夹名为 'bot'。")
        sys.exit(1)

async def test_api():
    print("🔄 正在测试诗词 API 连接...")
    
    # Test 1: Random Poetry
    try:
        print("   测试 1: 获取随机诗词...")
        poetry = await PoetryAPI.get_random_poetry()
        if poetry:
            print(f"   ✅  成功获取随机诗词: {poetry[:20]}...")
        else:
            print("   ⚠️  获取随机诗词返回为空 (可能是网络问题)")
    except Exception as e:
        print(f"   ❌  随机诗词测试失败: {e}")

    # Test 2: Specific Type (Classic)
    try:
        print("   测试 2: 获取古诗词...")
        poetry = await PoetryAPI.get_poetry_by_type("classic")
        if poetry:
            print(f"   ✅  成功获取古诗词: {poetry[:20]}...")
        else:
            print("   ⚠️  获取古诗词返回为空")
    except Exception as e:
        print(f"   ❌  古诗词测试失败: {e}")

    # Test 3: Specific Type (Modern)
    try:
        print("   测试 3: 获取现代诗...")
        poetry = await PoetryAPI.get_poetry_by_type("modern")
        if poetry:
             print(f"   ✅  成功获取现代诗: {poetry[:20]}...")
        else:
             print("   ⚠️  获取现代诗返回为空")
    except Exception as e:
        print(f"   ❌  现代诗测试失败: {e}")

async def test_plugin_init():
    print("\n🔄 正在测试插件初始化...")
    try:
        # Mock bot instance
        class MockBot:
            pass
        class MockEventBus: # Mock dependencies
            pass
        
        # Pass mock event_bus to satisfy BasePlugin requirements
        plugin = PoetryPlugin(event_bus=MockEventBus())
        plugin.bot = MockBot()
        
        # Test schedule manager init
        if plugin.schedule_manager:
            print("✅  插件初始化成功")
            print(f"   插件名称: {plugin.name}")
            print(f"   插件版本: {plugin.version}")
        else:
            print("❌  插件初始化失败: ScheduleManager 未创建")
    except Exception as e:
        print(f"❌  插件初始化异常: {e}")

async def main():
    print("🚀 开始代码可用性自检...\n")
    await test_api()
    await test_plugin_init()
    print("\n🎉 自检完成")

if __name__ == "__main__":
    asyncio.run(main())
