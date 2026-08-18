# ============================================================
# تهيئة الملحقات (Extensions)
# ============================================================
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

# إنشاء كائنات الملحقات (سيتم تهيئتها في create_app)
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# إعدادات Login Manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'يرجى تسجيل الدخول أولاً'
login_manager.login_message_category = 'info'