# ============================================================
# دوال مساعدة عامة
# ============================================================
from flask import session
import secrets
from app.extensions import db, bcrypt
from app.models import Setting, User, Branch
from datetime import datetime
from sqlalchemy import inspect, text


def generate_csrf_token():
    """توليد توكن CSRF وحفظه في الجلسة"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def get_settings():
    """جلب جميع الإعدادات من قاعدة البيانات"""
    settings_dict = {}
    all_settings = Setting.query.all()
    for setting in all_settings:
        settings_dict[setting.key] = setting.value
    return settings_dict


# ============================================================
# دوال الإنشاء الافتراضي
# ============================================================
def create_default_admin():
    """إنشاء حساب أدمن افتراضي إذا لم يكن موجوداً"""
    if User.query.count() == 0:
        print("⚠️ لم يتم العثور على مستخدمين. جاري إنشاء حساب أدمن...")
        main_branch = Branch.query.filter_by(is_main=True).first()
        if not main_branch:
            main_branch = Branch(name="الفرع الرئيسي - المخزن", is_main=True)
            db.session.add(main_branch)
            db.session.commit()
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(username='admin', password=hashed_password, role='admin', branch_id=main_branch.id)
        db.session.add(admin)
        db.session.commit()
        print("✅ تم إنشاء حساب المدير: admin / admin123")


def create_default_branch():
    """إنشاء فرع رئيسي افتراضي إذا لم يكن موجوداً"""
    if Branch.query.count() == 0:
        print("⚠️ جاري إنشاء فرع رئيسي افتراضي...")
        main_branch = Branch(name="الفرع الرئيسي - المخزن", is_main=True)
        db.session.add(main_branch)
        db.session.commit()
        print("✅ تم إنشاء الفرع الرئيسي.")


def create_default_settings():
    """إنشاء إعدادات افتراضية إذا لم تكن موجودة"""
    defaults = {
        'site_name': 'نظام POS المتكامل',
        'logo_path': '',
        'primary_color': '#0f172a',
        'secondary_color': '#fbbf24',
        'font_family': 'Cairo',
        'background_path': '',
        'phone': '',
        'address': ''
    }
    for key, value in defaults.items():
        if not Setting.query.filter_by(key=key).first():
            setting = Setting(key=key, value=value)
            db.session.add(setting)
    db.session.commit()
    print("✅ تم إنشاء الإعدادات الافتراضية.")


def upgrade_database():
    """ترقية قاعدة البيانات (إضافة أعمدة جديدة إذا لزم الأمر)"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('stock_movement')]
        with db.engine.connect() as conn:
            if 'sale_id' not in columns:
                conn.execute(text("ALTER TABLE stock_movement ADD COLUMN sale_id INTEGER REFERENCES sale(id)"))
                conn.commit()
            if 'purchase_id' not in columns:
                conn.execute(text("ALTER TABLE stock_movement ADD COLUMN purchase_id INTEGER REFERENCES purchase(id)"))
                conn.commit()
        print("✅ تم تحديث هيكل قاعدة البيانات (إذا لزم الأمر).")
    except Exception as e:
        print(f"⚠️ لم يتم تحديث قاعدة البيانات: {e}")