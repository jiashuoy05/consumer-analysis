import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

CATEGORY_LABELS = {"食": "飲食", "衣": "衣著", "住": "居住", "行": "交通", "育": "教育", "樂": "娛樂"}


def _get(exp, key, default=""):
    if isinstance(exp, dict):
        return exp.get(key, default)
    return getattr(exp, key, default)


def _sum_by_category(classified) -> dict:
    cat_totals: dict[str, float] = {}
    for exp in classified:
        cat = _get(exp, "category", "其他")
        amt_str = _get(exp, "amount", "")
        cat_totals[cat] = cat_totals.get(cat, 0) + float(amt_str or 0)
    return cat_totals


def _answer_text(a) -> str:
    if isinstance(a, list):
        return "\n".join(f"  - {item}" for item in a)
    return str(a)


def _q_text(q):
    if isinstance(q, dict):
        return q.get("text", str(q))
    return q.text if hasattr(q, "text") else str(q)


def _q_id(q):
    if isinstance(q, dict):
        return q.get("id", "")
    return q.id if hasattr(q, "id") else ""


def format_report_markdown(report: dict, classified, answers: dict, questions=None, period: str = "") -> str:
    cat_totals = _sum_by_category(classified)
    total = sum(cat_totals.values())

    q_map: dict[str, str] = {}
    if questions:
        for q in questions:
            q_map[_q_id(q)] = _q_text(q)

    lines = []
    lines.append(f"# AI 消費幸福感分析報告{'（' + period + '）' if period else ''}")
    lines.append("")

    lines.append("## 一、消費總覽")
    lines.append(f"- **本期總消費金額**：NT$ {total:,.0f}")
    lines.append(f"- 涵蓋 {len(classified)} 筆明細，分為 {len(cat_totals)} 大類別。")
    for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
        label = CATEGORY_LABELS.get(cat, cat)
        pct = f"{amt/total*100:.1f}" if total else "0.0"
        lines.append(f"  - **{label}**：NT$ {amt:,.0f}（佔比 {pct}%）")
    lines.append("")

    lines.append("## 二、幸福消費 Top 3")
    for i, item in enumerate(report.get("happy_top3", []), 1):
        lines.append(f"  {i}. {item}")
    lines.append("")

    lines.append("## 三、壓力消費 Top 3")
    for i, item in enumerate(report.get("stress_top3", []), 1):
        lines.append(f"  {i}. {item}")
    lines.append("")

    lines.append("## 四、改善建議")
    for i, item in enumerate(report.get("suggestions", []), 1):
        lines.append(f"  {i}. {item}")
    lines.append("")

    lines.append("## 五、整體總結")
    lines.append(report.get("summary", ""))
    lines.append("")

    if answers:
        lines.append("## 六、問卷回饋")
        for q_id, a in answers.items():
            q_text = q_map.get(q_id, q_id)
            lines.append(f"  **Q：** {q_text}")
            lines.append(f"  **A：** {_answer_text(a)}")
            lines.append("")

    return "\n".join(lines)


def send_email(to_email: str, report_md: str, smtp_config: dict | None = None, period: str = "") -> None:
    host = smtp_config.get("host", SMTP_HOST) if smtp_config else SMTP_HOST
    port = smtp_config.get("port", SMTP_PORT) if smtp_config else SMTP_PORT
    user = smtp_config.get("user", SMTP_USER) if smtp_config else SMTP_USER
    password = smtp_config.get("pass", SMTP_PASS) if smtp_config else SMTP_PASS

    if not user or not password:
        raise RuntimeError("SMTP 未設定，請檢查 SMTP_USER / SMTP_PASS 環境變數")

    label = f"（{period}）" if period else ""

    html_body = report_md.replace("\n", "<br>\n")
    html_body = html_body.replace("## ", "<h2>")
    import re
    html_body = re.sub(r"</h2>?$", "</h2>", html_body, flags=re.MULTILINE)
    html_body = html_body.replace("# ", "<h1>")
    html_body = re.sub(r"</h1>?$", "</h1>", html_body, flags=re.MULTILINE)
    html_body = html_body.replace("**", "<b>", 1)
    html_body = html_body.replace("**", "</b>", 1) if "**" in html_body else html_body

    # Proper markdown-to-HTML conversion for bold
    html_body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html_body)
    # convert bullet list items
    html_body = re.sub(r"^  - (.+)$", r"&nbsp;&nbsp;• \1", html_body, flags=re.MULTILINE)
    html_body = re.sub(r"^  (\d+\. .+)$", r"&nbsp;&nbsp;\1", html_body, flags=re.MULTILINE)

    msg = MIMEMultipart("alternative")
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = f"AI 消費幸福感分析報告{label}"

    plain_part = MIMEText(report_md, "plain", "utf-8")
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(plain_part)
    msg.attach(html_part)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
