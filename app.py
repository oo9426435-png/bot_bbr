import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'cyber_barber_secret_key_2026'

# إعداد قاعدة البيانات
db_path = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_path, 'cyber_barber.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------- نماذج قاعدة البيانات (Models) -----------------
class ActivationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Barber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    activation_code_id = db.Column(db.Integer, db.ForeignKey('activation_code.id'), nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'), nullable=False)
    client_name = db.Column(db.String(50), nullable=False)
    client_phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(100), nullable=False)
    appointment_time = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'), nullable=False)
    client_name = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------- التصاميم والصفحات (HTML Templates) -----------------
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة الحلاقة الذكية</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: Tahoma, sans-serif; }
        .navbar { background-color: #212529; }
        .navbar-brand, .nav-link { color: #fff !important; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg mb-4">
        <div class="container">
            <a class="navbar-brand" href="/">حلاقة برو</a>
            <div>
                <a class="btn btn-outline-light btn-sm" href="/admin_login">لوحة المشرف</a>
                <a class="btn btn-outline-warning btn-sm" href="/barber_login">دخول الحلاقين</a>
            </div>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

HOME_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<div class="row text-center">
    <div class="col-md-12">
        <h1 class="display-5 fw-bold">اختر الحلاق واحجز موعدك بكل سهولة</h1>
        <p class="lead text-muted">منصة متكاملة لإدارة مواعيد الحلاقة وتقييم الخدمات.</p>
        <hr class="my-4">
    </div>
</div>
<div class="row">
    {% for barber in barbers %}
    <div class="col-md-4 mb-3">
        <div class="card shadow-sm">
            <div class="card-body">
                <h5 class="card-title">{{ barber.first_name }} {{ barber.last_name }}</h5>
                <p class="card-text text-muted">📍 المكان: {{ barber.location }}</p>
                <p class="card-text">📞 الهاتف: {{ barber.phone }}</p>
                <a href="/book/{{ barber.id }}" class="btn btn-primary w-100 mb-2">حجز موعد</a>
                <a href="/barber/{{ barber.id }}" class="btn btn-outline-secondary w-100">عرض الملف والتقييمات</a>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}
"""

BOOK_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow">
            <div class="card-body">
                <h3>حجز موعد عند الحلاق: {{ barber.first_name }} {{ barber.last_name }}</h3>
                <form method="POST">
                    <div class="mb-3"><label>اسمك الكريم</label><input type="text" name="client_name" class="form-control" required></div>
                    <div class="mb-3"><label>رقم هاتفك</label><input type="text" name="client_phone" class="form-control" required></div>
                    <div class="mb-3"><label>نوع الخدمة</label><input type="text" name="service_type" class="form-control" placeholder="مثال: حلاقة شعر + لحية" required></div>
                    <div class="mb-3"><label>وقت الموعد المفضل</label><input type="text" name="appointment_time" class="form-control" placeholder="مثال: اليوم على الساعة 4 عصراً" required></div>
                    <button type="submit" class="btn btn-success w-100">إرسال طلب الحجز</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

BARBER_LOGIN_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow">
            <div class="card-body">
                <h3>تسجيل دخول الحلاقين</h3>
                <form method="POST">
                    <div class="mb-3"><label>اسم المستخدم</label><input type="text" name="username" class="form-control" required></div>
                    <div class="mb-3"><label>كلمة المرور</label><input type="password" name="password" class="form-control" required></div>
                    <button type="submit" class="btn btn-primary w-100">دخول</button>
                </form>
                <div class="mt-3 text-center"><a href="/barber_register">تسجيل حساب جديد بكود تفعيل</a></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

BARBER_REGISTER_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow">
            <div class="card-body">
                <h3>تسجيل حساب حلاق جديد (6 أشهر)</h3>
                <form method="POST">
                    <div class="mb-3"><label>اسم المستخدم</label><input type="text" name="username" class="form-control" required></div>
                    <div class="mb-3"><label>كلمة المرور</label><input type="password" name="password" class="form-control" required></div>
                    <div class="mb-3"><label>الاسم الأول</label><input type="text" name="first_name" class="form-control" required></div>
                    <div class="mb-3"><label>اسم اللقب</label><input type="text" name="last_name" class="form-control" required></div>
                    <div class="mb-3"><label>رقم الهاتف</label><input type="text" name="phone" class="form-control" required></div>
                    <div class="mb-3"><label>مكان المحل</label><input type="text" name="location" class="form-control" required></div>
                    <div class="mb-3"><label>كود التفعيل (أطلبه من المشرف)</label><input type="text" name="activation_code" class="form-control" required></div>
                    <button type="submit" class="btn btn-success w-100">تسجيل الحساب</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

BARBER_DASHBOARD_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<h2>لوحة تحكم الحلاق: {{ barber.first_name }}</h2>
<a href="/barber_logout" class="btn btn-danger btn-sm mb-3">تسجيل الخروج</a>
<hr>
<h4>طلبات المواعيد</h4>
<table class="table table-striped">
    <thead>
        <tr><th>الزبون</th><th>الهاتف</th><th>الخدمة</th><th>الوقت</th><th>الحالة</th><th>الإجراء</th></tr>
    </thead>
    <tbody>
        {% for appt in appointments %}
        <tr>
            <td>{{ appt.client_name }}</td>
            <td>{{ appt.client_phone }}</td>
            <td>{{ appt.service_type }}</td>
            <td>{{ appt.appointment_time }}</td>
            <td>{{ appt.status }}</td>
            <td>
                <a href="/appointment/accept/{{ appt.id }}" class="btn btn-success btn-sm">قبول</a>
                <a href="/appointment/reject/{{ appt.id }}" class="btn btn-danger btn-sm">رفض</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

ADMIN_LOGIN_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow">
            <div class="card-body">
                <h3>تسجيل دخول المشرف العام</h3>
                <form method="POST">
                    <div class="mb-3"><label>كلمة مرور المشرف</label><input type="password" name="password" class="form-control" required></div>
                    <button type="submit" class="btn btn-dark w-100">دخول الإدارة</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

ADMIN_DASHBOARD_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<h2>لوحة المشرف العام</h2>
<a href="/admin_logout" class="btn btn-danger btn-sm mb-3">خروج</a>
<hr>
<h4>توليد كود تفعيل جديد (صالحة لـ 6 أشهر)</h4>
<form method="POST" action="/admin/generate_code" class="mb-4">
    <button type="submit" class="btn btn-primary">توليد كود جديد</button>
</form>
<h4>أكواد التفعيل الموجودة</h4>
<ul class="list-group">
    {% for code in codes %}
    <li class="list-group-item d-flex justify-content-between align-items-center">
        {{ code.code }}
        <span>{% if code.is_used %}<span class="badge bg-danger">مستعمل</span>{% else %}<span class="badge bg-success">غير مستعمل</span>{% endif %}</span>
    </li>
    {% endfor %}
</ul>
{% endblock %}
"""

BARBER_PROFILE_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<div class="row">
    <div class="col-md-6">
        <h3>{{ barber.first_name }} {{ barber.last_name }}</h3>
        <p>📍 الموقع: {{ barber.location }}</p>
        <p>📞 الهاتف: {{ barber.phone }}</p>
        <a href="/book/{{ barber.id }}" class="btn btn-primary mb-3">احجز موعد الآن</a>
    </div>
    <div class="col-md-6">
        <h4>تقييمات الزبائن</h4>
        <form method="POST" action="/review/{{ barber.id }}" class="mb-4 card p-3">
            <h5>أضف تقييمك</h5>
            <div class="mb-2"><input type="text" name="client_name" class="form-control" placeholder="اسمك" required></div>
            <div class="mb-2">
                <select name="rating" class="form-control">
                    <option value="5">⭐⭐⭐⭐⭐ (5/5)</option>
                    <option value="4">⭐⭐⭐⭐ (4/5)</option>
                    <option value="3">⭐⭐⭐ (3/5)</option>
                    <option value="2">⭐⭐ (2/5)</option>
                    <option value="1">⭐ (1/5)</option>
                </select>
            </div>
            <div class="mb-2"><textarea name="comment" class="form-control" placeholder="تعليقك"></textarea></div>
            <button type="submit" class="btn btn-success btn-sm">إرسال التقييم</button>
        </form>
        {% for review in reviews %}
        <div class="card mb-2 p-2">
            <strong>{{ review.client_name }} ({{ review.rating }}/5)</strong>
            <p class="mb-0">{{ review.comment }}</p>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ----------------- المسارات (Routes) -----------------
@app.route('/')
def home():
    barbers = Barber.query.all()
    return render_template_string(HOME_TEMPLATE, barbers=barbers)

@app.route('/book/<int:barber_id>', methods=['GET', 'POST'])
def book(barber_id):
    barber = Barber.query.get_or_404(barber_id)
    if request.method == 'POST':
        client_name = request.form.get('client_name')
        client_phone = request.form.get('client_phone')
        service_type = request.form.get('service_type')
        appointment_time = request.form.get('appointment_time')
        appt = Appointment(barber_id=barber.id, client_name=client_name, client_phone=client_phone, service_type=service_type, appointment_time=appointment_time)
        db.session.add(appt)
        db.session.commit()
        flash('تم إرسال طلب الحجز بنجاح!', 'success')
        return redirect(url_for('home'))
    return render_template_string(BOOK_TEMPLATE, barber=barber)

@app.route('/barber/<int:barber_id>')
def barber_profile(barber_id):
    barber = Barber.query.get_or_404(barber_id)
    reviews = Review.query.filter_by(barber_id=barber.id).all()
    return render_template_string(BARBER_PROFILE_TEMPLATE, barber=barber, reviews=reviews)

@app.route('/review/<int:barber_id>', methods=['POST'])
def add_review(barber_id):
    client_name = request.form.get('client_name')
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    review = Review(barber_id=barber_id, client_name=client_name, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    flash('شكراً لك، تم إضافة تقييمك بنجاح!', 'success')
    return redirect(url_for('barber_profile', barber_id=barber_id))

@app.route('/barber_login', methods=['GET', 'POST'])
def barber_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        barber = Barber.query.filter_by(username=username, password=password).first()
        if barber:
            if datetime.utcnow() > barber.expiry_date:
                flash('انتهت صلاحية حسابك (6 أشهر)، يرجى تجديد الكود لدى الإدارة.', 'danger')
                return redirect(url_for('barber_login'))
            session['barber_id'] = barber.id
            return redirect(url_for('barber_dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template_string(BARBER_LOGIN_TEMPLATE)

@app.route('/barber_register', methods=['GET', 'POST'])
def barber_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        location = request.form.get('location')
        code_str = request.form.get('activation_code')
        
        code_obj = ActivationCode.query.filter_by(code=code_str, is_used=False).first()
        if not code_obj:
            flash('كود التفعيل غير صالح أو تم استخدامه مسبقاً!', 'danger')
            return redirect(url_for('barber_register'))
        
        expiry = datetime.utcnow() + timedelta(days=180)
        new_barber = Barber(username=username, password=password, first_name=first_name, last_name=last_name, phone=phone, location=location, activation_code_id=code_obj.id, expiry_date=expiry)
        code_obj.is_used = True
        
        db.session.add(new_barber)
        db.session.commit()
        flash('تم إنشاء الحساب بنجاح، يمكنك تسجيل الدخول الآن.', 'success')
        return redirect(url_for('barber_login'))
    return render_template_string(BARBER_REGISTER_TEMPLATE)

@app.route('/barber_dashboard')
def barber_dashboard():
    if 'barber_id' not in session:
        return redirect(url_for('barber_login'))
    barber = Barber.query.get(session['barber_id'])
    appointments = Appointment.query.filter_by(barber_id=barber.id).all()
    return render_template_string(BARBER_DASHBOARD_TEMPLATE, barber=barber, appointments=appointments)

@app.route('/barber_logout')
def barber_logout():
    session.pop('barber_id', None)
    return redirect(url_for('home'))

@app.route('/appointment/accept/<int:appt_id>')
def accept_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'مقبول'
    db.session.commit()
    return redirect(url_for('barber_dashboard'))

@app.route('/appointment/reject/<int:appt_id>')
def reject_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'مرفوض'
    db.session.commit()
    return redirect(url_for('barber_dashboard'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('كلمة مرور المشرف خاطئة', 'danger')
    return render_template_string(ADMIN_LOGIN_TEMPLATE)

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    codes = ActivationCode.query.all()
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, codes=codes)

@app.route('/admin/generate_code', methods=['POST'])
def generate_code():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    import uuid
    new_code = str(uuid.uuid4())[:8].upper()
    code_obj = ActivationCode(code=new_code)
    db.session.add(code_obj)
    db.session.commit()
    flash(f'تم توليد الكود بنجاح: {new_code}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))

# ----------------- إعادة ضبط قاعدة البيانات وإنشائها تلقائياً -----------------
if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  # حذف القديم الذي يسبب المشاكل
        db.create_all()  # إنشاء الجداول الجديدة بالشكل الصحيح
    app.run(host='0.0.0.0', port=5000)
