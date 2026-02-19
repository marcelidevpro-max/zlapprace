from flask import Flask, render_template, request, redirect, flash, url_for
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = os.getenv("DEBUG", "False") == "True"
app.secret_key = os.getenv("SECRET_KEY") or "dev-key"

# ===== DATABASE =====
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Waitlist(Base):
    __tablename__ = "waitlist"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    email = Column(String(200))
    user_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class Investor(Base):
    __tablename__ = "investors"
    id = Column(Integer, primary_key=True)
    email = Column(String(200))
    accepted = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ===== SMTP =====
def send_email(to_email, subject, body, html=None):
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr(("Złap Pracę", EMAIL_ADDRESS))
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print("SMTP ERROR:", e)

def send_pitch_password(to_email):
    PITCH_PASSWORD = os.getenv("PITCH_PASSWORD")

    subject = "Złap Pracę – Hasło do Pitch Deck"
    body = f"""
Dziękujemy za zainteresowanie projektem Złap Pracę.

Hasło do pliku Pitch Deck:
{PITCH_PASSWORD}

Plik znajduje się na stronie:
https://zlapprace.pl/static/pitch_deck.pdf

Zespół Złap Pracę
"""
    send_email(to_email, subject, body)

def send_confirmation_email(to_email, name, user_type):
    subject = "Złap Pracę – Potwierdzenie dołączenia do listy wczesnego dostępu"

    role_pl = "Klient" if user_type == "klient" else "Fachowiec"
    role_en = "Client" if user_type == "klient" else "Service Provider"

    body = f"""
Dziękujemy za dołączenie do listy wczesnego dostępu Złap Pracę jako {role_pl}!
Będziemy Cię informować o starcie platformy.

https://zlapprace.pl
"""

    html_content = f"""
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f8fafc; margin:0; padding:0; }}
    .container {{ max-width:600px; margin:30px auto; background:white; border-radius:12px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, #0B3C5D, #2563EB); padding:30px; text-align:center; color:white; }}
    .content {{ padding:30px; text-align:center; color:#0B3C5D; }}
    .btn {{ display:inline-block; padding:14px 28px; margin:20px 0; background:#2563EB; color:white; text-decoration:none; border-radius:8px; font-weight:bold; }}
    .footer {{ padding:20px; text-align:center; font-size:13px; color:#6b7280; border-top:1px solid #eee; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="https://zlapprace.pl/static/Ikona1.png" alt="Złap Pracę" style="max-width:150px; display:block; margin:0 auto;">
      <h2>Witaj {name or ''}</h2>
    </div>

    <div class="content">
      <p>Dziękujemy za dołączenie do listy wczesnego dostępu <strong>Złap Pracę</strong> jako {role_pl}!</p>
      <p>Będziemy Cię informować o starcie platformy i damy Ci pierwszeństwo.</p>
      <a href="https://zlapprace.pl" class="btn">Odwiedź stronę</a>

      <hr style="margin:30px 0; border:none; border-top:1px solid #eee;">

      <p>Thank you for joining the <strong>Złap Pracę</strong> early access list as a {role_en}!</p>
      <p>We’ll keep you updated on the launch and give you priority access.</p>
      <a href="https://zlapprace.pl" class="btn">Visit Website</a>
    </div>

    <div class="footer">
      Złap Pracę © 2026 | Wszelkie prawa zastrzeżone
    </div>
  </div>
</body>
</html>
"""

    send_email(to_email, subject, body, html_content)

# ===== ROUTES =====
@app.route("/", methods=["GET", "POST"])
def index():
    session = Session()
    waitlist_count = session.query(Waitlist).count()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        user_type = request.form.get("type", "")

        if not email or not user_type:
            flash("Proszę uzupełnić wszystkie wymagane pola.", "error")
            return redirect(url_for("index"))

        new_user = Waitlist(
            name=name,
            email=email,
            user_type=user_type
        )

        session.add(new_user)
        session.commit()

        send_confirmation_email(email, name, user_type)

        flash("Dziękujemy! Jesteś na liście wczesnego dostępu.", "success")
        session.close()
        return redirect(url_for("index"))

    session.close()
    return render_template("index.html", waitlist_count=waitlist_count)

@app.route("/investor-access", methods=["POST"])
def investor_access():
    session = Session()

    email = request.form.get("email", "").strip()
    confidentiality = request.form.get("confidentiality")

    if not email or not confidentiality:
        flash("Musisz podać email i zaakceptować poufność.", "error")
        return redirect(url_for("index"))

    investor = Investor(
        email=email,
        accepted="yes"
    )

    session.add(investor)
    session.commit()

    send_pitch_password(email)

    flash("Hasło zostało wysłane na podany email.", "success")
    session.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
