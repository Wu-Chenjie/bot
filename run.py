from pathlib import Path
import atexit
import ctypes
import yaml

from ncatbot.core import BotClient
from ncatbot.utils import ncatbot_config
from ncatbot.utils.error import NcatBotConnectionError


KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
ERROR_ALREADY_EXISTS = 183
KERNEL32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
KERNEL32.CreateMutexW.restype = ctypes.c_void_p
KERNEL32.CloseHandle.argtypes = [ctypes.c_void_p]
KERNEL32.CloseHandle.restype = ctypes.c_bool


def load_runtime_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f) or {}
        return content if isinstance(content, dict) else {}


class SingleInstanceLock:
    def __init__(self, mutex_name: str):
        self.mutex_name = mutex_name
        self.handle = None

    def acquire(self) -> bool:
        ctypes.set_last_error(0)
        self.handle = KERNEL32.CreateMutexW(None, False, self.mutex_name)
        if not self.handle:
            return False
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            KERNEL32.CloseHandle(self.handle)
            self.handle = None
            return False
        return True

    def release(self):
        if not self.handle:
            return
        KERNEL32.CloseHandle(self.handle)
        self.handle = None


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    plugin_name = current_dir.name
    config_path = current_dir / "config.yaml"
    mutex_name = f"Local\\NcatBot_{str(current_dir).replace(':', '_').replace('\\', '_').replace('/', '_')}"
    instance_lock = SingleInstanceLock(mutex_name)

    if not instance_lock.acquire():
        print("⚠️ 已检测到机器人实例正在运行，本次启动已终止（避免重复回复）。")
        raise SystemExit(1)

    atexit.register(instance_lock.release)

    runtime_config = load_runtime_config(config_path)
    napcat_config = runtime_config.get("napcat") if isinstance(runtime_config.get("napcat"), dict) else {}

    ws_uri = (runtime_config.get("ws_uri") or napcat_config.get("ws_uri") or "").strip()
    ws_token = (
        runtime_config.get("ws_token")
        or runtime_config.get("access_token")
        or napcat_config.get("ws_token")
    )
    ws_token = (ws_token or "").strip()
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
    print(f"🔌 WebSocket 地址: {ws_uri}")
    print(f"🔐 WebSocket 鉴权: {'已启用' if ws_token else '未启用'}")
    if not bt_uin:
        print("⚠️ 未在 config.yaml 配置 bt_uin，启动时可能会要求手动输入 QQ 号")

    bot = BotClient()
    run_kwargs = {
        "ws_uri": ws_uri,
    }
    if ws_token:
        run_kwargs["ws_token"] = ws_token
    if bt_uin:
        run_kwargs["bt_uin"] = str(bt_uin)

    try:
        bot.run(**run_kwargs)
    except NcatBotConnectionError as e:
        print(f"❌ 连接 NapCat 失败: {e}")
        print("\n请检查以下配置是否一致：")
        print("1) NapCat OneBot WebSocket 服务已开启")
        print("2) NapCat 的 WS 地址与本配置 ws_uri 完全一致（含端口）")
        print("3) 若 NapCat 开启了 WS Token，config.yaml 的 ws_token 也必须一致")
        print("4) 若 NapCat 未开启 WS Token，请确保 config.yaml 的 ws_token 为空")
        raise
