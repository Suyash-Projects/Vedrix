import smtplib
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  BASE LAYOUT  (shared wrapper for all emails)
# ─────────────────────────────────────────────────────────────────────────────

def _base(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#020617;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#020617;padding:40px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <!-- HEADER -->
      <tr><td style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 100%);border-radius:24px 24px 0 0;padding:40px 48px;border-bottom:1px solid rgba(139,92,246,0.3);">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td>
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:linear-gradient(135deg,#7c3aed,#4f46e5);width:36px;height:36px;border-radius:10px;text-align:center;vertical-align:middle;">
                    <span style="color:#fff;font-size:18px;font-weight:900;">V</span>
                  </td>
                  <td style="padding-left:12px;color:#fff;font-size:22px;font-weight:900;letter-spacing:-0.5px;">Vedrix</td>
                </tr>
              </table>
            </td>
            <td align="right">
              <span style="background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);color:#a78bfa;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:6px 14px;border-radius:20px;">AI Interview Platform</span>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- BODY -->
      <tr><td style="background:#0f172a;padding:48px;border-left:1px solid rgba(255,255,255,0.05);border-right:1px solid rgba(255,255,255,0.05);">
        {body}
      </td></tr>

      <!-- FOOTER -->
      <tr><td style="background:#080d1a;border-radius:0 0 24px 24px;padding:32px 48px;border:1px solid rgba(255,255,255,0.05);border-top:1px solid rgba(139,92,246,0.15);">
        <p style="margin:0 0 8px;color:#475569;font-size:12px;text-align:center;">© 2026 Vedrix AI System · Building the future of hiring</p>
        <p style="margin:0;color:#334155;font-size:11px;text-align:center;">
          This email was sent by Vedrix. If you didn't request this, you can safely ignore it.
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
#  REUSABLE COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def _btn(text: str, url: str) -> str:
    return f"""<table cellpadding="0" cellspacing="0" style="margin:32px 0;">
  <tr><td style="background:linear-gradient(135deg,#7c3aed,#4f46e5);border-radius:14px;box-shadow:0 8px 32px rgba(124,58,237,0.4);">
    <a href="{url}" style="display:block;padding:16px 40px;color:#fff;font-size:14px;font-weight:800;text-decoration:none;letter-spacing:1px;text-transform:uppercase;">{text}</a>
  </td></tr>
</table>"""


def _stat(label: str, value: str, color: str = "#a78bfa") -> str:
    return f"""<td style="text-align:center;padding:0 12px;">
  <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:20px 24px;">
    <p style="margin:0 0 6px;color:{color};font-size:26px;font-weight:900;">{value}</p>
    <p style="margin:0;color:#64748b;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">{label}</p>
  </div>
</td>"""


def _section_title(text: str) -> str:
    return f"""<p style="margin:32px 0 16px;color:#94a3b8;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:12px;">{text}</p>"""


def _list_item(text: str, icon_color: str = "#7c3aed", bullet: str = "●") -> str:
    return f"""<tr><td style="padding:8px 0;">
  <table cellpadding="0" cellspacing="0"><tr>
    <td style="color:{icon_color};font-size:8px;padding-right:12px;vertical-align:top;padding-top:4px;">{bullet}</td>
    <td style="color:#cbd5e1;font-size:14px;line-height:1.6;">{text}</td>
  </tr></table>
</td></tr>"""


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATE 1 — WELCOME EMAIL
# ─────────────────────────────────────────────────────────────────────────────

def _build_welcome(first_name: str, user_type: str) -> str:
    role_badge = "HR Expert" if user_type == "hr" else "Candidate"
    role_color = "#818cf8" if user_type == "hr" else "#34d399"
    features = (
        [
            "Create unlimited recruitment drives",
            "Generate magic invite links for candidates",
            "Bulk schedule candidates via email",
            "View real-time AI evaluation reports",
        ]
        if user_type == "hr"
        else [
            "Take adaptive AI-powered interviews",
            "Get instant performance reports",
            "Track your scores across dimensions",
            "Receive detailed feedback after each session",
        ]
    )
    body = f"""
<p style="margin:0 0 8px;color:#64748b;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">Welcome to Vedrix</p>
<h1 style="margin:0 0 24px;color:#f8fafc;font-size:32px;font-weight:900;line-height:1.2;">Hello, {first_name}! 👋</h1>
<p style="margin:0 0 24px;color:#94a3b8;font-size:15px;line-height:1.7;">
  Your account has been created successfully. You're registered as a
  <span style="background:rgba(124,58,237,0.15);color:{role_color};font-weight:700;padding:2px 10px;border-radius:6px;font-size:13px;">{role_badge}</span>
  on the Vedrix platform.
</p>

{_section_title("What you can do")}
<table cellpadding="0" cellspacing="0" width="100%">
  {''.join(_list_item(f) for f in features)}
</table>

{_btn("Go to Dashboard", settings.FRONTEND_URL)}

<p style="margin:24px 0 0;color:#475569;font-size:13px;line-height:1.6;">
  If you have any questions, reply to this email and our team will help you get started.
</p>"""
    return _base(f"Welcome to Vedrix, {first_name}!", body)


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATE 2 — INTERVIEW INVITE (magic link)
# ─────────────────────────────────────────────────────────────────────────────

def _build_invite(
    candidate_email: str,
    job_role: str,
    drive_title: str,
    invite_link: str,
    expires_hours: int,
    skills: Optional[str] = None,
) -> str:
    skills_row = ""
    if skills:
        tags = "".join(
            f'<span style="background:rgba(124,58,237,0.12);border:1px solid rgba(124,58,237,0.25);color:#a78bfa;font-size:11px;font-weight:700;padding:4px 12px;border-radius:20px;margin:4px 4px 0 0;display:inline-block;">{s.strip()}</span>'
            for s in skills.split(",") if s.strip()
        )
        skills_row = f"""
{_section_title("Required Skills")}
<p style="margin:0 0 16px;">{tags}</p>"""

    body = f"""
<p style="margin:0 0 8px;color:#64748b;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">Interview Invitation</p>
<h1 style="margin:0 0 24px;color:#f8fafc;font-size:28px;font-weight:900;line-height:1.2;">You've been invited to interview 🎯</h1>
<p style="margin:0 0 24px;color:#94a3b8;font-size:15px;line-height:1.7;">
  You have been selected to participate in an AI-powered interview for the following position.
  Click the button below to begin your assessment.
</p>

<div style="background:rgba(124,58,237,0.06);border:1px solid rgba(124,58,237,0.2);border-radius:20px;padding:28px 32px;margin:0 0 8px;">
  <p style="margin:0 0 4px;color:#64748b;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Position</p>
  <p style="margin:0 0 20px;color:#f8fafc;font-size:22px;font-weight:900;">{job_role}</p>
  <p style="margin:0 0 4px;color:#64748b;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Drive</p>
  <p style="margin:0;color:#a78bfa;font-size:15px;font-weight:700;">{drive_title}</p>
</div>

{skills_row}

{_section_title("How it works")}
<table cellpadding="0" cellspacing="0" width="100%">
  {_list_item("The interview is fully AI-powered and adaptive — no human interviewer needed")}
  {_list_item("Speak naturally using your microphone for voice-based responses")}
  {_list_item("The AI adapts questions based on your answers in real-time")}
  {_list_item("You'll receive a detailed performance report immediately after")}
</table>

{_btn("Start My Interview", invite_link)}

<div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:12px;padding:16px 20px;margin-top:8px;">
  <p style="margin:0;color:#f87171;font-size:12px;font-weight:700;">
    ⏰ This link expires in <strong>{expires_hours} hours</strong>. Do not share it — it is unique to you.
  </p>
</div>"""
    return _base(f"Interview Invitation — {job_role}", body)


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATE 3 — INTERVIEW STARTED (confirmation to candidate)
# ─────────────────────────────────────────────────────────────────────────────

def _build_interview_started(first_name: str, job_role: str) -> str:
    body = f"""
<p style="margin:0 0 8px;color:#64748b;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">Interview In Progress</p>
<h1 style="margin:0 0 24px;color:#f8fafc;font-size:28px;font-weight:900;line-height:1.2;">Your interview has started, {first_name}! 🚀</h1>
<p style="margin:0 0 24px;color:#94a3b8;font-size:15px;line-height:1.7;">
  We've recorded the start of your AI interview for the role of
  <strong style="color:#a78bfa;">{job_role}</strong>.
  Good luck — our AI interviewer is ready to evaluate your responses.
</p>

<div style="background:rgba(52,211,153,0.06);border:1px solid rgba(52,211,153,0.2);border-radius:20px;padding:28px 32px;">
  <table cellpadding="0" cellspacing="0" width="100%">
    {_list_item("Stay in fullscreen mode throughout the session", "#34d399", "✓")}
    {_list_item("Speak clearly and at a natural pace", "#34d399", "✓")}
    {_list_item("Answer each question as thoroughly as possible", "#34d399", "✓")}
    {_list_item("Your report will be emailed to you upon completion", "#34d399", "✓")}
  </table>
</div>

<p style="margin:32px 0 0;color:#475569;font-size:13px;line-height:1.6;">
  This is an automated confirmation. Your session is being monitored by our AI proctoring system.
</p>"""
    return _base("Interview Started — Vedrix", body)


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATE 4 — INTERVIEW COMPLETE + FULL REPORT (to candidate)
# ─────────────────────────────────────────────────────────────────────────────

def _score_bar(label: str, score: float) -> str:
    pct = int((score / 10) * 100)
    color = "#34d399" if score >= 7.5 else "#f59e0b" if score >= 5 else "#f87171"
    return f"""<tr><td style="padding:8px 0;">
  <table cellpadding="0" cellspacing="0" width="100%"><tr>
    <td style="color:#94a3b8;font-size:12px;font-weight:700;width:140px;text-transform:uppercase;letter-spacing:1px;">{label}</td>
    <td style="padding:0 16px;">
      <div style="background:rgba(255,255,255,0.05);border-radius:100px;height:8px;overflow:hidden;">
        <div style="background:{color};width:{pct}%;height:8px;border-radius:100px;"></div>
      </div>
    </td>
    <td style="color:{color};font-size:14px;font-weight:900;width:40px;text-align:right;">{score}</td>
  </tr></table>
</td></tr>"""


def _build_report_candidate(
    first_name: str,
    job_role: str,
    report: Dict[str, Any],
) -> str:
    rec = report.get("hire_recommendation", "—")
    rec_color = {"Strong Hire": "#34d399", "Hire": "#34d399", "Maybe": "#f59e0b", "No Hire": "#f87171"}.get(rec, "#a78bfa")

    strengths_rows = "".join(_list_item(s, "#34d399", "✓") for s in report.get("strengths", []))
    weaknesses_rows = "".join(_list_item(w, "#f59e0b", "→") for w in report.get("weaknesses", []))

    body = f"""
<p style="margin:0 0 8px;color:#64748b;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">Interview Complete</p>
<h1 style="margin:0 0 8px;color:#f8fafc;font-size:28px;font-weight:900;line-height:1.2;">Your results are in, {first_name}! 📊</h1>
<p style="margin:0 0 32px;color:#94a3b8;font-size:15px;line-height:1.7;">
  Your AI interview for <strong style="color:#a78bfa;">{job_role}</strong> has been completed and evaluated.
  Here is your full performance report.
</p>

<!-- SCORE HERO -->
<div style="background:linear-gradient(135deg,rgba(124,58,237,0.15),rgba(79,70,229,0.1));border:1px solid rgba(124,58,237,0.25);border-radius:24px;padding:36px;text-align:center;margin-bottom:32px;">
  <p style="margin:0 0 4px;color:#64748b;font-size:10px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">Overall Score</p>
  <p style="margin:0 0 12px;color:#f8fafc;font-size:64px;font-weight:900;line-height:1;">{report.get('overall_score', '—')}<span style="font-size:24px;color:#64748b;">/10</span></p>
  <span style="background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);color:{rec_color};font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:8px 20px;border-radius:20px;">{rec}</span>
</div>

<!-- SCORE BREAKDOWN -->
{_section_title("Score Breakdown")}
<table cellpadding="0" cellspacing="0" width="100%">
  {_score_bar("Technical Accuracy", report.get('technical_accuracy', 0))}
  {_score_bar("Communication", report.get('communication_clarity', 0))}
  {_score_bar("Depth of Knowledge", report.get('depth_of_knowledge', 0))}
</table>

<!-- SUMMARY -->
{_section_title("Executive Summary")}
<div style="background:rgba(255,255,255,0.02);border-left:3px solid #7c3aed;border-radius:0 12px 12px 0;padding:20px 24px;margin-bottom:8px;">
  <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.8;font-style:italic;">"{report.get('summary', '')}"</p>
</div>

<!-- STRENGTHS -->
{_section_title("Key Strengths")}
<table cellpadding="0" cellspacing="0" width="100%">{strengths_rows}</table>

<!-- WEAKNESSES -->
{_section_title("Areas for Improvement")}
<table cellpadding="0" cellspacing="0" width="100%">{weaknesses_rows}</table>

{_btn("View Full Report Online", settings.FRONTEND_URL)}

<p style="margin:0;color:#475569;font-size:12px;line-height:1.6;text-align:center;">
  This report has also been shared with the hiring team for review.
</p>"""
    return _base(f"Your Interview Report — {job_role}", body)


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATE 5 — HR NOTIFICATION (new interview completed)
# ─────────────────────────────────────────────────────────────────────────────

def _build_report_hr(
    hr_first_name: str,
    candidate_email: str,
    job_role: str,
    drive_title: str,
    report: Dict[str, Any],
    session_id: str,
) -> str:
    rec = report.get("hire_recommendation", "—")
    rec_color = {"Strong Hire": "#34d399", "Hire": "#34d399", "Maybe": "#f59e0b", "No Hire": "#f87171"}.get(rec, "#a78bfa")
    report_url = f"{settings.FRONTEND_URL}?view=report&session={session_id}"

    strengths_rows = "".join(_list_item(s, "#34d399", "✓") for s in report.get("strengths", []))
    weaknesses_rows = "".join(_list_item(w, "#f59e0b", "→") for w in report.get("weaknesses", []))

    body = f"""
<p style="margin:0 0 8px;color:#64748b;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;">New Evaluation Ready</p>
<h1 style="margin:0 0 24px;color:#f8fafc;font-size:28px;font-weight:900;line-height:1.2;">Candidate report ready, {hr_first_name}! 🎯</h1>
<p style="margin:0 0 24px;color:#94a3b8;font-size:15px;line-height:1.7;">
  A candidate has completed their AI interview. Here is the full evaluation summary.
</p>

<!-- CANDIDATE + DRIVE INFO -->
<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:20px;padding:28px 32px;margin-bottom:32px;">
  <table cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td style="padding-bottom:16px;">
        <p style="margin:0 0 4px;color:#475569;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Candidate</p>
        <p style="margin:0;color:#f8fafc;font-size:16px;font-weight:700;">{candidate_email}</p>
      </td>
      <td style="padding-bottom:16px;text-align:right;">
        <span style="background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);color:{rec_color};font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:6px 16px;border-radius:20px;">{rec}</span>
      </td>
    </tr>
    <tr>
      <td>
        <p style="margin:0 0 4px;color:#475569;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Role</p>
        <p style="margin:0;color:#a78bfa;font-size:15px;font-weight:700;">{job_role}</p>
      </td>
      <td style="text-align:right;">
        <p style="margin:0 0 4px;color:#475569;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Drive</p>
        <p style="margin:0;color:#94a3b8;font-size:14px;font-weight:600;">{drive_title}</p>
      </td>
    </tr>
  </table>
</div>

<!-- SCORES -->
<table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:32px;">
  <tr>
    {_stat("Overall", str(report.get('overall_score', '—')), "#a78bfa")}
    {_stat("Technical", str(report.get('technical_accuracy', '—')), "#818cf8")}
    {_stat("Communication", str(report.get('communication_clarity', '—')), "#34d399")}
    {_stat("Depth", str(report.get('depth_of_knowledge', '—')), "#f59e0b")}
  </tr>
</table>

<!-- SUMMARY -->
{_section_title("AI Executive Summary")}
<div style="background:rgba(255,255,255,0.02);border-left:3px solid #7c3aed;border-radius:0 12px 12px 0;padding:20px 24px;margin-bottom:8px;">
  <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.8;font-style:italic;">"{report.get('summary', '')}"</p>
</div>

{_section_title("Strengths")}
<table cellpadding="0" cellspacing="0" width="100%">{strengths_rows}</table>

{_section_title("Improvement Areas")}
<table cellpadding="0" cellspacing="0" width="100%">{weaknesses_rows}</table>

{_btn("View Full Report & Transcript", report_url)}"""
    return _base(f"New Candidate Report — {job_role}", body)


# ─────────────────────────────────────────────────────────────────────────────
#  SEND ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _send_sync(to: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_USERNAME}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    mail_server = settings.MAIL_SERVER
    mail_port = settings.MAIL_PORT
    
    # Handle SSL (port 465) vs TLS (port 587)
    if mail_port == 465:
        with smtplib.SMTP_SSL(mail_server, mail_port) as server:
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_USERNAME, to, msg.as_string())
    else:
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except smtplib.SMTPNotSupportedError:
                # Server doesn't support STARTTLS, continue without encryption
                pass
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_USERNAME, to, msg.as_string())


