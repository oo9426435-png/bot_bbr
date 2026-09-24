from datetime import datetime, timedelta
import os
import random
import string
from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "cyber_barber_ultra_modern_secure_2026"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + os.path.join(basedir, "cyber_barber.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------- Models -----------------


class ActivationCode(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  code = db.Column(db.String(30), unique=True, nullable=False)
  is_used = db.Column(db.Boolean, default=False)
  activated_at = db.Column(db.DateTime, nullable=True)
  expires_at = db.Column(db.DateTime, nullable=True)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Barber(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  activation_code_id = db.Column(
      db.Integer, db.ForeignKey("activation_code.id"), nullable=True
  )
  first_name = db.Column(db.String(50), nullable=False)
  last_name = db.Column(db.String(50), nullable=False)
  username = db.Column(db.String(50), unique=True, nullable=False)
  phone = db.Column(db.String(20), nullable=False)
  location = db.Column(db.String(150), nullable=False)
  password = db.Column(db.String(100), nullable=False)

  activation_code = db.relationship(
      "ActivationCode", backref=db.backref("barber", uselist=False)
  )


class Service(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  barber_id = db.Column(
      db.Integer, db.ForeignKey("barber.id"), nullable=False
  )
  name = db.Column(db.String(100), nullable=False)
  price = db.Column(db.Float, nullable=False)
  duration = db.Column(db.Integer, nullable=False)
  barber = db.relationship(
      "Barber", backref=db.backref("services", lazy=True)
  )


class Appointment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  barber_id = db.Column(
      db.Integer, db.ForeignKey("barber.id"), nullable=False
  )
  customer_name = db.Column(db.String(100), nullable=False)
  phone = db.Column(db.String(20), nullable=False)
  service_id = db.Column(
      db.Integer, db.ForeignKey("service.id"), nullable=False
  )
  date_time = db.Column(db.String(50), nullable=False)
  status = db.Column(db.String(20), default="قيد الانتظار")
  updated_at = db.Column(
      db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
  )
  service = db.relationship("Service", backref=db.backref("appointments", lazy=True))
  barber = db.relationship(
      "Barber", backref=db.backref("appointments", lazy=True)
  )


class Review(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  barber_id = db.Column(
      db.Integer, db.ForeignKey("barber.id"), nullable=False
  )
  client_name = db.Column(db.String(100), nullable=False)
  rating = db.Column(db.Integer, nullable=False)
  comment = db.Column(db.Text, nullable=True)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  barber = db.relationship("Barber", backref=db.backref("reviews", lazy=True))


# ----------------- Cyber UI Templates -----------------

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة النخبة - حجز الحلاقة الذكي</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

        :root {
            --primary: #f59e0b;
            --primary-hover: #d97706;
            --bg-main: #0b0f19;
            --card-bg: #131c2e;
            --input-bg: #1a263d;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --border-color: #2a3b5e;
            --danger: #f43f5e;
            --success: #10b981;
            --radius: 16px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }

        body {
            background-color: var(--bg-main);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(19, 28, 46, 0.98);
            border-bottom: 1px solid var(--border-color);
            padding: 0.8rem 1.2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .nav-container {
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 1.3rem;
            font-weight: 900;
            color: #fff;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .logo span { color: var(--primary); }

        .admin-link {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-decoration: none;
            padding: 5px 10px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            transition: 0.2s;
        }
        .admin-link:hover { color: var(--primary); border-color: var(--primary); }

        .modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(5px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            padding: 20px;
        }
        .modal-box {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            width: 100%;
            max-width: 380px;
            padding: 25px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
            text-align: center;
            animation: modalPop 0.3s ease;
        }
        @keyframes modalPop {
            0% { transform: scale(0.9); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
        .modal-title { font-size: 1.25rem; font-weight: 800; margin-bottom: 8px; color: #fff; }
        .modal-desc { font-size: 0.88rem; color: var(--text-muted); margin-bottom: 20px; }
        .modal-btn {
            display: block;
            width: 100%;
            padding: 12px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 12px;
            transition: 0.2s;
        }
        .modal-btn-primary {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #0b0f19;
            box-shadow: 0 4px 15px rgba(245,158,11,0.3);
        }
        .modal-btn-outline {
            background: var(--input-bg);
            color: var(--text-main);
            border: 1px solid var(--border-color);
        }
        .modal-btn-outline:hover { border-color: var(--primary); color: var(--primary); }
        .modal-close {
            background: transparent; border: none; color: var(--text-muted);
            font-size: 0.88rem; cursor: pointer; margin-top: 5px;
        }

        .container {
            max-width: 900px;
            width: 94%;
            margin: 25px auto;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 20px;
            border-radius: var(--radius);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            flex: 1;
        }

        @media (min-width: 768px) {
            .container { padding: 30px; margin: 35px auto; }
        }

        h3 { font-size: 1.35rem; font-weight: 800; color: var(--text-main); margin-bottom: 20px; }

        .barbers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 18px;
            margin-top: 15px;
        }

        .barber-card {
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 15px;
            transition: all 0.3s ease;
        }
        .barber-card:hover { border-color: var(--primary); transform: translateY(-2px); }

        .form-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 7px; font-weight: 600; color: var(--text-muted); font-size: 0.88rem; }
        input, select, textarea {
            width: 100%;
            padding: 12px 15px;
            background: var(--input-bg);
            border: 2px solid var(--border-color);
            border-radius: 12px;
            font-size: 0.95rem;
            color: var(--text-main);
            outline: none;
            transition: all 0.3s ease;
        }
        input:focus, select:focus, textarea:focus { border-color: var(--primary); background: #1e293b; }

        .btn {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #0b0f19;
            border: none;
            padding: 13px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 800;
            width: 100%;
            text-align: center;
            text-decoration: none;
            display: block;
            box-shadow: 0 8px 18px -4px rgba(245, 158, 11, 0.4);
        }

        .table-responsive {
            overflow-x: auto;
            margin-top: 20px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            background: var(--input-bg);
        }
        table { width: 100%; border-collapse: collapse; text-align: right; min-width: 500px; }
        th, td { padding: 12px 15px; border-bottom: 1px solid var(--border-color); font-size: 0.9rem; }
        th { background: rgba(11, 15, 25, 0.6); color: var(--text-muted); }

        .alert {
            padding: 14px 18px;
            background: rgba(244, 63, 94, 0.15);
            color: #fb7185;
            margin-bottom: 20px;
            border-radius: 12px;
            font-weight: 600;
            border: 1px solid rgba(244, 63, 94, 0.3);
        }
        .success { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
        .badge { background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; }
        .badge-success { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge-danger { background: rgba(244, 63, 94, 0.15); color: #fb7185; }

        footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--border-color);
            margin-top: auto;
        }
    </style>
</head>
<body>
    <header>
        <div class="nav-container">
            <a href="{{ url_for('index') }}" class="logo">⚡ Prime<span>Cut</span></a>
            <a href="{{ url_for('admin_login') }}" class="admin-link">👑 لوحة المالك</a>
        </div>
    </header>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>

    <div id="barberModal" class="modal-overlay">
        <div class="modal-box">
            <div class="modal-title">🔐 بوابة الحلاقين</div>
            <div class="modal-desc">اختر العملية المطلوبة للمتابعة:</div>
            
            <a href="{{ url_for('barber_login') }}" class="modal-btn modal-btn-primary">🔑 تسجيل دخول حلاق مسجل</a>
            <a href="{{ url_for('barber_register') }}" class="modal-btn modal-btn-outline">✨ تسجيل حساب جديد (برمز التفعيل)</a>
            
            <button onclick="toggleBarberModal()" class="modal-close">إلغاء</button>
        </div>
    </div>

    <script>
        function toggleBarberModal() {
            const modal = document.getElementById('barberModal');
            modal.style.display = (modal.style.display === 'flex') ? 'none' : 'flex';
        }
    </script>

    <footer>
        جميع الحقوق محفوظة &copy; 2026 - نظام حجز صالونات الحلاقة الذكي
    </footer>
</body>
</html>
"""

INDEX_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;">
        <button onclick="toggleBarberModal()" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #0b0f19; border: none; padding: 16px; border-radius: 14px; font-weight: 800; font-size: 1rem; cursor: pointer; box-shadow: 0 6px 20px rgba(245,158,11,0.3); text-align: center;">
            ✂️ تسجيل / دخول حلاق
        </button>
        
        <a href="#salons-section" style="background: var(--input-bg); color: var(--text-main); border: 2px solid var(--border-color); padding: 16px; border-radius: 14px; font-weight: 800; font-size: 1rem; text-decoration: none; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px;">
            👤 تصفح الصالونات <span style="font-size: 0.8rem; color: var(--primary);">(اختر واجز)</span>
        </a>
    </div>

    <div id="salons-section">
        <h3>💈 صالونات الحلاقة المتاحة للحجز والتقييمات</h3>
        <p style="color: var(--text-muted); margin-bottom: 20px; font-size: 0.9rem;">اختر الحلاق المناسب لعرض خدماته، تقييمات الزبائن، وحجز موعدك:</p>
        
        <div class="barbers-grid">
            {% for item in active_barbers %}
            <div class="barber-card">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <h4 style="font-size: 1.15rem; color: var(--text-main);">✨ {{ item.barber.username }}</h4>
                        <span style="color: #f59e0b; font-weight: bold; font-size: 0.9rem;">★ {{ item.avg_rating }} <span style="color: var(--text-muted); font-size: 0.75rem;">({{ item.total_reviews }})</span></span>
                    </div>
                    <p style="margin-top: 8px; font-size: 0.88rem; color: var(--text-muted);">👤 <b>الحلاق:</b> {{ item.barber.first_name }} {{ item.barber.last_name }}</p>
                    <p style="margin-top: 4px; font-size: 0.88rem; color: var(--text-muted);">📍 <b>الموقع:</b> {{ item.barber.location }}</p>
                    <p style="margin-top: 4px; font-size: 0.88rem; color: var(--text-muted);">📞 <b>الهاتف:</b> {{ item.barber.phone }}</p>
                </div>
                <a href="{{ url_for('barber_profile', barber_id=item.barber.id) }}" class="btn">عرض الخدمات والتقييمات 🚀</a>
            </div>
            {% else %}
            <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 40px;">
                لا توجد صالونات حلاقة نشطة حالياً.
            </div>
            {% endfor %}
        </div>
    </div>
""",
)

BARBER_PROFILE_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <a href="{{ url_for('index') }}" style="color: var(--primary); text-decoration: none; font-weight: 700; display: inline-block; margin-bottom: 15px; font-size: 0.9rem;">← العودة للقائمة</a>
    
    <div style="background: rgba(11, 15, 25, 0.4); padding: 20px; border-radius: 14px; border: 1px solid var(--border-color); margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 15px;">
        <div>
            <h3 style="margin-bottom: 10px; color: var(--primary);">💈 {{ barber.username }}</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 4px;">📍 <b>المكان:</b> {{ barber.location }}</p>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 4px;">👤 <b>المشرف:</b> {{ barber.first_name }} {{ barber.last_name }}</p>
            <p style="color: var(--text-muted); font-size: 0.9rem;">📞 <b>الهاتف:</b> {{ barber.phone }}</p>
        </div>
        <div style="background: var(--input-bg); padding: 12px 20px; border-radius: 12px; border: 1px solid var(--border-color); text-align: center;">
            <div style="font-size: 1.5rem; color: #f59e0b; font-weight: bold;">★ {{ avg_rating }}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">({{ total_reviews }} تقييم إجمالي)</div>
        </div>
    </div>

    <h4 style="margin-bottom: 15px; font-size: 1.15rem; color: var(--text-main);">الخدمات المتاحة والأسعار</h4>
    <div class="table-responsive" style="margin-bottom: 25px;">
        <table>
            <thead>
                <tr>
                    <th>الخدمة</th>
                    <th>السعر</th>
                    <th>المدة</th>
                </tr>
            </thead>
            <tbody>
                {% for s in services %}
                <tr>
                    <td><b>{{ s.name }}</b></td>
                    <td><span class="badge">{{ s.price }} دج</span></td>
                    <td>⏱️ {{ s.duration }} دقيقة</td>
                </tr>
                {% else %}
                <tr><td colspan="3" style="text-align: center; color: var(--text-muted);">لا توجد خدمات مضافة حالياً.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {% if services %}
    <form method="POST" action="{{ url_for('book_appointment', barber_id=barber.id) }}" style="background: rgba(11, 15, 25, 0.4); padding: 20px; border-radius: 14px; border: 1px solid var(--border-color); margin-bottom: 30px;">
        <h4 style="margin-bottom: 15px; color: var(--text-main); font-size: 1.1rem;">📅 حجز موعد جديد</h4>
        
        <div class="form-group">
            <label>الاسم الكامل:</label>
            <input type="text" name="customer_name" placeholder="أدخل اسمك هنا..." required>
        </div>
        <div class="form-group">
            <label>رقم الهاتف:</label>
            <input type="text" name="phone" placeholder="06XXXXXXXX" required>
        </div>
        <div class="form-group">
            <label>اختر الخدمة:</label>
            <select name="service_id" required>
                <option value="">-- اختر الخدمة --</option>
                {% for s in services %}
                <option value="{{ s.id }}">{{ s.name }} — ({{ s.price }} دج / ⏱️ {{ s.duration }} دقيقة)</option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group">
            <label>تاريخ ووقت الموعد:</label>
            <input type="datetime-local" name="date_time" required>
        </div>
        <button type="submit" class="btn">تأكيد حجز الموعد الآن 🚀</button>
    </form>
    {% endif %}

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;" class="reviews-section-grid">
        <form method="POST" action="{{ url_for('add_review', barber_id=barber.id) }}" style="background: rgba(11, 15, 25, 0.4); padding: 20px; border-radius: 14px; border: 1px solid var(--border-color);">
            <h4 style="margin-bottom: 15px; color: var(--text-main); font-size: 1.1rem;">⭐ أضف تقييمك للحلاق</h4>
            <div class="form-group">
                <label>اسمك:</label>
                <input type="text" name="client_name" placeholder="اسمك الكريم..." required>
            </div>
            <div class="form-group">
                <label>التقييم:</label>
                <select name="rating" required>
                    <option value="5">★★★★★ (5 - ممتاز)</option>
                    <option value="4">★★★★☆ (4 - جيد جداً)</option>
                    <option value="3">★★★☆☆ (3 - متوسط)</option>
                    <option value="2">★★☆☆☆ (2 - سيء)</option>
                    <option value="1">★☆☆☆☆ (1 - سيء جداً)</option>
                </select>
            </div>
            <div class="form-group">
                <label>التعليق:</label>
                <textarea name="comment" rows="2" placeholder="اكتب رأيك في جودة الخدمة والمكان..."></textarea>
            </div>
            <button type="submit" class="btn" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff;">إرسال التقييم 🌟</button>
        </form>

        <div>
            <h4 style="margin-bottom: 15px; font-size: 1.1rem; color: var(--text-main);">💬 آراء الزبائن والتقييمات</h4>
            <div style="display: flex; flex-direction: column; gap: 10px; max-height: 400px; overflow-y: auto;">
                {% for rev in reviews %}
                <div style="background: var(--input-bg); padding: 14px; border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <b style="font-size: 0.9rem;">{{ rev.client_name }}</b>
                        <span style="color: #f59e0b; font-size: 0.85rem; font-weight: bold;">
                            {% for i in range(rev.rating) %}★{% endfor %}
                        </span>
                    </div>
                    {% if rev.comment %}
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px;">{{ rev.comment }}</p>
                    {% endif %}
                    <div style="font-size: 0.72rem; color: var(--text-muted); text-align: left;">{{ rev.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                </div>
                {% else %}
                <div style="text-align: center; color: var(--text-muted); padding: 30px; background: var(--input-bg); border-radius: 12px; border: 1px solid var(--border-color);">
                    لا توجد تقييمات لهذا الحلاق حتى الآن. كن أول من يقيّمه!
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
""",
)

REGISTER_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <a href="{{ url_for('index') }}" style="color: var(--primary); text-decoration: none; font-weight: 700; display: inline-block; margin-bottom: 15px; font-size: 0.9rem;">← العودة للرئيسية</a>
    <h3>📝 تسجيل حساب حلاق جديد</h3>
    <p style="color: var(--text-muted); margin-bottom: 20px; font-size: 0.88rem;">ملاحظة: كود التفعيل صالح لمدة <b>6 أشهر</b> من تاريخ التسجيل.</p>
    <form method="POST">
        <div class="form-group">
            <label>كود التفعيل (من الإدارة):</label>
            <input type="text" name="activation_code" placeholder="أدخل كود التفعيل هنا..." required style="border-color: var(--primary);">
        </div>
        <div class="form-group">
            <label>الاسم الحقيقي:</label>
            <input type="text" name="first_name" placeholder="الاسم" required>
        </div>
        <div class="form-group">
            <label>اللقب:</label>
            <input type="text" name="last_name" placeholder="اللقب" required>
        </div>
        <div class="form-group">
            <label>اسم المحل / الشهرة:</label>
            <input type="text" name="username" placeholder="مثال: صالون الأسطورة" required>
        </div>
        <div class="form-group">
            <label>رقم الهاتف الشخصي:</label>
            <input type="text" name="phone" placeholder="رقم الهاتف" required>
        </div>
        <div class="form-group">
            <label>مكان العمل (المدينة، الحي):</label>
            <input type="text" name="location" placeholder="العنوان بالتفصيل" required>
        </div>
        <div class="form-group">
            <label>كلمة المرور:</label>
            <input type="password" name="password" placeholder="••••••••" required>
        </div>
        <button type="submit" class="btn">تفعيل الحساب والبدء فورا 💼</button>
    </form>
""",
)

LOGIN_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <a href="{{ url_for('index') }}" style="color: var(--primary); text-decoration: none; font-weight: 700; display: inline-block; margin-bottom: 15px; font-size: 0.9rem;">← العودة للرئيسية</a>
    <h3>🔐 دخول لوحة تحكم الحلاقين</h3>
    <form method="POST">
        <div class="form-group">
            <label>اسم المحل / الشهرة:</label>
            <input type="text" name="username" placeholder="ادخل اسمك المستعار" required>
        </div>
        <div class="form-group">
            <label>كلمة المرور:</label>
            <input type="password" name="password" placeholder="••••••••" required>
        </div>
        <button type="submit" class="btn">تسجيل الدخول 🔓</button>
    </form>
""",
)

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; gap: 15px;">
        <div>
            <h3 style="margin: 0;">✨ أهلاً بك، {{ barber.username }}</h3>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-top: 4px;">📍 الموقع: {{ barber.location }}</p>
            {% if barber.activation_code %}
            <p style="color: var(--success); font-size: 0.82rem; margin-top: 2px;">⏳ الاشتراك ينتهي في: {{ barber.activation_code.expires_at.strftime('%Y-%m-%d') }}</p>
            {% endif %}
        </div>
        <a href="{{ url_for('logout') }}" style="background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); padding: 8px 14px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 0.85rem;">تسجيل الخروج 🚪</a>
    </div>

    <h4 style="margin-top: 25px; font-size: 1.15rem; color: var(--text-main);">إدارة الخدمات والأسعار</h4>
    <form action="{{ url_for('add_service') }}" method="POST" style="background: rgba(11, 15, 25, 0.4); padding: 18px; border-radius: 12px; border: 1px solid var(--border-color); margin-top: 10px;">
        <div class="form-group">
            <label>اسم الخدمة:</label>
            <input type="text" name="name" placeholder="مثال: حلاقة عصرية" required>
        </div>
        <div class="form-group">
            <label>السعر (دج):</label>
            <input type="number" step="0.01" name="price" placeholder="500" required>
        </div>
        <div class="form-group">
            <label>المدة (دقيقة):</label>
            <input type="number" name="duration" placeholder="20" required>
        </div>
        <button type="submit" class="btn">إضافة الخدمة ➕</button>
    </form>

    <div class="table-responsive">
        <table>
            <thead>
                <tr>
                    <th>الخدمة</th>
                    <th>السعر</th>
                    <th>المدة</th>
                    <th>إجراء</th>
                </tr>
            </thead>
            <tbody>
                {% for s in services %}
                <tr>
                    <td><b>{{ s.name }}</b></td>
                    <td><span class="badge">{{ s.price }} دج</span></td>
                    <td>⏱️ {{ s.duration }} دقيقة</td>
                    <td><a href="{{ url_for('delete_service', id=s.id) }}" style="color: #fb7185; text-decoration: none; font-weight: bold;">حذف 🗑️</a></td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">لا توجد خدمات مضافة.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <h4 style="margin-top: 35px; font-size: 1.15rem; color: var(--text-main);">طلبات الحجز الواردة</h4>
    <div class="table-responsive">
        <table>
            <thead>
                <tr>
                    <th>الزبون</th>
                    <th>الهاتف</th>
                    <th>الخدمة</th>
                    <th>الموعد</th>
                    <th>الحالة</th>
                    <th>الإجراءات</th>
                </tr>
            </thead>
            <tbody>
                {% for app in appointments %}
                <tr>
                    <td><b>{{ app.customer_name }}</b></td>
                    <td>{{ app.phone }}</td>
                    <td>{{ app.service.name }}</td>
                    <td>{{ app.date_time }}</td>
                    <td>
                        {% if app.status == 'مؤكد' %}
                            <span class="badge badge-success">مؤكد</span>
                        {% elif app.status == 'ملغي' %}
                            <span class="badge badge-danger">ملغي</span>
                        {% else %}
                            <span class="badge" style="background:rgba(245, 158, 11, 0.15); color:#f59e0b;">قيد الانتظار</span>
                        {% endif %}
                    </td>
                    <td>
                        <a href="{{ url_for('update_status', id=app.id, status='مؤكد') }}" style="color: #34d399; text-decoration: none; font-weight: bold;">تأكيد</a> | 
                        <a href="{{ url_for('update_status', id=app.id, status='ملغي') }}" style="color: #fb7185; text-decoration: none; font-weight: bold;">إلغاء</a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">لا توجد مواعيد جديدة.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
""",
)

ADMIN_LOGIN_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <a href="{{ url_for('index') }}" style="color: var(--primary); text-decoration: none; font-weight: 700; display: inline-block; margin-bottom: 15px; font-size: 0.9rem;">← العودة للرئيسية</a>
    <h3>👑 تسجيل دخول مالك المنصة</h3>
    <form method="POST">
        <div class="form-group">
            <label>كلمة مرور المالك:</label>
            <input type="password" name="admin_password" placeholder="أدخل كلمة المرور السرية..." required>
        </div>
        <button type="submit" class="btn">دخول لوحة التحكم 🚀</button>
    </form>
""",
)

ADMIN_DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace(
    "{% block content %}{% endblock %}",
    """
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
        <h3>👑 لوحة تحكم المالك</h3>
        <a href="{{ url_for('admin_logout') }}" style="background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); padding: 8px 14px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 0.85rem;">تسجيل الخروج 🚪</a>
    </div>

    <form action="{{ url_for('generate_code') }}" method="POST" style="background: rgba(11, 15, 25, 0.4); padding: 18px; border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 25px;">
        <button type="submit" class="btn">➕ توليد كود تفعيل جديد (صالح لـ 6 أشهر)</button>
    </form>

    <h4 style="margin-bottom: 15px; font-size: 1.15rem;">📊 إحصائيات الزبائن المقبولين يومياً حسب الصالون</h4>
    <div class="table-responsive" style="margin-bottom: 30px;">
        <table>
            <thead>
                <tr>
                    <th>اسم الصالون / الحلاق</th>
                    <th>التاريخ (اليوم)</th>
                    <th>عدد الزبائن المقبولين</th>
                </tr>
            </thead>
            <tbody>
                {% for stat in daily_stats %}
                <tr>
                    <td><b>{{ stat.barber_name }}</b></td>
                    <td>{{ stat.day }}</td>
                    <td><span class="badge badge-success">{{ stat.count }} زبون</span></td>
                </tr>
                {% else %}
                <tr><td colspan="3" style="text-align: center; color: var(--text-muted);">لا توجد حجوزات مؤكدة حتى الآن.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <h4 style="margin-bottom: 15px; font-size: 1.15rem;">قائمة الأكواد وحالة الاشتراكات</h4>
    <div class="table-responsive">
        <table>
            <thead>
                <tr>
                    <th>كود التفعيل</th>
                    <th>الحالة</th>
                    <th>تاريخ التفعيل</th>
                    <th>تاريخ انتهاء الصلاحية (6 أشهر)</th>
                    <th>إجراء</th>
                </tr>
            </thead>
            <tbody>
                {% for c in codes %}
                <tr>
                    <td>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="text" id="code-{{ c.id }}" value="{{ c.code }}" readonly style="width: 120px; padding: 5px; font-family: monospace; font-size: 0.88rem; font-weight: bold; color: var(--primary); background: var(--bg-main); border: 1px solid var(--border-color); border-radius: 6px; text-align: center;">
                            <button onclick="copyCode('code-{{ c.id }}', this)" style="background: rgba(245, 158, 11, 0.15); color: var(--primary); border: 1px solid rgba(245, 158, 11, 0.3); padding: 6px 10px; border-radius: 6px; cursor: pointer; font-size: 0.78rem; font-weight: bold;">نسخ 📋</button>
                        </div>
                    </td>
                    <td>
                        {% if c.is_used %}
                            {% if c.expires_at and c.expires_at < now %}
                                <span class="badge badge-danger">منتهي الصلاحية ⌛</span>
                            {% else %}
                                <span class="badge badge-success">مفعل ونشط ✔️</span>
                            {% endif %}
                        {% else %}
                            <span class="badge" style="background:rgba(245, 158, 11, 0.15); color:#f59e0b;">متاح للبيع 🟢</span>
                        {% endif %}
                    </td>
                    <td>{{ c.activated_at.strftime('%Y-%m-%d') if c.activated_at else '-' }}</td>
                    <td>{{ c.expires_at.strftime('%Y-%m-%d') if c.expires_at else '-' }}</td>
                    <td>
                        <a href="{{ url_for('delete_code', id=c.id) }}" style="color: #fb7185; text-decoration: none; font-weight: bold;">حذف 🗑️</a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">لا توجد أكواد مولدة حتى الآن.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
        function copyCode(elementId, btn) {
            const inputField = document.getElementById(elementId);
            inputField.select();
            inputField.setSelectionRange(0, 99999);
            try {
                navigator.clipboard.writeText(inputField.value).then(() => showSuccess(btn));
            } catch (err) {
                document.execCommand('copy');
                showSuccess(btn);
            }
        }
        function showSuccess(btn) {
            const originalText = btn.innerText;
            btn.innerText = "تم ✓";
            btn.style.background = "rgba(16, 185, 129, 0.2)";
            btn.style.color = "#34d399";
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.background = "rgba(245, 158, 11, 0.15)";
                btn.style.color = "var(--primary)";
            }, 2000);
        }
    </script>
""",
)

# ----------------- Routes -----------------


@app.route("/")
def index():
  now = datetime.utcnow()
  all_barbers = Barber.query.all()
  active_barbers = []
  for b in all_barbers:
    if b.activation_code and b.activation_code.expires_at > now:
      reviews = Review.query.filter_by(barber_id=b.id).all()
      if reviews:
        avg = sum([r.rating for r in reviews]) / len(reviews)
        avg_rating = round(avg, 1)
        total_reviews = len(reviews)
      else:
        avg_rating = 0.0
        total_reviews = 0

      active_barbers.append({
          "barber": b,
          "avg_rating": avg_rating,
          "total_reviews": total_reviews,
      })

  return render_template_string(
      INDEX_TEMPLATE, active_barbers=active_barbers
  )


@app.route("/barber/<int:barber_id>")
def barber_profile(barber_id):
  now = datetime.utcnow()
  barber = Barber.query.get_or_404(barber_id)
  if not barber.activation_code or barber.activation_code.expires_at <= now:
    flash("عذراً، هذا الحلاق منتهي الاشتراك حالياً.", "alert")
    return redirect(url_for("index"))

  services = Service.query.filter_by(barber_id=barber.id).all()
  reviews = Review.query.filter_by(barber_id=barber.id).order_by(
      Review.created_at.desc()
  ).all()

  if reviews:
    avg = sum([r.rating for r in reviews]) / len(reviews)
    avg_rating = round(avg, 1)
    total_reviews = len(reviews)
  else:
    avg_rating = 0.0
    total_reviews = 0

  return render_template_string(
      BARBER_PROFILE_TEMPLATE,
      barber=barber,
      services=services,
      reviews=reviews,
      avg_rating=avg_rating,
      total_reviews=total_reviews,
  )


@app.route("/book/<int:barber_id>", methods=["POST"])
def book_appointment(barber_id):
  customer_name = request.form.get("customer_name")
  phone = request.form.get("phone")
  service_id = request.form.get("service_id")
  date_time = request.form.get("date_time")

  if customer_name and phone and service_id and date_time:
    new_app = Appointment(
        barber_id=barber_id,
        customer_name=customer_name,
        phone=phone,
        service_id=service_id,
        date_time=date_time,
        status="قيد الانتظار",
    )
    db.session.add(new_app)
    db.session.commit()
    flash("تم إرسال طلب الحجز بنجاح!", "success")

  return redirect(url_for("barber_profile", barber_id=barber_id))


@app.route("/review/<int:barber_id>", methods=["POST"])
def add_review(barber_id):
  client_name = request.form.get("client_name")
  rating = request.form.get("rating")
  comment = request.form.get("comment")

  if client_name and rating:
    new_rev = Review(
        barber_id=barber_id,
        client_name=client_name,
        rating=int(rating),
        comment=comment,
    )
    db.session.add(new_rev)
    db.session.commit()
    flash("تم إضافة تقييمك بنجاح، شكراً لك!", "success")

  return redirect(url_for("barber_profile", barber_id=barber_id))


@app.route("/barber/register", methods=["GET", "POST"])
def barber_register():
  if request.method == "POST":
    activation_code = request.form.get("activation_code").strip()
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    username = request.form.get("username")
    phone = request.form.get("phone")
    location = request.form.get("location")
    password = request.form.get("password")

    code_obj = ActivationCode.query.filter_by(
        code=activation_code, is_used=False
    ).first()
    if not code_obj:
      flash("كود التفعيل غير صالح أو مستخدم مسبقاً!", "alert")
      return render_template_string(REGISTER_TEMPLATE)

    existing = Barber.query.filter_by(username=username).first()
    if existing:
      flash("اسم المحل مستخدم مسبقاً، اختر اسماً آخر.", "alert")
    else:
      now = datetime.utcnow()
      code_obj.is_used = True
      code_obj.activated_at = now
      code_obj.expires_at = now + timedelta(days=180)
      db.session.commit()

      new_barber = Barber(
          activation_code_id=code_obj.id,
          first_name=first_name,
          last_name=last_name,
          username=username,
          phone=phone,
          location=location,
          password=password,
      )
      db.session.add(new_barber)
      db.session.commit()

      flash("تم تفعيل حسابك بنجاح لمدة 6 أشهر! سجل دخولك الآن.", "success")
      return redirect(url_for("barber_login"))

  return render_template_string(REGISTER_TEMPLATE)


@app.route("/barber/login", methods=["GET", "POST"])
def barber_login():
  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")

    barber = Barber.query.filter_by(
        username=username, password=password
    ).first()
    if barber:
      now = datetime.utcnow()
      if (
          not barber.activation_code
          or barber.activation_code.expires_at <= now
      ):
        flash(
            "عذراً، لقد انتهت صلاحية حسابك (مرت 6 أشهر). يرجى تجديد الكود مع"
            " المالك.",
            "alert",
        )
      else:
        session["barber_id"] = barber.id
        return redirect(url_for("dashboard"))
    else:
      flash("بيانات الدخول غير صحيحة!", "alert")

  return render_template_string(LOGIN_TEMPLATE)


@app.route("/barber/dashboard")
def dashboard():
  barber_id = session.get("barber_id")
  if not barber_id:
    return redirect(url_for("barber_login"))

  barber = Barber.query.get(barber_id)
  now = datetime.utcnow()
  if not barber.activation_code or barber.activation_code.expires_at <= now:
    session.pop("barber_id", None)
    flash("انتهت صلاحية حسابك.", "alert")
    return redirect(url_for("barber_login"))

  services = Service.query.filter_by(barber_id=barber_id).all()
  appointments = Appointment.query.filter_by(barber_id=barber_id).order_by(
      Appointment.date_time.desc()
  ).all()

  return render_template_string(
      DASHBOARD_TEMPLATE,
      barber=barber,
      services=services,
      appointments=appointments,
  )


@app.route("/barber/add_service", methods=["POST"])
def add_service():
  barber_id = session.get("barber_id")
  if not barber_id:
    return redirect(url_for("barber_login"))

  name = request.form.get("name")
  price = request.form.get("price")
  duration = request.form.get("duration")

  if name and price and duration:
    new_service = Service(
        barber_id=barber_id,
        name=name,
        price=float(price),
        duration=int(duration),
    )
    db.session.add(new_service)
    db.session.commit()
    flash("تمت إضافة الخدمة بنجاح", "success")

  return redirect(url_for("dashboard"))


@app.route("/barber/delete_service/<int:id>")
def delete_service(id):
  barber_id = session.get("barber_id")
  if not barber_id:
    return redirect(url_for("barber_login"))

  service = Service.query.get_or_404(id)
  if service.barber_id == barber_id:
    db.session.delete(service)
    db.session.commit()
    flash("تم حذف الخدمة بنجاح", "success")

  return redirect(url_for("dashboard"))


@app.route("/barber/update/<int:id>/<status>")
def update_status(id, status):
  barber_id = session.get("barber_id")
  if not barber_id:
    return redirect(url_for("barber_login"))

  app_item = Appointment.query.get_or_404(id)
  if app_item.barber_id == barber_id:
    app_item.status = status
    db.session.commit()

  return redirect(url_for("dashboard"))


@app.route("/barber/logout")
def logout():
  session.pop("barber_id", None)
  return redirect(url_for("index"))


# ----------------- Admin Routes -----------------

ADMIN_SECRET_KEY = "admin123"


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
  if request.method == "POST":
    pwd = request.form.get("admin_password")
    if pwd == ADMIN_SECRET_KEY:
      session["is_admin"] = True
      return redirect(url_for("admin_dashboard"))
    else:
      flash("كلمة مرور المالك غير صحيحة!", "alert")
  return render_template_string(ADMIN_LOGIN_TEMPLATE)


@app.route("/admin/dashboard")
def admin_dashboard():
  if not session.get("is_admin"):
    return redirect(url_for("admin_login"))

  now = datetime.utcnow()
  codes = ActivationCode.query.order_by(ActivationCode.created_at.desc()).all()

  confirmed_apps = Appointment.query.filter_by(status="مؤكد").all()
  stats_dict = {}

  for app_item in confirmed_apps:
    barber_name = (
        app_item.barber.username if app_item.barber else "غير معروف"
    )
    day_str = (
        app_item.updated_at.strftime("%Y-%m-%d")
        if app_item.updated_at
        else "اليوم"
    )

    key = (barber_name, day_str)
    stats_dict[key] = stats_dict.get(key, 0) + 1

  daily_stats = []
  for (b_name, day_val), count in stats_dict.items():
    daily_stats.append(
        {"barber_name": b_name, "day": day_val, "count": count}
    )

  return render_template_string(
      ADMIN_DASHBOARD_TEMPLATE,
      codes=codes,
      daily_stats=daily_stats,
      now=now,
  )


@app.route("/admin/generate_code", methods=["POST"])
def generate_code():
  if not session.get("is_admin"):
    return redirect(url_for("admin_login"))

  chars = string.ascii_uppercase + string.digits
  random_part = "".join(random.choices(chars, k=8))
  new_code_str = f"CUT-{random_part[:4]}-{random_part[4:]}"

  code_item = ActivationCode(code=new_code_str)
  db.session.add(code_item)
  db.session.commit()
  flash(f"تم توليد الكود بنجاح: {new_code_str}", "success")

  return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_code/<int:id>")
def delete_code(id):
  if not session.get("is_admin"):
    return redirect(url_for("admin_login"))

  code_item = ActivationCode.query.get_or_404(id)
  db.session.delete(code_item)
  db.session.commit()
  flash("تم حذف الكود بنجاح", "success")

  return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
  session.pop("is_admin", None)
  return redirect(url_for("index"))


if __name__ == "__main__":
  with app.app_context():
    db.create_all()  # تم التعديل هنا: إنشاء الجداول بأمان بدون حذف القديمة
  app.run(host="0.0.0.0", port=5000, debug=True)
