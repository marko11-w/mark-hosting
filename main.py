import json
from pathlib import Path
from typing import Dict, Any, List

USERS_FILE = Path("users.json")
ORDERS_FILE = Path("orders.json")
CHANNELS_FILE = Path("channels.json")


def _ensure_file(path: Path, default_content: Any):
    if not path.exists():
        path.write_text(json.dumps(default_content, ensure_ascii=False, indent=2), encoding="utf-8")


def load_users() -> Dict[str, Any]:
    _ensure_file(USERS_FILE, {})
    data = USERS_FILE.read_text(encoding="utf-8")
    return json.loads(data) if data.strip() else {}


def save_users(d: Dict[str, Any]):
    USERS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user(user_id: int, username: str = "") -> Dict[str, Any]:
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "username": username,
            "points": 0,
            "joined_channels": [],  # قائمة قنوات حصل منها نقاط
            "welcome_points_given": False,
        }
        save_users(users)
    else:
        # تحديث اليوزر لو متغير
        if username and users[uid].get("username") != username:
            users[uid]["username"] = username
            save_users(users)
    return users[uid]


def add_points(user_id: int, amount: int) -> int:
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_user(user_id)
        users = load_users()
    users[uid]["points"] = users[uid].get("points", 0) + amount
    save_users(users)
    return users[uid]["points"]


def set_points(user_id: int, amount: int) -> int:
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_user(user_id)
        users = load_users()
    users[uid]["points"] = amount
    save_users(users)
    return users[uid]["points"]


def get_all_users() -> Dict[str, Any]:
    return load_users()


# ======= الطلبات =======

def load_orders() -> Dict[str, Any]:
    _ensure_file(ORDERS_FILE, {"last_id": 0, "orders": {}})
    data = ORDERS_FILE.read_text(encoding="utf-8")
    return json.loads(data)


def save_orders(d: Dict[str, Any]):
    ORDERS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def create_order(user_id: int, service: str, target: str, quantity: int, cost: int) -> int:
    data = load_orders()
    last_id = data.get("last_id", 0) + 1
    data["last_id"] = last_id
    data["orders"][str(last_id)] = {
        "id": last_id,
        "user_id": user_id,
        "service": service,
        "target": target,
        "quantity": quantity,
        "cost": cost,
        "status": "pending",
    }
    save_orders(data)
    return last_id


def get_stats() -> Dict[str, Any]:
    users = load_users()
    orders_data = load_orders()
    orders = list(orders_data["orders"].values())
    pending = [o for o in orders if o.get("status") == "pending"]
    return {
        "users_count": len(users),
        "orders_count": len(orders),
        "pending_orders": len(pending),
        "orders": orders,
    }


# ======= القنوات (جمع النقاط) =======

def load_channels() -> List[Dict[str, Any]]:
    # ملف مثال: قائمة قنوات
    _ensure_file(
        CHANNELS_FILE,
        [
            {
                "id": -1001234567890,
                "title": "قناة مارك الرسمية",
                "reward": 10,
                "link": "https://t.me/YourChannelUsername",
            }
        ],
    )
    data = CHANNELS_FILE.read_text(encoding="utf-8")
    return json.loads(data)


def has_channel_rewarded(user_id: int, channel_id: int) -> bool:
    u = get_user(user_id)
    return channel_id in u.get("joined_channels", [])


def mark_channel_rewarded(user_id: int, channel_id: int):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        get_user(user_id)
        users = load_users()
    jc = users[uid].get("joined_channels", [])
    if channel_id not in jc:
        jc.append(channel_id)
    users[uid]["joined_channels"] = jc
    save_users(users)
