from pathlib import Path
import atexit
import builtins
import ctypes
import subprocess
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


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _as_bool(value, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _first_non_empty_str(*values) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def parse_runtime_settings(runtime_config: dict) -> dict:
    napcat_config = _as_dict(runtime_config.get("napcat"))
    ws_uri = _first_non_empty_str(runtime_config.get("ws_uri"), napcat_config.get("ws_uri"))
    ws_token = _first_non_empty_str(
        runtime_config.get("ws_token"),
        runtime_config.get("access_token"),
        napcat_config.get("ws_token"),
    )

    return {
        "napcat_config": napcat_config,
        "ws_uri": ws_uri,
        "ws_token": ws_token,
        "bt_uin": runtime_config.get("bt_uin"),
        "enable_webui_interaction": _as_bool(runtime_config.get("enable_webui_interaction"), default=False),
    }


def apply_ncatbot_runtime_config(plugins_dir: Path, plugin_name: str, ws_uri: str, ws_token: str, napcat_config: dict) -> None:
    ncatbot_config.update_value("debug", False)
    ncatbot_config.plugin.update_value("plugins_dir", str(plugins_dir))
    ncatbot_config.plugin.update_value("plugin_whitelist", [plugin_name])
    ncatbot_config.plugin.update_value("plugin_blacklist", [])
    ncatbot_config.plugin.update_value("skip_plugin_load", False)

    if not hasattr(ncatbot_config, "napcat"):
        return

    ncatbot_config.napcat.update_value("ws_uri", ws_uri)
    ncatbot_config.napcat.update_value("ws_token", ws_token)

    ws_listen_ip = _first_non_empty_str(napcat_config.get("ws_listen_ip"))
    if ws_listen_ip:
        ncatbot_config.napcat.update_value("ws_listen_ip", ws_listen_ip)

    remote_mode = napcat_config.get("remote_mode")
    if isinstance(remote_mode, bool):
        ncatbot_config.napcat.update_value("remote_mode", remote_mode)


def prepare_plugin_runtime_dir(current_dir: Path, plugin_name: str) -> Path:
    runtime_root = current_dir.parent / ".ncatbot_plugins_runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    link_path = runtime_root / plugin_name

    if link_path.exists():
        return runtime_root

    cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(current_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("⚠️ 创建插件运行目录联接失败，将回退到默认插件目录。")
        if result.stderr:
            print(result.stderr.strip())
        return current_dir.parent

    return runtime_root


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
    plugin_name = current_dir.name
    config_path = current_dir / "config.yaml"
    plugins_dir = prepare_plugin_runtime_dir(current_dir, plugin_name)
    mutex_name = f"Local\\NcatBot_{str(current_dir).replace(':', '_').replace('\\', '_').replace('/', '_')}"
    instance_lock = SingleInstanceLock(mutex_name)

    if not instance_lock.acquire():
        print("⚠️ 已检测到机器人实例正在运行，本次启动已终止（避免重复回复）。")
        raise SystemExit(1)

    atexit.register(instance_lock.release)

    runtime_config = load_runtime_config(config_path)
    settings = parse_runtime_settings(runtime_config)
    napcat_config = settings["napcat_config"]
    ws_uri = settings["ws_uri"]
    ws_token = settings["ws_token"]
    bt_uin = settings["bt_uin"]
    enable_webui_interaction = settings["enable_webui_interaction"]

    if not ws_uri:
        print("❌ 配置缺失：config.yaml 需要提供 ws_uri")
        raise SystemExit(1)

    apply_ncatbot_runtime_config(
        plugins_dir=plugins_dir,
        plugin_name=plugin_name,
        ws_uri=ws_uri,
        ws_token=ws_token,
        napcat_config=napcat_config,
    )

    print("🚀 正在启动机器人...")
    print(f"📂 配置文件: {config_path}")
    print(f"📦 插件目录: {plugins_dir}")
    print(f"✅ 仅加载插件: {plugin_name}")
    print(f"🔌 WebSocket 地址: {ws_uri}")
    print(f"🔐 WebSocket 鉴权: {'已启用' if ws_token else '未启用'}")
    print(f"🧭 WebUI 交互授权: {'开启' if enable_webui_interaction else '关闭'}")
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
    run_kwargs["enable_webui_interaction"] = enable_webui_interaction

    original_input = builtins.input

    def non_interactive_input(prompt: str = "") -> str:
        prompt_text = str(prompt)
        if ("端口" in prompt_text and "强制覆盖" in prompt_text) or ("port" in prompt_text.lower() and "overwrite" in prompt_text.lower()):
            print("[AUTO] 检测到端口覆盖确认，自动选择: y")
            return "y"
        if ("安装" in prompt_text and "继续" in prompt_text) or ("install" in prompt_text.lower() and "continue" in prompt_text.lower()):
            print("[AUTO] 检测到安装确认，自动选择: n")
            return "n"
        if "y/n" in prompt_text.lower():
            print("[AUTO] 检测到通用确认提示，自动选择: n")
            return "n"
        return original_input(prompt)

    try:
        if not enable_webui_interaction:
            builtins.input = non_interactive_input
        bot.run(**run_kwargs)
    except NcatBotConnectionError as e:
        print(f"❌ 连接 NapCat 失败: {e}")
        print("\n请检查以下配置是否一致：")
        print("1) NapCat OneBot WebSocket 服务已开启")
        print("2) NapCat 的 WS 地址与本配置 ws_uri 完全一致（含端口）")
        print("3) 若 NapCat 开启了 WS Token，config.yaml 的 ws_token 也必须一致")
        print("4) 若 NapCat 未开启 WS Token，请确保 config.yaml 的 ws_token 为空")
        raise
    finally:
        builtins.input = original_input
