import asyncio
import sys
from pathlib import Path
import importlib

# Adjust path to allow importing from current directory as a package
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

print(f"DEBUG: current_dir={current_dir}")
print(f"DEBUG: parent_dir={parent_dir}")


def import_plugin_modules():
    candidates = ["bot"]
    if current_dir.name != "bot":
        candidates.append(current_dir.name)

    for package_name in candidates:
        try:
            print(f"DEBUG: 尝试从包 '{package_name}' 导入模块...")
            api_mod = importlib.import_module(f"{package_name}.poetry_api")
            main_mod = importlib.import_module(f"{package_name}.main")
            print(f"✅  模块导入成功 (作为 '{package_name}' 包)")
            return api_mod.PoetryAPI, main_mod.PoetryPlugin
        except Exception as e:
            print(f"DEBUG: 从 '{package_name}' 导入失败: {e}")

    print("❌ 无法导入模块。请确保在 'bot' 上一级目录运行，或者确认文件夹名。")
    sys.exit(1)


PoetryAPI, PoetryPlugin = import_plugin_modules()

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

        class MockEventBus:
            pass

        plugin = PoetryPlugin(event_bus=MockEventBus())
        plugin.bot = MockBot()

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
