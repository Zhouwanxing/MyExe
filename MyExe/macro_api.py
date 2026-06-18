import requests

try:
    from utils.config_loader import Config
except ImportError:
    from MyExe.utils.config_loader import Config


class MacroApiError(Exception):
    pass


BASE_URL = Config.get("server.baseUrl", "https://goldtask.onrender.com") + "/client/auto"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30


def _post(path, payload):
    try:
        resp = requests.post(BASE_URL + path, json=payload, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MacroApiError(f"网络请求失败: {e}") from e

    try:
        data = resp.json()
    except ValueError as e:
        raise MacroApiError(f"响应解析失败: {resp.text[:200]}") from e

    if not data.get("success"):
        raise MacroApiError(data.get("msg") or "服务端返回失败")
    return data


def find_list():
    data = _post("/findList", {})
    return data.get("list") or []


def add_macro(payload):
    return _post("/add", payload)


def update_macro(payload):
    return _post("/update", payload)


def delete_macro_by_id(macro_id):
    return _post("/delete", {"_id": macro_id})
