# ============================================================
# تطبيق POS - نقطة الدخول الرئيسية
# ============================================================
from app.factory import create_app
from app.extensions import db, bcrypt, login_manager

# تصدير العناصر الرئيسية للاستخدام في باقي أجزاء التطبيق
__all__ = ['create_app', 'db', 'bcrypt', 'login_manager']