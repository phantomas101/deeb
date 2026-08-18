from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.extensions import bcrypt
from app.models import Setting, Product, Supplier, Customer, Branch, User, Sale, SaleItem, Purchase, PurchaseItem, CashDrawer, StockMovement
from app.routes.auth import verify_license
import os
import sys
import tempfile
from werkzeug.utils import secure_filename
from datetime import datetime
import zipfile
import io
import shutil
import traceback

settings_bp = Blueprint('settings', __name__)

# ============================================================
# تحديد المسار الجذر للمشروع (وليس مجلد app)
# ============================================================
# __file__ = .../app/routes/settings.py
# نرفع 3 مستويات للوصول إلى جذر المشروع (حيث يوجد مجلد 'app')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===== المسارات المطلقة =====
INSTANCE_DIR = os.path.join(BASE_DIR, 'app', 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'pos.db')
STATIC_UPLOADS_DIR = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
LOGOS_DIR = os.path.join(STATIC_UPLOADS_DIR, 'logos')
BACKGROUNDS_DIR = os.path.join(STATIC_UPLOADS_DIR, 'backgrounds')

# ============================================================
# إعدادات رفع الملفات
# ============================================================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================
# 1. صفحة الإعدادات الرئيسية
# ============================================================
@settings_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))

    settings = {}
    all_settings = Setting.query.all()
    for setting in all_settings:
        settings[setting.key] = setting.value
    
    license_status, license_info = verify_license()
    
    return render_template('settings.html', settings=settings, license_status=license_status, license_info=license_info)

# ============================================================
# 2. تحديث الإعدادات
# ============================================================
@settings_bp.route('/update', methods=['POST'])
@login_required
def update():
    if current_user.role != 'admin':
        flash('غير مصرح.', 'danger')
        return redirect(url_for('settings.index'))

    current_settings = {}
    all_settings = Setting.query.all()
    for setting in all_settings:
        current_settings[setting.key] = setting.value

    site_name = request.form.get('site_name', current_settings.get('site_name', 'نظام POS المتكامل'))
    phone = request.form.get('phone', current_settings.get('phone', ''))
    address = request.form.get('address', current_settings.get('address', ''))
    primary_color = request.form.get('primary_color', current_settings.get('primary_color', '#0f172a'))
    secondary_color = request.form.get('secondary_color', current_settings.get('secondary_color', '#fbbf24'))
    font_family = request.form.get('font_family', current_settings.get('font_family', 'Cairo'))

    updates = {
        'site_name': site_name,
        'phone': phone,
        'address': address,
        'primary_color': primary_color,
        'secondary_color': secondary_color,
        'font_family': font_family
    }

    # ===== رفع الشعار (Logo) =====
    if 'logo' in request.files:
        logo = request.files['logo']
        if logo and allowed_file(logo.filename):
            # حذف الشعار القديم
            old_logo = Setting.query.filter_by(key='logo_path').first()
            if old_logo and old_logo.value:
                old_path = os.path.join(BASE_DIR, 'app', 'static', old_logo.value)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # حفظ الشعار الجديد
            ext = logo.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"logo_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            file_path = os.path.join(LOGOS_DIR, filename)
            os.makedirs(LOGOS_DIR, exist_ok=True)
            logo.save(file_path)
            updates['logo_path'] = f"uploads/logos/{filename}"
        else:
            updates['logo_path'] = current_settings.get('logo_path', '')

    # ===== رفع الخلفية (Background) =====
    if 'background' in request.files:
        background = request.files['background']
        if background and allowed_file(background.filename):
            # حذف الخلفية القديمة
            old_bg = Setting.query.filter_by(key='background_path').first()
            if old_bg and old_bg.value:
                old_path = os.path.join(BASE_DIR, 'app', 'static', old_bg.value)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # حفظ الخلفية الجديدة
            ext = background.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"bg_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
            file_path = os.path.join(BACKGROUNDS_DIR, filename)
            os.makedirs(BACKGROUNDS_DIR, exist_ok=True)
            background.save(file_path)
            updates['background_path'] = f"uploads/backgrounds/{filename}"
        else:
            updates['background_path'] = current_settings.get('background_path', '')

    # حفظ التحديثات في قاعدة البيانات
    for key, value in updates.items():
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            new_setting = Setting(key=key, value=value)
            db.session.add(new_setting)

    db.session.commit()
    flash('تم تحديث الإعدادات بنجاح!', 'success')
    return redirect(url_for('settings.index'))