async def _send(to: str, subject: str, html: str) -> None:
    """Non-blocking send — runs SMTP in a thread so it never blocks the event loop."""
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.warning(f"[Email] Skipped (no credentials) → {subject} → {to}")
        return
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _send_sync, to, subject, html)
        logger.info(f"[Email] Sent → {subject} → {to}")
    except Exception as e:
        logger.error(f"[Email] Failed → {subject} → {to} | Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

async def send_welcome_email(to: str, first_name: str, user_type: str) -> None:
    await _send(to, f"Welcome to Vedrix, {first_name}! 🚀", _build_welcome(first_name, user_type))


async def send_invite_email(
    to: str,
    job_role: str,
    drive_title: str,
    invite_link: str,
    expires_hours: int = 72,
    skills: Optional[str] = None,
) -> None:
    await _send(
        to,
        f"You're invited to interview for {job_role} — Vedrix",
        _build_invite(to, job_role, drive_title, invite_link, expires_hours, skills),
    )


async def send_interview_started_email(to: str, first_name: str, job_role: str) -> None:
    await _send(to, "Your Vedrix interview has started 🎙️", _build_interview_started(first_name, job_role))


async def send_report_to_candidate(
    to: str,
    first_name: str,
    job_role: str,
    report: Dict[str, Any],
) -> None:
    await _send(
        to,
        f"Your Interview Report is Ready — {job_role} | Vedrix",
        _build_report_candidate(first_name, job_role, report),
    )


async def send_report_to_hr(
    to: str,
    hr_first_name: str,
    candidate_email: str,
    job_role: str,
    drive_title: str,
    report: Dict[str, Any],
    session_id: str,
) -> None:
    await _send(
        to,
        f"New Candidate Evaluated — {job_role} | Vedrix",
        _build_report_hr(hr_first_name, candidate_email, job_role, drive_title, report, session_id),
    )


def _build_credentials_email(first_name: str, username: str, password: str, user_type: str) -> str:
    user_type_label = "Candidate" if user_type == "student" else "HR Manager" if user_type == "hr" else "Administrator"
    login_url = "https://vedrix.ai/login"

    return _base(
        "Your Vedrix Account Credentials",
        f"""
        <div style="padding: 20px 0;">
          <p style="color:#a78bfa;font-size:14px;margin-bottom:24px;">
            Your Vedrix account has been created by an administrator. Here are your login credentials:
          </p>

          <!-- CREDENTIALS BOX -->
          <div style="background:rgba(124,58,237,0.1);border:1px solid rgba(124,58,237,0.3);border-radius:16px;padding:24px;margin:24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding-bottom:12px;">
                  <span style="color:#a78bfa;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Username</span>
                  <div style="color:#fff;font-size:20px;font-weight:700;margin-top:4px;">{username}</div>
                </td>
              </tr>
              <tr>
                <td style="padding-top:12px;border-top:1px solid rgba(255,255,255,0.1);">
                  <span style="color:#a78bfa;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Password</span>
                  <div style="color:#fff;font-size:20px;font-weight:700;margin-top:4px;font-family:monospace;">{password}</div>
                </td>
              </tr>
            </table>
          </div>

          <!-- WARNING -->
          <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:16px;margin:24px 0;">
            <p style="color:#fbbf24;font-size:12px;font-weight:600;margin:0;">
              ⚠️ Please change your password after first login for security.
            </p>
          </div>

          <!-- LOGIN BUTTON -->
          <div style="text-align:center;margin:32px 0;">
            <a href="{login_url}" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;font-size:14px;font-weight:700;padding:16px 32px;border-radius:12px;text-decoration:none;">
              Login to Vedrix
            </a>
          </div>

          <p style="color:#64748b;font-size:12px;margin-top:24px;">
            If you didn't request this account, please contact your administrator immediately.
          </p>
        </div>
        """
    )


async def send_credentials_email(to: str, first_name: str, username: str, password: str, user_type: str) -> None:
    """Send login credentials to a user (admin triggered)."""
    await _send(
        to,
        "Your Vedrix Login Credentials",
        _build_credentials_email(first_name, username, password, user_type),
    )
