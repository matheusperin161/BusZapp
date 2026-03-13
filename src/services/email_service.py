"""Serviço de envio de e-mail via Gmail SMTP."""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = os.getenv('GMAIL_USER', '')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
APP_URL = os.getenv('APP_URL', 'http://localhost:8080')


def _send(to_email: str, subject: str, html_body: str) -> bool:
    """Envia um e-mail via Gmail SMTP. Retorna True se enviado com sucesso."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print('[email_service] GMAIL_USER ou GMAIL_APP_PASSWORD não configurados.')
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f'BusZapp <{GMAIL_USER}>'
    msg['To']      = to_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, to_email, msg.as_string())
        print(f'[email_service] E-mail enviado para {to_email}')
        return True
    except Exception as e:
        print(f'[email_service] Erro ao enviar e-mail: {e}')
        return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Envia e-mail de verificação de conta."""
    link = f'{APP_URL}/api/auth/verify-email?token={token}'
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)">
      <div style="background:linear-gradient(135deg,#fbbf24,#f97316);padding:32px 40px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:28px;font-weight:800">🚌 BusZapp</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px">Confirme seu cadastro</p>
      </div>
      <div style="padding:32px 40px">
        <h2 style="color:#1a202c;margin:0 0 12px;font-size:20px">Olá, {username}!</h2>
        <p style="color:#4a5568;line-height:1.6;margin:0 0 24px">
          Obrigado por se cadastrar no BusZapp. Clique no botão abaixo para confirmar seu e-mail e ativar sua conta.
        </p>
        <div style="text-align:center;margin-bottom:28px">
          <a href="{link}"
             style="display:inline-block;background:linear-gradient(135deg,#fbbf24,#f97316);color:#fff;text-decoration:none;padding:14px 36px;border-radius:12px;font-weight:700;font-size:15px;box-shadow:0 4px 16px rgba(249,115,22,0.35)">
            ✅ Confirmar e-mail
          </a>
        </div>
        <p style="color:#718096;font-size:13px;line-height:1.5;margin:0">
          Este link expira em <strong>24 horas</strong>. Se você não criou uma conta, pode ignorar este e-mail.
        </p>
      </div>
      <div style="background:#f7fafc;padding:16px 40px;text-align:center;border-top:1px solid #e2e8f0">
        <p style="color:#a0aec0;font-size:12px;margin:0">BusZapp — Mobilidade Urbana</p>
      </div>
    </div>
    """
    return _send(to_email, 'Confirme seu cadastro no BusZapp', html)


def send_password_reset_email(to_email: str, username: str, token: str) -> bool:
    """Envia e-mail de redefinição de senha."""
    link = f'{APP_URL}/forgot-password.html?token={token}'
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)">
      <div style="background:linear-gradient(135deg,#fbbf24,#f97316);padding:32px 40px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:28px;font-weight:800">🚌 BusZapp</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px">Redefinição de senha</p>
      </div>
      <div style="padding:32px 40px">
        <h2 style="color:#1a202c;margin:0 0 12px;font-size:20px">Olá, {username}!</h2>
        <p style="color:#4a5568;line-height:1.6;margin:0 0 24px">
          Recebemos uma solicitação para redefinir a senha da sua conta. Clique no botão abaixo para criar uma nova senha.
        </p>
        <div style="text-align:center;margin-bottom:28px">
          <a href="{link}"
             style="display:inline-block;background:linear-gradient(135deg,#fbbf24,#f97316);color:#fff;text-decoration:none;padding:14px 36px;border-radius:12px;font-weight:700;font-size:15px;box-shadow:0 4px 16px rgba(249,115,22,0.35)">
            🔑 Redefinir senha
          </a>
        </div>
        <p style="color:#718096;font-size:13px;line-height:1.5;margin:0">
          Este link expira em <strong>1 hora</strong>. Se você não solicitou a redefinição, pode ignorar este e-mail.
        </p>
      </div>
      <div style="background:#f7fafc;padding:16px 40px;text-align:center;border-top:1px solid #e2e8f0">
        <p style="color:#a0aec0;font-size:12px;margin:0">BusZapp — Mobilidade Urbana</p>
      </div>
    </div>
    """
    return _send(to_email, 'Redefinição de senha — BusZapp', html)