# ============================================================
# 3. النسخ الاحتياطي
# ============================================================
@settings_bp.route('/backup')
@login_required
def backup():
    if current_user.role != 'admin':
        return jsonify({'error': 'غير مصرح'}), 403

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. إضافة قاعدة البيانات
        if os.path.exists(DB_PATH):
            zf.write(DB_PATH, 'pos.db')
        else:
            print(f"⚠️ قاعدة البيانات غير موجودة: {DB_PATH}")

        # 2. إضافة الملفات المرفوعة
        if os.path.exists(STATIC_UPLOADS_DIR):
            for root, dirs, files in os.walk(STATIC_UPLOADS_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('uploads', os.path.relpath(file_path, STATIC_UPLOADS_DIR))
                    zf.write(file_path, arcname)
        else:
            print(f"⚠️ مجلد المرفوعات غير موجود: {STATIC_UPLOADS_DIR}")

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
    )

# ============================================================
# 4. استعادة النسخة الاحتياطية
# ============================================================
@settings_bp.route('/restore', methods=['POST'])
@login_required
def restore():
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403

    if 'backup_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'لم يتم رفع أي ملف.'}), 400

    file = request.files['backup_file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'اسم الملف فارغ.'}), 400

    if not file.filename.endswith('.zip'):
        return jsonify({'status': 'error', 'message': 'يجب أن يكون الملف بصيغة ZIP.'}), 400

    try:
        # عمل نسخة احتياطية سريعة من قاعدة البيانات الحالية (للأمان)
        if os.path.exists(DB_PATH):
            backup_db = DB_PATH + '.restore_backup'
            shutil.copy2(DB_PATH, backup_db)

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'restore.zip')
            file.save(zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)

            # استعادة قاعدة البيانات
            extracted_db = os.path.join(temp_dir, 'pos.db')
            if os.path.exists(extracted_db):
                db.session.remove()
                db.engine.dispose()
                shutil.copy2(extracted_db, DB_PATH)

            # استعادة الملفات المرفوعة
            extracted_uploads = os.path.join(temp_dir, 'uploads')
            if os.path.exists(extracted_uploads):
                if os.path.exists(STATIC_UPLOADS_DIR):
                    shutil.rmtree(STATIC_UPLOADS_DIR)
                shutil.copytree(extracted_uploads, STATIC_UPLOADS_DIR)

        # حذف ملف النسخة الاحتياطية المؤقتة
        if os.path.exists(DB_PATH + '.restore_backup'):
            os.remove(DB_PATH + '.restore_backup')

        return jsonify({
            'status': 'success',
            'message': 'تمت استعادة النسخة الاحتياطية بنجاح!'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'فشلت الاستعادة: {str(e)}'}), 500

# ============================================================
# 5. إضافة البيانات التجريبية
# ============================================================
@settings_bp.route('/add-demo-data', methods=['POST'])
@login_required
def add_demo_data():
    # هذا الكود كما هو دون تغيير (أضعه للاكتمال، لكن يمكنك حذفه إذا أردت)
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403

    try:
        # نفس الكود السابق (أضعه مختصراً للاختصار)
        main_branch = Branch.query.filter_by(is_main=True).first()
        if not main_branch:
            main_branch = Branch(name="الفرع الرئيسي - المخزن", is_main=True)
            db.session.add(main_branch)
            db.session.commit()
        # ... باقي الكود (نفس الملف الأصلي)
        # (لن أكرره هنا للاختصار، يمكنك الاحتفاظ بالكود الأصلي)
        return jsonify({'status': 'success', 'message': 'تم إضافة البيانات التجريبية بنجاح!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500