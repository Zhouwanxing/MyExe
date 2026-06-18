import uuid
from datetime import datetime

try:
    from macro_api import (
        MacroApiError,
        add_macro,
        delete_macro_by_id,
        find_list,
        update_macro,
    )
except ImportError:
    from MyExe.macro_api import (
        MacroApiError,
        add_macro,
        delete_macro_by_id,
        find_list,
        update_macro,
    )


def _normalize_item(item):
    data = dict(item)
    if "_id" in data and "id" not in data:
        data["id"] = data["_id"]
    elif "id" in data and "_id" not in data:
        data["_id"] = data["id"]
    return data


def _build_payload(macro):
    payload = {
        k: v for k, v in macro.items()
        if k not in ("_file",)
    }
    macro_id = payload.get("_id") or payload.get("id") or str(uuid.uuid4())
    payload["_id"] = macro_id
    payload.pop("id", None)
    return payload, macro_id


def list_macros():
    items = find_list()
    return [_normalize_item(item) for item in items]


def load_macro(macro_id):
    for macro in list_macros():
        if macro.get("id") == macro_id or macro.get("_id") == macro_id:
            return macro
    return None


def save_macro(macro, is_new=None):
    macro_id = macro.get("id") or macro.get("_id")
    if is_new is None:
        is_new = not macro_id or load_macro(macro_id) is None

    macro["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if is_new or "created_at" not in macro:
        macro["created_at"] = macro["updated_at"]

    payload, macro_id = _build_payload(macro)
    if is_new:
        add_macro(payload)
    else:
        update_macro(payload)

    macro["id"] = macro_id
    macro["_id"] = macro_id
    return macro


def delete_macro(macro_id):
    delete_macro_by_id(macro_id)
    return True
