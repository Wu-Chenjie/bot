from pathlib import Path
import yaml

from ncatbot.core import BotClient
from ncatbot.utils import ncatbot_config


def load_runtime_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f) or {}
        return content if isinstance(content, dict) else {}


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    plugin_name = current_dir.name
    config_path = current_dir / "config.yaml"

    runtime_config = load_runtime_config(config_path)
    napcat_config = runtime_config.get("napcat") if isinstance(runtime_config.get("napcat"), dict) else {}

    ws_uri = runtime_config.get("ws_uri") or napcat_config.get("ws_uri")
    ws_token = (
        runtime_config.get("ws_token")
        or runtime_config.get("access_token")
        or napcat_config.get("ws_token")
    )
    bt_uin = runtime_config.get("bt_uin")

    if not ws_uri:
        print("❌ 配置缺失：config.yaml 需要提供 ws_uri")
        raise SystemExit(1)

    ncatbot_config.plugin.update_value("plugins_dir", str(parent_dir))
    ncatbot_config.plugin.update_value("plugin_whitelist", [plugin_name])
    ncatbot_config.plugin.update_value("plugin_blacklist", [])
    ncatbot_config.plugin.update_value("skip_plugin_load", False)

    print("🚀 正在启动机器人...")
    print(f"📂 配置文件: {config_path}")
    print(f"📦 插件目录: {parent_dir}")
    print(f"✅ 仅加载插件: {plugin_name}")
    if not bt_uin:
        print("⚠️ 未在 config.yaml 配置 bt_uin，启动时可能会要求手动输入 QQ 号")

    bot = BotClient()
    run_kwargs = {
        "ws_uri": ws_uri,
        "ws_token": ws_token,
    }
    if bt_uin:
        run_kwargs["bt_uin"] = str(bt_uin)

    bot.run(**run_kwargs)
