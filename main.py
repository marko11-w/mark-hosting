import json
from pathlib import Path
from typing import Dict, Any, List

# 🔹 ملفات البيانات
USERS_FILE = Path("users.json")
ORDERS_FILE = Path("orders.json")
CHANNELS_FILE = Path("channels.json")


# ====== دوال عامة ======
def _write_json(path: Path, content: Any):
    """كتابة محتوى JSON للملف بصيغة مرتبة."""
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path, default_content: Any) -> Any:
    """
    تحميل JSON من ملف:
    - إذا الملف غير موجود → ينشئه بالمحتوى الافتراضي.
    - إذا الملف موجود لكن فارغ → يرجع المحتوى الافتراضي ويكتبه.
    - إذا الملف يحتوي JSON معطوب → يعيد ضبطه بالمحتوى الافتراضي.
    """
    if not path.exists():
        _write_json(path, default_content)
        return default_content

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        # الملف فارغ
        _write_json(path, default_content)
        return default_content

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON معطوب → إعادة تهيئة
        _write_json(path, default_content)
        return default_content


# ====== المستخدمين ======
def load_users() -> Dict[str, Any]:
    """تحميل كل المستخدمين من users.json"""
    return _load_json(USERS_FILE, {})


def save_users(users: Dict[str, Any]):
    """حفظ قاموس المستخدمين في users.json"""
    _write_json(USERS_FILE, users)


def get_user(user_id: int, username: str = "") -> Dict[str, Any]:
    """
    إحضار بيانات المستخدم:
    - إذا غير موجود → يتم إنشاؤه بقيم افتراضية.
    - يتم تحديث اسم المستخدم إذا تغيّر.
    """
    users = load_users()
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "username": username,
            "points": 0,
            "joined_channels": [],
            "welcome_points_given": False,
        }
    else:
        # تحديث اسم المستخدم إذا تغيّر
        if username and users[uid].get("username") != username:
            users[uid]["username"] = username

    save_users(users)
    return users[uid]


def add_points(user_id: int, amount: int) -> int:
    """إضافة نقاط للمستخدم وإرجاع مجموع نقاطه بعد الإضافة."""
    users = load_users()
    uid = str(user_id)

    if uid not in users:
        # إنشاء المستخدم إن لم يكن موجودًا
        users[uid] = get_user(user_id)

    users[uid]["points"] = users[uid].get("points", 0) + amount
    save_users(users)
    return users[uid]["points"]


def set_points(user_id: int, amount: int) -> int:
    """تعيين عدد النقاط للمستخدم مباشرة وإرجاعها."""
    users = load_users()
    uid = str(user_id)

    if uid not in users:
        users[uid] = get_user(user_id)

    users[uid]["points"] = amount
    save_users(users)
    return users[uid]["points"]


def get_all_users() -> Dict[str, Any]:
    """إرجاع قاموس جميع المستخدمين كما هو."""
    return load_users()


# ====== الطلبات ======
def load_orders() -> Dict[str, Any]:
    """تحميل الطلبات من orders.json"""
    default = {"last_id": 0, "orders": {}}
    data = _load_json(ORDERS_FILE, default)

    # ضمان وجود المفاتيح الأساسية
    if "last_id" not in data:
        data["last_id"] = 0
    if "orders" not in data:
        data["orders"] = {}

    return data


def save_orders(data: Dict[str, Any]):
    """حفظ بيانات الطلبات في orders.json"""
    _write_json(ORDERS_FILE, data)


def create_order(user_id: int, service: str, target: str, quantity: int, cost: int) -> int:
    """
    إنشاء طلب جديد:
    - يزيد last_id
    - يخزن الطلب داخل data["orders"]
    - يرجع رقم الطلب الجديد
    """
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
    """إرجاع إحصائيات عامة عن المستخدمين والطلبات."""
    users = load_users()
    orders_data = load_orders()
    orders = list(orders_data.get("orders", {}).values())
    pending = [o for o in orders if o.get("status") == "pending"]

    return:
        {
        "users_count": len(users),
        "orders_count": len(orders),
    }


# ====== القنوات (لجمع النقاط) ======
def load_channels() -> List[Dict[str, Any]]:
    """
    تحميل القنوات من channels.json
    إذا لم يكن الملف موجودًا أو فارغًا، يتم إنشاؤه بمحتوى افتراضي.
    """
    default_channels = [
        {
            "id": -1001234567890,
            "title": "قناة مارك الرسمية",
            "reward": 10,
            "link": "https://t.me/YourChannelUsername",
        }
    ]
    data = _load_json(CHANNELS_FILE, default_channels)

    # ضمان أن البيانات قائمة (list)
    if not isinstance(data, list):
        data = default_channels
        _write_json(CHANNELS_FILE, data)

    return data


def has_channel_rewarded(user_id: int, channel_id: int) -> bool:
    """يتحقق هل المستخدم أخذ نقاط هذه القناة بالفعل أم لا."""
    u = get_user(user_id)
    return channel_id in u.get("joined_channels", [])


def get_stats() -> Dict[str, Any]:
    """إرجاع إحصائيات عامة عن المستخدمين والطلبات."""
    users = load_users()
    orders_data = load_orders()
    orders = list(orders_data.get("orders", {}).values())
    pending = [o for o in orders if o.get("status") == "pending"]

    return {
        "users_count": len(users),
        "orders_count": len(orders),
        "pending_orders": len(pending),
        "orders": orders,
    }
