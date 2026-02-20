from flask import Flask, render_template, request, redirect, flash, url_for
from dotenv import load_dotenv
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import resend

load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = os.getenv("DEBUG", "False") == "True"
app.secret_key = os.getenv("SECRET_KEY") or "dev-key"

# ===== RESEND CONFIG =====
resend.api_key = os.getenv("RESEND_API_KEY")

# ===== DATABASE =====
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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


# ===== EMAIL (API) =====
def send_email(to_email, subject, body, html=None):
    try:
        resend.Emails.send({
            "from": "Złap Pracę <support@zlapprace.pl>",
            "to": [to_email],
            "subject": subject,
            "html": html if html else f"<p>{body}</p>",
        })
        print(f"Email sent to {to_email}")

    except Exception as e:
        print("EMAIL API ERROR:", e)


def send_pitch_password(to_email):
    PITCH_PASSWORD = os.getenv("PITCH_PASSWORD")

    subject = "Złap Pracę – Hasło do Pitch Deck"

    body = f"""
Dziękujemy za zainteresowanie projektem Złap Pracę.

Hasło do pliku Pitch Deck:
{PITCH_PASSWORD}

Plik:
https://zlapprace.pl/static/pitch_deck.pdf

Zespół Złap Pracę
"""

    html = f"""
    <h2>Złap Pracę – Pitch Deck</h2>
    <p>Dziękujemy za zainteresowanie projektem.</p>
    <p><strong>Hasło:</strong> {PITCH_PASSWORD}</p>
    <p><a href="https://zlapprace.pl/static/pitch_deck.pdf">
    Otwórz Pitch Deck</a></p>
    """

    send_email(to_email, subject, body, html)


def send_confirmation_email(to_email, name, user_type):
    subject = "Złap Pracę – Potwierdzenie dołączenia"

    role_pl = "Klient" if user_type == "klient" else "Fachowiec"
    role_en = "Client" if user_type == "klient" else "Service Provider"

    body = f"""
Dziękujemy za dołączenie do listy wczesnego dostępu jako {role_pl}.
https://zlapprace.pl
"""

    html = f"""
    <html>
    <body style="font-family:Arial;background:#f8fafc;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;padding:30px;border-radius:12px;">
            <h2>Witaj {name or ''}</h2>
            <p>Dziękujemy za dołączenie jako <strong>{role_pl}</strong>.</p>
            <p>Thank you for joining as a <strong>{role_en}</strong>.</p>
            <p>
                <a href="https://zlapprace.pl"
                style="display:inline-block;padding:12px 24px;
                background:#2563EB;color:white;text-decoration:none;border-radius:8px;">
                Odwiedź stronę
                </a>
            </p>
            <hr>
            <small>Złap Pracę © 2026</small>
        </div>
    </body>
    </html>
    """

    send_email(to_email, subject, body, html)


# ===== ROUTES =====
@app.route("/", methods=["GET", "POST"])
def index():
    session = Session()

    try:
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

            flash("Dziękujemy! Jesteś na liście.", "success")
            return redirect(url_for("index"))

        return render_template("index.html", waitlist_count=waitlist_count)

    finally:
        session.close()


@app.route("/investor-access", methods=["POST"])
def investor_access():
    session = Session()

    try:
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

        flash("Hasło zostało wysłane na email.", "success")
        return redirect(url_for("index"))

    finally:
        session.close()


@app.route("/confidentiality-policy")
def confidentiality_policy():
    lang = request.args.get("lang", "pl")
    return render_template("confidentiality.html", lang=lang)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))