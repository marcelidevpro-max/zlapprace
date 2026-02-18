from flask import Flask, render_template, request, redirect, flash, url_for
from dotenv import load_dotenv
import os
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['DEBUG'] = os.getenv("DEBUG", "False") == "True"
app.secret_key = os.getenv("SECRET_KEY") or "tymczasowy-klucz-tylko-do-testow"

# SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 465)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
PITCH_PASSWORD = os.getenv("PITCH_PASSWORD")

CSV_FILE = "waitlist.csv"
INVESTORS_CSV = "investors.csv"

# --- Funkcje pomocnicze ---
def get_waitlist_count():
    if not os.path.exists(CSV_FILE):
        return 0
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            return len(rows) if rows else 0
    except:
        return 0

def send_email(to_email, subject, body, html=None):
    from email.utils import formataddr
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib
    import os

    # Nadawca – wyświetlana nazwa + prawdziwy adres SMTP
    display_name = "support@zlapprace.pl"
    sender_email = os.getenv("EMAIL_ADDRESS")  # np. support+zlapprace_pl.serwer2692968@home.pl

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((display_name, sender_email))
    msg["To"] = to_email
    msg["Subject"] = subject

    # Dodajemy treść zwykłą i HTML
    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    # Połączenie z serwerem Home.pl przez SSL
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT"))
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.set_debuglevel(1)  # pokazuje cały handshake SMTP
        server.login(sender_email, EMAIL_PASSWORD)
        server.send_message(msg)
        
def send_pitch_password(to_email):
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
    body {{ font-family: 'Inter', sans-serif; background: #f8fafc; margin:0; padding:0; }}
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
      <h2 style="margin:10px 0 0 0;">Witaj {name or '!'}</h2>
    </div>
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

# --- Routes ---
@app.route("/investor-access", methods=["POST"])
def investor_access():
    email = request.form.get("email", "").strip()
    confidentiality = request.form.get("confidentiality")

    if not email:
        flash("Podaj poprawny adres email.", "error")
        return redirect(url_for("index"))

    if not confidentiality:
        flash("Musisz zaakceptować poufność materiałów.", "error")
        return redirect(url_for("index"))

    # zapis do CSV z informacją o zgodzie
    with open(INVESTORS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([email, "accepted", datetime.now().isoformat()])

    try:
        send_pitch_password(email)
        flash("Hasło zostało wysłane na podany email.", "success")
    except Exception as e:
        flash(f"Błąd wysyłki: {str(e)}", "error")

    return redirect(url_for("index"))

@app.route("/polityka-poufnosci")
def confidentiality_policy():
    lang = request.args.get('lang', 'pl')
    if lang not in ['pl', 'en']:
        lang = 'pl'
    return render_template("confidentiality.html", lang=lang)

@app.route("/", methods=["GET", "POST"])
def index():
    lang = request.args.get('lang', 'pl')
    if lang not in ['pl', 'en']:
        lang = 'pl'

    waitlist_count = get_waitlist_count()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        user_type = request.form.get("type", "")

        if not email or not user_type:
            flash("Proszę uzupełnić wszystkie wymagane pola.", "error")
            return redirect(url_for("index", lang=lang))

        # Zapis do CSV
        try:
            file_exists = os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0
            with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["name", "email", "type", "timestamp"])
                writer.writerow([name, email, user_type, datetime.now().isoformat()])
        except Exception as e:
            flash(f"Błąd zapisu: {str(e)}", "error")
            return redirect(url_for("index", lang=lang))

        # Wysyłka maila
        try:
            send_confirmation_email(email, name, user_type)
            flash("Dziękujemy! Jesteś na liście wczesnego dostępu.", "success")
        except Exception as e:
            flash(f"Nie udało się wysłać potwierdzenia: {str(e)}", "error")

        return redirect(url_for("index", lang=lang))

    return render_template("index.html", waitlist_count=waitlist_count, lang=lang)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
