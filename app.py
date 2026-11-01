"""
CV Analyzer Pro - Mini Project (single file)
Run:  streamlit run app.py
Features: Login/Sign up (email or phone + captcha), PDF/DOCX/TXT/Image upload (OCR),
step-by-step scan, score/grade/charts, mistakes + improvements, job match,
project topics, PDF/TXT/JSON download, ChatGPT-style history sidebar,
login history, SQLite database, admin panel.
"""
import os
import re
import io
import json
import time
import hmac
import random
import string
import base64
import hashlib
import sqlite3
import datetime as dt

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from fpdf import FPDF

# ------------------------------------------------------------------ optional libraries
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None
try:
    import docx
except Exception:
    docx = None
try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None
try:
    import pytesseract
except Exception:
    pytesseract = None
try:
    import fitz  # PyMuPDF, used only for scanned PDFs
except Exception:
    fitz = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "cv_analyzer.db")
ADMIN_ID = "admin@gmail.com"  # sign up with this ID to unlock the Admin panel

# ================================================================== DATABASE
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run(sql, params=(), fetch=None):
    conn = get_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, login_id TEXT UNIQUE NOT NULL,
            kind TEXT, salt TEXT, pw TEXT, role TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS logins(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ts TEXT);
        CREATE TABLE IF NOT EXISTS analyses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, filename TEXT,
            name TEXT, field TEXT, score REAL, grade TEXT, data TEXT, created TEXT);
        CREATE INDEX IF NOT EXISTS idx_logins_user ON logins(user_id);
        CREATE INDEX IF NOT EXISTS idx_an_user ON analyses(user_id);
        """
    )
    conn.commit()
    conn.close()


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()


def normalize_id(raw):
    raw = (raw or "").strip()
    if "@" in raw:
        return raw.lower()
    return re.sub(r"[^\d]", "", raw)


def valid_id(login_id):
    if "@" in login_id:
        return re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", login_id) is not None
    return 10 <= len(login_id) <= 13


def create_user(login_id, pw):
    salt = os.urandom(8).hex()
    role = "admin" if login_id == ADMIN_ID else "user"
    kind = "email" if "@" in login_id else "phone"
    try:
        run("INSERT INTO users(login_id,kind,salt,pw,role,created) VALUES(?,?,?,?,?,?)",
            (login_id, kind, salt, hash_pw(pw, salt), role, now()))
        return True
    except sqlite3.IntegrityError:
        return False


def check_login(login_id, pw):
    u = run("SELECT * FROM users WHERE login_id=?", (login_id,), "one")
    if u and hmac.compare_digest(u["pw"], hash_pw(pw, u["salt"])):
        run("INSERT INTO logins(user_id,ts) VALUES(?,?)", (u["id"], now()))
        return u
    return None


# ================================================================== KNOWLEDGE BASE
FIELDS = {
    "Information Technology": ["python", "java", "c++", "javascript", "sql", "html", "css", "react", "node.js",
        "machine learning", "data analysis", "aws", "docker", "git", "django", "flask", "power bi", "tableau", "linux"],
    "Business & Management": ["project management", "operations", "strategy", "leadership", "budgeting", "stakeholder",
        "negotiation", "business development", "agile", "scrum", "ms office", "reporting", "planning", "excel"],
    "Finance & Accounting": ["accounting", "tally", "gst", "taxation", "auditing", "financial analysis", "balance sheet",
        "sap", "bookkeeping", "payroll", "forecasting", "valuation", "excel", "budgeting"],
    "Marketing & Sales": ["seo", "social media", "content writing", "digital marketing", "google ads", "crm",
        "lead generation", "sales", "branding", "market research", "copywriting", "email marketing", "analytics"],
    "Human Resources": ["recruitment", "onboarding", "payroll", "employee engagement", "hr policies",
        "talent acquisition", "performance management", "training", "labour law", "hris"],
    "Healthcare & Medical": ["patient care", "nursing", "clinical", "diagnosis", "pharmacy", "emr", "first aid",
        "medical records", "surgery", "laboratory", "public health", "cpr"],
    "Education & Teaching": ["lesson planning", "curriculum", "classroom management", "teaching", "assessment",
        "e-learning", "mentoring", "student counselling", "pedagogy", "research"],
    "Engineering (Civil/Mech/Elec)": ["autocad", "solidworks", "staad pro", "revit", "plc", "circuit design", "cad",
        "thermodynamics", "site supervision", "estimation", "matlab", "quality control", "robotics", "hvac"],
    "Design & Creative": ["photoshop", "illustrator", "figma", "ui design", "ux", "video editing", "premiere pro",
        "after effects", "typography", "canva", "animation", "photography", "branding"],
    "Law & Compliance": ["legal research", "drafting", "contracts", "litigation", "compliance", "ipr", "arbitration",
        "corporate law", "due diligence", "legal writing"],
    "Operations & Supply Chain": ["logistics", "inventory", "procurement", "supply chain", "warehouse", "erp", "lean",
        "six sigma", "vendor management", "forecasting"],
}

JOBS = {
    "Software Developer": ["python", "java", "sql", "git", "javascript", "html"],
    "Data Analyst": ["sql", "excel", "python", "power bi", "tableau", "data analysis"],
    "Project Manager": ["project management", "agile", "scrum", "leadership", "stakeholder", "planning"],
    "Accountant": ["accounting", "tally", "gst", "taxation", "bookkeeping", "excel"],
    "Financial Analyst": ["financial analysis", "forecasting", "valuation", "excel", "budgeting"],
    "Digital Marketer": ["seo", "social media", "google ads", "digital marketing", "analytics", "content writing"],
    "Sales Executive": ["sales", "crm", "lead generation", "negotiation", "business development"],
    "HR Executive": ["recruitment", "onboarding", "talent acquisition", "employee engagement", "payroll"],
    "Staff Nurse": ["nursing", "patient care", "clinical", "first aid", "medical records"],
    "Teacher / Lecturer": ["teaching", "lesson planning", "curriculum", "classroom management", "assessment"],
    "Civil / Mechanical Engineer": ["autocad", "cad", "estimation", "site supervision", "quality control"],
    "Graphic / UI Designer": ["photoshop", "illustrator", "figma", "ui design", "typography"],
    "Legal Associate": ["legal research", "drafting", "contracts", "compliance", "litigation"],
    "Supply Chain Executive": ["logistics", "inventory", "procurement", "supply chain", "erp"],
}

PROJECTS = {
    "Information Technology": ["AI Resume Screening System", "Real-time Chat App with WebSockets",
        "Sales Forecasting Dashboard", "Expense Tracker with Login and Reports"],
    "Business & Management": ["Market Entry Strategy Report", "Process Optimisation Case Study",
        "Startup Business Plan with Financial Model", "Customer Satisfaction Survey Analysis"],
    "Finance & Accounting": ["Ratio Analysis of Listed Companies", "GST Filing Automation in Excel",
        "Personal Budget and Investment Tracker", "Cash Flow Forecasting Model"],
    "Marketing & Sales": ["SEO Audit and Growth Plan for a Local Business", "Social Media Campaign Performance Study",
        "Customer Segmentation using CRM Data", "Brand Awareness Survey"],
    "Human Resources": ["Employee Attrition Analysis", "Onboarding Process Redesign",
        "Training Needs Assessment Survey", "Recruitment Funnel Dashboard"],
    "Healthcare & Medical": ["Patient Records Management Study", "Community Health Awareness Campaign",
        "Hospital Infection Control Audit", "Medication Error Reduction Study"],
    "Education & Teaching": ["Activity-based Learning Module", "Student Performance Analytics Study",
        "E-learning Course Design", "Classroom Engagement Experiment"],
    "Engineering (Civil/Mech/Elec)": ["Cost Estimation of a Residential Building", "Solar Powered Automation System",
        "Quality Control Study on a Manufacturing Line", "Energy Audit of a Small Facility"],
    "Design & Creative": ["Brand Identity Kit for a Startup", "Mobile App UI/UX Case Study",
        "Short Animated Explainer Video", "Website Redesign Portfolio Piece"],
    "Law & Compliance": ["Contract Risk Review Checklist", "Case Law Study on Consumer Protection",
        "Compliance Calendar for an SME", "Data Privacy Policy Draft"],
    "Operations & Supply Chain": ["Inventory Optimisation using ABC Analysis", "Warehouse Layout Improvement Study",
        "Vendor Evaluation Scorecard", "Delivery Route Cost Analysis"],
    "General": ["Industry Case Study", "Process Improvement Project", "Data-driven Survey Report",
        "Personal Portfolio Website"],
}

HEADS = {
    "education": ["education", "academic", "academics", "qualification", "qualifications", "academic qualification"],
    "experience": ["experience", "work experience", "professional experience", "employment", "work history",
                   "internship", "internships", "employment history"],
    "projects": ["projects", "project", "academic projects", "personal projects", "key projects"],
    "certifications": ["certifications", "certification", "certificates", "courses", "licenses", "achievements",
                       "awards"],
    "skills": ["skills", "technical skills", "key skills", "core competencies", "skill set", "areas of expertise"],
    "summary": ["summary", "objective", "profile", "career objective", "about me", "professional summary"],
}

ACTION_VERBS = {
    "managed", "led", "built", "developed", "designed", "created", "implemented", "improved", "increased",
    "reduced", "achieved", "launched", "analyzed", "analysed", "delivered", "organized", "organised", "trained",
    "negotiated", "optimized", "optimised", "coordinated", "supervised", "established", "automated", "generated",
    "executed", "streamlined", "handled", "prepared", "conducted", "planned", "resolved", "supported", "initiated",
}
CLICHES = ["hardworking", "hard working", "team player", "go-getter", "detail oriented", "detail-oriented",
           "self motivated", "self-motivated", "result oriented", "result-oriented", "passionate", "dynamic",
           "responsible for", "quick learner", "fast learner"]
DEGREE_WORDS = r"b\.?tech|b\.?e\b|bachelor|master|mba|b\.?com|m\.?com|b\.?sc|m\.?sc|b\.?a\b|m\.?a\b|ph\.?d|diploma|12th|10th|hsc|ssc|mbbs|llb|b\.?ed"

SAMPLE_CV = """PRIYA VERMA
priya.verma@gmail.com | +91 98765 12345 | linkedin.com/in/priyaverma
SUMMARY
Digital marketing graduate with 2 years of experience in SEO, social media and paid campaigns.
EXPERIENCE
Digital Marketing Executive, BrightEdge Media, Jun 2023 - Present
- Managed social media campaigns that increased followers by 45% in 6 months
- Ran Google Ads with a monthly budget of $4000 and improved leads by 30%
- Built weekly analytics dashboards in Excel and Google Analytics for 5 clients
- Created SEO content for 40+ blog posts, growing organic traffic by 60%
- Coordinated with the sales team on CRM lead generation, generating 120+ qualified leads per quarter
- Trained 3 new team members on content planning, keyword research and reporting tools
- Reduced cost per click by 18% by restructuring ad groups and testing new copywriting variations
- Presented monthly performance reports to the management team and clients
Marketing Intern, Orbit Solutions, Jan 2023 - May 2023
- Conducted market research for 3 product launches
- Prepared email marketing campaigns reaching 10k subscribers
- Designed social media creatives using Canva and scheduled 60+ posts across three platforms
EDUCATION
MBA Marketing, Pune University, 2023
B.Com, Delhi University, 2021
SKILLS
SEO, social media, google ads, content writing, analytics, CRM, excel, email marketing, branding, market research
PROJECTS
- Brand awareness survey for a local cafe with 200 respondents; presented the final report and recommendations to the owner
- Social media growth plan for a startup that doubled engagement in 3 months using weekly content calendars and A/B tests
- Email newsletter redesign project that improved open rates from 18% to 31% across 8 campaigns
CERTIFICATIONS
Google Analytics Certification, 2023
HubSpot Content Marketing Certification, 2023
Google Ads Search Certification, 2024
"""


# ================================================================== FILE READING / OCR
class ReadError(Exception):
    pass


def setup_tesseract():
    if pytesseract is None:
        return
    for p in (os.environ.get("TESSERACT_CMD"),
              r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if p and os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break


def ocr_ready():
    if Image is None or pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image(img):
    if not ocr_ready():
        raise ReadError("Photo/scanned resumes need OCR. Install Tesseract OCR (see README) or use the "
                        "'Paste text' tab. PDF, DOCX and TXT files work without OCR.")
    img = ImageOps.autocontrast(img.convert("L"))
    if img.width < 1400:
        img = img.resize((img.width * 2, img.height * 2))
    return pytesseract.image_to_string(img)


def read_upload(uploaded):
    """Return (text, method)."""
    data = uploaded.getvalue()
    name = uploaded.name.lower()
    if name.endswith(".pdf"):
        if PdfReader is None:
            raise ReadError("pypdf is not installed. Run: pip install pypdf")
        reader = PdfReader(io.BytesIO(data))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                raise ReadError("This PDF is password protected. Please remove the password and retry.")
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
        if len(text.split()) < 30 and fitz is not None and ocr_ready():
            doc = fitz.open(stream=data, filetype="pdf")
            parts = []
            for page in list(doc)[:3]:
                pix = page.get_pixmap(dpi=200)
                parts.append(ocr_image(Image.open(io.BytesIO(pix.tobytes("png")))))
            return "\n".join(parts), "PDF (scanned, OCR)"
        return text, "PDF (text)"
    if name.endswith(".docx"):
        if docx is None:
            raise ReadError("python-docx is not installed. Run: pip install python-docx")
        d = docx.Document(io.BytesIO(data))
        lines = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                lines.append(" | ".join(c.text for c in row.cells))
        return "\n".join(lines), "Word document"
    if name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        if Image is None:
            raise ReadError("Pillow is not installed. Run: pip install pillow")
        return ocr_image(Image.open(io.BytesIO(data))), "Image (OCR)"
    return data.decode("utf-8", "ignore"), "Plain text"


# ================================================================== ANALYSIS ENGINE
def has(term, text):
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None


def extract_contact(text):
    email = (re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text) or [""])[0]
    phone = ""
    for cand in re.findall(r"\+?\d[\d\s().-]{8,16}\d", text):
        digits = re.sub(r"\D", "", cand)
        if 10 <= len(digits) <= 13:
            phone = cand.strip()
            break
    linkedin = (re.findall(r"linkedin\.com/[\w\-/%.]+", text, re.I) or [""])[0]
    github = (re.findall(r"github\.com/[\w\-/.]+", text, re.I) or [""])[0]
    name = ""
    for line in text.splitlines()[:8]:
        s = line.strip()
        if not s or "@" in s or re.search(r"\d", s) or "http" in s.lower():
            continue
        words = s.split()
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.\-']+", w) for w in words):
            if s.lower() not in ("curriculum vitae", "resume", "my resume"):
                name = s.title()
                break
    return dict(name=name, email=email, phone=phone, linkedin=linkedin, github=github)


def split_sections(text):
    sec = {k: [] for k in HEADS}
    found, cur = [], None
    for line in text.splitlines():
        key = re.sub(r"[^a-z ]", "", line.lower()).strip()
        hit = next((k for k, v in HEADS.items() if key in v), None)
        if hit and len(line.strip()) < 40:
            cur = hit
            if hit not in found:
                found.append(hit)
        elif cur and line.strip():
            sec[cur].append(line.strip())
    return {k: "\n".join(v) for k, v in sec.items()}, found


def analyze(text, source, filename, log=None, jd=""):
    """Full analysis. `log(step, detail)` is called after every scan step."""
    steps = []

    def step(title, detail, pause=0.0):
        steps.append({"step": title, "detail": detail})
        if log:
            log(title, detail)
        if pause:
            time.sleep(pause)

    text = text.replace("\r", "")
    low = text.lower()
    words_total = len(text.split())
    step("Reading file", f"{filename} read as {source}: {words_total} words found.", 0.3)
    if words_total < 30:
        raise ReadError("Very little text could be read from this file. Try a clearer file or the 'Paste text' tab.")

    c = extract_contact(text)
    found_c = [k for k in ("name", "email", "phone", "linkedin", "github") if c[k]]
    step("Extracting contact details", "Found: " + (", ".join(found_c) or "nothing"), 0.3)

    sec, found_heads = split_sections(text)
    if not sec["education"].strip():
        sec["education"] = "\n".join(l.strip() for l in text.splitlines() if re.search(DEGREE_WORDS, l, re.I))[:600]
    if not sec["certifications"].strip():
        sec["certifications"] = "\n".join(
            l.strip() for l in text.splitlines() if re.search(r"certif", l, re.I))[:600]
    step("Detecting sections", "Headings found: " + (", ".join(found_heads) or "none"), 0.3)

    hits = {f: [s for s in sk if has(s, low)] for f, sk in FIELDS.items()}
    skills = sorted({s for v in hits.values() for s in v})
    field = max(hits, key=lambda f: len(hits[f])) if skills else "General"
    step("Finding skills and best-fit field", f"{len(skills)} skills detected. Best-fit field: {field}.", 0.3)

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    bullets = [re.sub(r"^[\u2022\u25cf\-*\u25aa\u2013]\s*", "", l) for l in lines
               if re.match(r"^[\u2022\u25cf\-*\u25aa\u2013]\s*\S", l)]
    verb_lines = [b for b in bullets if b.split() and b.split()[0].lower().strip(",.") in ACTION_VERBS]
    verb_ratio = len(verb_lines) / len(bullets) if bullets else 0
    metrics = re.findall(r"\d+(?:\.\d+)?\s?%|[$\u20b9\u20ac]\s?\d[\d,]*|\b\d+\+|\b\d+[kKmM]\b", text)
    pronouns = len(re.findall(r"\b(i|my|me)\b", low))
    cliches = sorted({c_ for c_ in CLICHES if c_ in low})
    years = [float(y) for y in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", low)]
    step("Checking writing quality",
         f"{len(bullets)} bullet points, {len(metrics)} measurable results, {len(verb_lines)} strong action verbs.", 0.3)

    wc = lambda k: len(sec[k].split())
    comp = {
        "Contact": 3 * bool(c["name"]) + 3 * bool(c["email"]) + 3 * bool(c["phone"]) + 1 * bool(c["linkedin"] or c["github"]),
        "Skills": min(len(skills), 12) / 12 * 20,
        "Education": 10 if wc("education") > 3 else 0,
        "Experience": min(wc("experience"), 120) / 120 * 20,
        "Projects": min(wc("projects"), 80) / 80 * 12,
        "Certifications": min(wc("certifications"), 20) / 20 * 8,
        "Impact": min(len(metrics), 6) / 6 * 5 + min(verb_ratio, 1) * 5,
        "Format": (4 if 250 <= words_total <= 900 else 1) + (3 if len(bullets) >= 6 else 0)
                  + (2 if wc("summary") > 5 else 0) + (1 if pronouns == 0 else 0),
    }
    maxes = {"Contact": 10, "Skills": 20, "Education": 10, "Experience": 20, "Projects": 12,
             "Certifications": 8, "Impact": 10, "Format": 10}
    comp = {k: round(float(v), 1) for k, v in comp.items()}
    score = round(sum(comp.values()), 1)
    grade = next(g for t, g in [(90, "A+"), (80, "A"), (70, "B"), (60, "C"), (50, "D"), (0, "F")] if score >= t)
    step("Calculating CV score", f"Score {score}/100, grade {grade}.", 0.3)

    jobs = []
    for title, req in JOBS.items():
        got = [s for s in req if has(s, low)]
        jobs.append({"title": title, "match": round(100 * len(got) / len(req)),
                     "missing": [s for s in req if s not in got]})
    jobs = sorted(jobs, key=lambda j: -j["match"])[:6]
    step("Matching job roles", f"Best match: {jobs[0]['title']} ({jobs[0]['match']}%).", 0.3)

    ats = ats_check(text, c, found_heads, words_total, len(bullets), skills, source, jd)
    step("Running ATS check", f"ATS score {ats['score']}/100 - {ats['verdict']}.", 0.3)

    strengths = [f"Strong {k.lower()} section ({comp[k]}/{maxes[k]})" for k in comp if comp[k] >= 0.8 * maxes[k]]
    if len(metrics) >= 3:
        strengths.append(f"Uses measurable results ({len(metrics)} found)")
    if ats["score"] >= 80:
        strengths.append("Passes the ATS compatibility checks")

    # ---- mistakes
    issues = []

    def add(sev, title, detail, fix):
        issues.append({"sev": sev, "title": title, "detail": detail, "fix": fix})

    if not c["name"]:
        add("Critical", "Name not detected", "Recruiters and ATS software could not find your name at the top.",
            "Put your full name in a large font on the first line, with no title above it.")
    if not c["email"]:
        add("Critical", "Email address missing", "Employers cannot contact you without an email.",
            "Add a professional email such as firstname.lastname@gmail.com.")
    if not c["phone"]:
        add("Critical", "Phone number missing", "No valid 10-digit phone number was found.",
            "Add your mobile number with country code, e.g. +91 98XXXXXXXX.")
    if c["email"] and (len(re.findall(r"\d", c["email"].split("@")[0])) >= 4
                       or re.search(r"cool|boy|girl|king|queen|hot|sexy|baby", c["email"], re.I)):
        add("Info", "Email looks unprofessional", f"'{c['email']}' may create a poor first impression.",
            "Create a simple email using your real name.")
    if not (c["linkedin"] or c["github"]):
        add("Warning", "No LinkedIn / GitHub / portfolio link", "Online profiles build trust and show proof of work.",
            "Add your LinkedIn URL (and GitHub or portfolio if relevant) in the header.")
    missing_heads = [h for h in ("education", "experience", "skills", "projects") if h not in found_heads
                     and not sec[h].strip()]
    if missing_heads:
        add("Warning", "Missing standard sections", "Not found: " + ", ".join(missing_heads) + ".",
            "Use clear headings such as EDUCATION, EXPERIENCE, SKILLS, PROJECTS so ATS can read each part.")
    if wc("experience") == 0 and wc("projects") == 0:
        add("Critical", "No experience or projects", "Nothing shows what you have actually done.",
            "Add internships, jobs, academic projects or volunteer work with 2-4 bullet points each.")
    if len(skills) < 8:
        add("Warning", "Too few skills detected", f"Only {len(skills)} recognised skills found (aim for 8-15).",
            "Create a Skills section and list tools, software and domain skills relevant to the job.")
    if len(metrics) < 3:
        add("Warning", "No measurable achievements", "Numbers make achievements believable.",
            "Add results like 'Reduced costs by 15%' or 'Handled 40+ clients per month'.")
    if bullets and verb_ratio < 0.4:
        add("Warning", "Weak bullet points", f"Only {len(verb_lines)} of {len(bullets)} bullets start with an action verb.",
            "Start every bullet with a verb: Managed, Built, Improved, Led, Designed.")
    if len(bullets) < 6:
        add("Warning", "Few bullet points", "Dense paragraphs are hard to scan in the 6 seconds recruiters give a CV.",
            "Convert paragraphs into short bullet points (1-2 lines each).")
    if pronouns > 0:
        add("Info", "First-person words used", f"Found {pronouns} uses of I / me / my.",
            "Remove 'I' and 'my' - write bullets in an implied first person.")
    if cliches:
        add("Info", "Overused buzzwords", "Found: " + ", ".join(cliches) + ".",
            "Replace buzzwords with proof, e.g. 'Led a 5-member team to deliver the project 2 weeks early'.")
    if words_total < 250:
        add("Warning", "CV is too short", f"Only {words_total} words.", "Aim for 300-700 words (1-2 pages).")
    if words_total > 900:
        add("Warning", "CV is too long", f"{words_total} words (about {round(words_total / 500, 1)} pages).",
            "Cut older or irrelevant details. Keep it to 2 pages maximum.")
    if wc("summary") <= 5:
        add("Info", "No professional summary", "A 2-3 line summary helps recruiters understand you quickly.",
            "Add a summary: your field, years of experience or level, and your top 2-3 strengths.")
    if wc("certifications") < 3:
        add("Info", "No certifications", "Certifications prove skills and show learning habit.",
            "Add 1-3 relevant online or professional certifications with the year.")
    if ats["score"] < 60:
        add("Critical", "Likely to be rejected by ATS", f"ATS score is only {ats['score']}/100.",
            "Fix the failed checks in the ATS tab: plain-text contact details, standard headings, bullets and keywords.")
    order = {"Critical": 0, "Warning": 1, "Info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    step("Detecting mistakes", f"{len(issues)} issues found "
         f"({sum(i['sev'] == 'Critical' for i in issues)} critical).", 0.3)

    verdicts = {"A+": "Excellent CV. Ready to apply.", "A": "Very strong CV with small polish needed.",
                "B": "Good CV. Fix the warnings to stand out.", "C": "Average CV. Needs clear improvements.",
                "D": "Weak CV. Work through the critical issues first.", "F": "Needs a rewrite. Follow the action plan."}
    plan = [f"{i['title']}: {i['fix']}" for i in issues[:6]] or ["Tailor your CV to every job description."]
    examples = [("Responsible for sales", "Increased regional sales by 18% in 6 months by building a new dealer network."),
                ("Worked on website project", "Designed and launched a 5-page website used by 1,200+ monthly visitors."),
                ("Good communication skills", "Presented weekly reports to a 10-member management team.")]
    step("Preparing improvement plan", f"{len(plan)} priority actions prepared.", 0.3)

    return {
        "meta": {"filename": filename, "source": source, "created": now(), "words": words_total},
        "contact": c, "field": field, "skills": skills,
        "sections": {k: v[:2500] for k, v in sec.items()}, "found_heads": found_heads,
        "components": comp, "maxes": maxes, "score": score, "grade": grade, "verdict": verdicts[grade],
        "jobs": jobs, "ats": ats, "strengths": strengths, "issues": issues, "plan": plan, "examples": examples,
        "topics": PROJECTS.get(field, PROJECTS["General"]), "years": max(years) if years else 0,
        "stats": {"bullets": len(bullets), "metrics": len(metrics), "action_verbs": len(verb_lines),
                  "pronouns": pronouns, "cliches": len(cliches)},
        "log": steps,
    }


# ================================================================== ATS ENGINE
STOP = set("""a an the and or of to in for on with at by from as is are was were be been this that these those you your
we our they their will can may must should would could have has had not but if it its into about over under per via
etc using use work working experience years year role job candidate required requirements responsibilities skills
ability strong good knowledge looking join team company plus new more other also any all such who what when where
which how than then them being able hiring seeking opportunity preferred excellent""".split())


def jd_keywords(jd):
    jl = jd.lower()
    terms = [sk for lst in FIELDS.values() for sk in lst if has(sk, jl)]
    freq = {}
    for w in re.findall(r"[a-z][a-z+#.]{2,}", jl):
        w = w.strip(".")
        if len(w) >= 3 and w not in STOP:
            freq[w] = freq.get(w, 0) + 1
    top = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:20]]
    out = []
    for t in terms + top:
        if t not in out:
            out.append(t)
    multi = [t for t in out if " " in t]
    out = [t for t in out if " " in t or not any(t in m.split() for m in multi)]
    return out[:25]


def ats_check(text, c, found_heads, words_total, n_bullets, skills, source, jd):
    """Applicant Tracking System compatibility check (100 points)."""
    low = text.lower()
    checks = []

    def add(name, pts, mx, detail, fix):
        status = "pass" if pts >= mx * 0.8 else ("warn" if pts >= mx * 0.4 else "fail")
        checks.append({"name": name, "points": round(float(pts), 1), "max": mx, "status": status,
                       "detail": detail, "fix": fix})

    got = [k for k in ("name", "email", "phone") if c[k]]
    add("Contact details readable", 5 * len(got), 15, f"Parsed: {', '.join(got) or 'nothing'}.",
        "Keep name, email and phone as plain text at the top - not inside images, headers or text boxes.")
    ok = [h for h in ("experience", "education", "skills") if h in found_heads]
    add("Standard section headings", 5 * len(ok), 15,
        f"Recognised headings: {', '.join(ok) or 'none'} (needs experience, education, skills).",
        "Use plain headings ATS understand: EXPERIENCE, EDUCATION, SKILLS. Avoid creative names like 'My Journey'.")
    if source in ("PDF (text)", "Word document"):
        fmt, fd = 10, f"{source} - machine readable."
    elif source in ("Plain text", "Pasted text"):
        fmt, fd = 8, "Plain text is readable, but upload a PDF or DOCX when applying."
    else:
        fmt, fd = 4, f"{source} - text was recovered by OCR, which many ATS cannot do."
    add("File format", fmt, 10, fd, "Submit a text-based PDF or DOCX. Do not submit a photo, screenshot or scanned copy.")
    add("Length", 10 if 250 <= words_total <= 900 else 4, 10, f"{words_total} words.",
        "Keep the CV between 300 and 700 words (1-2 pages).")
    add("Bullet formatting", 10 if n_bullets >= 6 else 4, 10, f"{n_bullets} bullet points found.",
        "Use simple round bullets with one achievement per line.")
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    add("Dates present", 10 if len(years) >= 2 else 3, 10, f"{len(years)} year values found.",
        "Add start and end dates (e.g. Jun 2022 - Aug 2024) to every job, education and certification.")
    pipes = text.count("|") + text.count("\t")
    odd = len(re.findall(r"[^\x00-\x7F\u2022\u2013\u2014\u2019\u201c\u201d\u25cf\u25aa\u20b9\u20ac]", text))
    add("Tables / special characters", 10 if pipes <= 8 and odd <= 20 else 4, 10,
        f"{pipes} table-like separators, {odd} unusual symbols.",
        "Avoid tables, columns, icons and graphics - ATS often scramble or skip them.")
    jd_info = None
    if jd and len(jd.split()) >= 10:
        kws = jd_keywords(jd)
        found = [k for k in kws if has(k, low)]
        miss = [k for k in kws if k not in found]
        pct = round(100 * len(found) / len(kws)) if kws else 0
        jd_info = {"keywords": kws, "matched": found, "missing": miss, "percent": pct}
        add("Job description keyword match", 20 * pct / 100, 20,
            f"{len(found)} of {len(kws)} job keywords found ({pct}%).",
            "Add the missing keywords where they are truthful, in your skills and experience bullets.")
    else:
        add("Skill keyword coverage", min(len(skills), 12) / 12 * 20, 20,
            f"{len(skills)} recognised skills. Paste a job description for an exact keyword match.",
            "List 10-15 relevant skills using the same words the job advert uses.")
    score = round(sum(k["points"] for k in checks), 1)
    verdict = "ATS Friendly" if score >= 80 else ("Needs fixes" if score >= 60 else "Likely to be rejected by ATS")
    return {"score": score, "verdict": verdict, "checks": checks, "jd": jd_info}


# ================================================================== LOGOS (inline SVG, no internet needed)
APP_LOGO = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="g" x1="0" y1="0" '
            'x2="1" y2="1"><stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>'
            '</defs><rect width="64" height="64" rx="16" fill="url(#g)"/><path d="M20 12h18l8 8v30a2 2 0 0 1-2 2H20a2 2 0 '
            '0 1-2-2V14a2 2 0 0 1 2-2z" fill="#fff"/><path d="M38 12v8h8" fill="#c7d2fe"/><path d="M24 30h16M24 36h16M24 42h9" '
            'stroke="#4f46e5" stroke-width="2.5" stroke-linecap="round"/><circle cx="44" cy="44" r="9" fill="#22c55e"/>'
            '<path d="M40 44l3 3 5-6" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round" '
            'stroke-linejoin="round"/></svg>')
GMAIL_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect x="4" y="10" width="40" height="28" rx="4" '
             'fill="#fff" stroke="#e2e8f0"/><path d="M4 12v26" stroke="#4285f4" stroke-width="5"/><path d="M44 12v26" '
             'stroke="#34a853" stroke-width="5"/><path d="M5 13l19 14 19-14" fill="none" stroke="#ea4335" stroke-width="4.5"/></svg>')
PHONE_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><circle cx="24" cy="24" r="22" fill="#22c55e"/>'
             '<g transform="translate(10 10) scale(1.16)"><path fill="#fff" d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 '
             '1 0 0 1 1.02-.24 11.36 11.36 0 0 0 3.57.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 '
             '0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1.02l-2.2 2.2z"/></g></svg>')
SHIELD_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path d="M24 4l16 6v12c0 11-7 19-16 22C15 41 8 33 '
              '8 22V10z" fill="#4f46e5"/><text x="24" y="29" font-size="13" font-weight="bold" text-anchor="middle" '
              'fill="#fff" font-family="Arial">ATS</text></svg>')


GOOGLE_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 '
              '9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
              '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c'
              '4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59'
              'l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 '
              '11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 '
              '14.62 48 24 48z"/></svg>')
CHART_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="10" fill="#e0e7ff"/>'
             '<rect x="10" y="26" width="6" height="12" rx="1" fill="#4f46e5"/><rect x="21" y="18" width="6" height="20" rx="1" '
             'fill="#06b6d4"/><rect x="32" y="10" width="6" height="28" rx="1" fill="#22c55e"/></svg>')
TARGET_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><circle cx="24" cy="24" r="21" fill="#fee2e2"/>'
              '<circle cx="24" cy="24" r="14" fill="#fff"/><circle cx="24" cy="24" r="8" fill="#ef4444"/>'
              '<circle cx="24" cy="24" r="3" fill="#fff"/></svg>')
PDF_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path d="M12 4h17l9 9v29a2 2 0 0 1-2 2H12a2 2 0 0 1-2-2V6'
           'a2 2 0 0 1 2-2z" fill="#fff" stroke="#cbd5e1"/><rect x="7" y="24" width="28" height="12" rx="2" fill="#ef4444"/>'
           '<text x="21" y="33.5" font-size="9" font-weight="bold" text-anchor="middle" fill="#fff" font-family="Arial">PDF</text></svg>')


def feature_strip():
    items = [(SHIELD_SVG, "ATS Check", "Will ATS read your CV?"), (CHART_SVG, "Score & Grade", "100-point scoring"),
             (TARGET_SVG, "Job Match", "14 roles, every field"), (PDF_SVG, "PDF Report", "Download full report")]
    cards = "".join(f'<div class="feat">{svg_img(i, 44)}<b>{t}</b><small>{d}</small></div>' for i, t, d in items)
    return f'<div class="featrow">{cards}</div>'


def svg_img(svg, w=48):
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{w}" height="{w}" style="vertical-align:middle">'


def provider_row():
    return ('<div class="prov">'
            f'<span>{svg_img(GOOGLE_SVG, 24)} Gmail / Google ID</span>'
            f'<span>{svg_img(GMAIL_SVG, 26)} Any Email</span>'
            f'<span>{svg_img(PHONE_SVG, 26)} Phone number</span>'
            f'<span>{svg_img(SHIELD_SVG, 26)} ATS Ready</span></div>')


# ================================================================== REPORTS (PDF / TXT)
def safe(t):
    t = str(t).replace("\u2022", "-").replace("\u2013", "-").replace("\u2014", "-")
    t = t.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = t.encode("latin-1", "replace").decode("latin-1")
    return re.sub(r"(\S{50})(?=\S)", r"\1 ", t)


class Report(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"CV Analyzer Pro  |  Page {self.page_no()}", align="C")


def make_pdf(r):
    p = Report()
    p.set_auto_page_break(True, 16)
    p.add_page()
    p.set_fill_color(79, 70, 229)
    p.rect(0, 0, 210, 32, "F")
    p.set_fill_color(255, 255, 255)
    p.rect(10, 6, 20, 20, "F")
    p.set_draw_color(79, 70, 229)
    p.set_line_width(1.4)
    p.line(14.5, 16.5, 18.5, 21)
    p.line(18.5, 21, 26, 11)
    p.set_line_width(0.2)
    p.set_draw_color(0, 0, 0)
    p.set_xy(34, 8)
    p.set_text_color(255, 255, 255)
    p.set_font("Helvetica", "B", 20)
    p.cell(0, 10, "CV Analysis Report", new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", "", 10)
    p.set_x(34)
    p.cell(0, 6, safe(f"File: {r['meta']['filename']}   |   Generated: {r['meta']['created']}"),
           new_x="LMARGIN", new_y="NEXT")
    p.set_y(38)
    p.set_text_color(30, 30, 30)

    def head(t):
        p.ln(3)
        p.set_font("Helvetica", "B", 13)
        p.set_text_color(79, 70, 229)
        p.cell(0, 8, safe(t), new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(30, 30, 30)
        p.set_font("Helvetica", "", 10.5)

    def para(t, indent=0, rgb=(30, 30, 30)):
        p.set_x(p.l_margin + indent)
        p.set_text_color(*rgb)
        p.multi_cell(0, 6, safe(t), new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(30, 30, 30)

    c = r["contact"]
    head("Candidate")
    para(f"Name: {c['name'] or 'Not found'}\nEmail: {c['email'] or 'Not found'}\n"
         f"Phone: {c['phone'] or 'Not found'}\nBest-fit field: {r['field']}")
    head("Overall Score")
    para(f"{r['score']} / 100    Grade: {r['grade']}    ({r['verdict']})")
    y = p.get_y() + 1
    p.set_fill_color(226, 232, 240)
    p.rect(10, y, 150, 5, "F")
    p.set_fill_color(79, 70, 229)
    p.rect(10, y, 150 * min(r["score"], 100) / 100, 5, "F")
    p.set_y(y + 8)
    for k, v in r["components"].items():
        para(f"- {k}: {v} / {r['maxes'][k]}", indent=4)
    head("Skills Found")
    para(", ".join(r["skills"]) or "No recognised skills.")
    ats = r.get("ats")
    if ats:
        head("ATS Compatibility")
        para(f"ATS score: {ats['score']} / 100  -  {ats['verdict']}")
        for ck in ats["checks"]:
            para(f"[{ck['status'].upper()}] {ck['name']} ({ck['points']}/{ck['max']}): {ck['detail']}", indent=4)
        if ats.get("jd") and ats["jd"]["missing"]:
            para("Missing job keywords: " + ", ".join(ats["jd"]["missing"][:15]), indent=4)
    head("Mistakes Found")
    colors = {"Critical": (200, 30, 30), "Warning": (200, 120, 0), "Info": (60, 100, 200)}
    for i in r["issues"] or []:
        para(f"[{i['sev']}] {i['title']}", rgb=colors[i["sev"]])
        para(i["detail"], indent=4)
        para("Fix: " + i["fix"], indent=4)
        p.ln(1)
    if not r["issues"]:
        para("No major mistakes found.")
    head("Priority Action Plan")
    for n, t in enumerate(r["plan"], 1):
        para(f"{n}. {t}")
    head("Better Bullet Examples")
    for weak, strong in r["examples"]:
        para(f"Weak: {weak}", indent=4)
        para(f"Strong: {strong}", indent=4)
    head("Top Job Matches")
    for j in r["jobs"]:
        miss = (" | learn: " + ", ".join(j["missing"][:3])) if j["missing"] else ""
        para(f"- {j['title']}: {j['match']}%{miss}")
    head("Suggested Project Topics")
    for t in r["topics"]:
        para(f"- {t}")
    return bytes(p.output())


def make_txt(r):
    c = r["contact"]
    out = ["CV ANALYSIS REPORT", "=" * 40,
           f"File: {r['meta']['filename']}  |  {r['meta']['created']}",
           f"Name: {c['name']}  Email: {c['email']}  Phone: {c['phone']}",
           f"Field: {r['field']}  Score: {r['score']}/100  Grade: {r['grade']}", "", "SCORE BREAKDOWN"]
    out += [f"  {k}: {v}/{r['maxes'][k]}" for k, v in r["components"].items()]
    ats = r.get("ats")
    if ats:
        out += ["", f"ATS SCORE: {ats['score']}/100 - {ats['verdict']}"]
        out += [f"  [{k['status'].upper()}] {k['name']} ({k['points']}/{k['max']}) - {k['detail']}" for k in ats["checks"]]
    out += ["", "MISTAKES"]
    out += [f"  [{i['sev']}] {i['title']} - {i['detail']}  FIX: {i['fix']}" for i in r["issues"]]
    out += ["", "ACTION PLAN"] + [f"  {n}. {t}" for n, t in enumerate(r["plan"], 1)]
    out += ["", "JOB MATCHES"] + [f"  {j['title']}: {j['match']}%" for j in r["jobs"]]
    out += ["", "PROJECT TOPICS"] + [f"  - {t}" for t in r["topics"]]
    return "\n".join(out)


# ================================================================== UI HELPERS
CSS = """
<style>
.block-container{padding-top:2rem;max-width:1100px}
.hero{background:linear-gradient(120deg,#4f46e5,#06b6d4);padding:26px 30px;border-radius:18px;color:#fff;margin-bottom:18px}
.hero h1{margin:0;font-size:2.1rem;color:#fff}.hero p{margin:6px 0 0;font-size:1.05rem;opacity:.93;color:#fff}
.center-title{text-align:center;font-size:2.3rem;font-weight:800;margin:30px 0 4px}
.center-sub{text-align:center;opacity:.75;margin-bottom:22px;font-size:1.05rem}
.card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:14px 18px;margin-bottom:10px;color:#0f172a}
.chip{display:inline-block;background:#e0e7ff;color:#3730a3;padding:4px 12px;border-radius:20px;margin:3px;font-weight:600;font-size:.85rem}
.issue{border-radius:10px;padding:10px 14px;margin:8px 0;color:#0f172a}
.sev-Critical{background:#fee2e2;border-left:6px solid #dc2626}
.sev-Warning{background:#fef3c7;border-left:6px solid #f59e0b}
.sev-Info{background:#dbeafe;border-left:6px solid #3b82f6}
.captcha{font-family:monospace;font-size:1.8rem;letter-spacing:8px;font-weight:800;text-align:center;
 background:#eef2ff;color:#3730a3;border-radius:10px;padding:8px;border:2px dashed #818cf8;margin-bottom:6px}
.prov{display:flex;gap:10px;justify-content:center;margin:6px 0 14px;flex-wrap:wrap}
.prov span{display:flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:24px;padding:4px 14px 4px 6px;color:#0f172a;font-weight:600;font-size:.85rem}
.featrow{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:6px 0 18px}
.feat{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:14px 8px;text-align:center;color:#0f172a;display:flex;flex-direction:column;gap:4px;align-items:center}
.feat small{opacity:.7}
@media(max-width:700px){.featrow{grid-template-columns:repeat(2,1fr)}}
.sev-pass{background:#dcfce7;border-left:6px solid #16a34a}
.sev-warn{background:#fef3c7;border-left:6px solid #f59e0b}
.sev-fail{background:#fee2e2;border-left:6px solid #dc2626}
section[data-testid="stSidebar"] .stButton button{width:100%;text-align:left;justify-content:flex-start}
</style>
"""


def new_captcha():
    return "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5))


def init_state():
    for k, v in dict(user=None, view="new", result=None, result_id=None, flash=None, uk=0).items():
        st.session_state.setdefault(k, v)
    if "captcha" not in st.session_state:
        st.session_state.captcha = new_captcha()


def hero(title, sub):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def go_view(view):
    st.session_state.view = view


def open_analysis(aid):
    row = run("SELECT * FROM analyses WHERE id=? AND user_id=?", (aid, st.session_state.user["id"]), "one")
    if row:
        st.session_state.result = json.loads(row["data"])
        st.session_state.result_id = aid
        st.session_state.view = "result"


def delete_analysis(aid):
    run("DELETE FROM analyses WHERE id=? AND user_id=?", (aid, st.session_state.user["id"]))
    st.session_state.result = None
    st.session_state.result_id = None
    st.session_state.view = "new"


def logout():
    for k in ("user", "result", "result_id"):
        st.session_state[k] = None
    st.session_state.view = "new"


def style_fig(fig, h=340):
    fig.update_layout(height=h, margin=dict(l=20, r=20, t=50, b=20))
    return fig


# ================================================================== AUTH PAGE
def auth_page():
    st.markdown(f'<div style="text-align:center">{svg_img(APP_LOGO, 84)}</div>'
                '<div class="center-title">CV Analyzer Pro</div>'
                '<div class="center-sub">Log in to scan your resume, get a score, fix mistakes and download a report.</div>',
                unsafe_allow_html=True)
    st.markdown(provider_row(), unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        flash = st.session_state.flash
        if flash:
            (st.success if flash[0] == "ok" else st.error)(flash[1])
            st.session_state.flash = None
        st.markdown(f'<div class="captcha">{st.session_state.captcha}</div>', unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["🔐 Login", "📝 Sign Up"])
        for tab, kind in ((tab_in, "login"), (tab_up, "signup")):
            with tab:
                with st.form(f"form_{kind}"):
                    raw = st.text_input("Gmail / Email or Phone Number", key=f"id_{kind}")
                    pw = st.text_input("Password", type="password", key=f"pw_{kind}")
                    cap = st.text_input("Type the captcha shown above", key=f"cap_{kind}")
                    ok = st.form_submit_button("Login" if kind == "login" else "Create Account")
                if ok:
                    handle_auth(kind, raw, pw, cap)
        st.caption("Tip: use admin@gmail.com when signing up to get the Admin panel.")


def handle_auth(kind, raw, pw, cap):
    login_id = normalize_id(raw)
    good_cap = cap.strip().upper() == st.session_state.captcha
    st.session_state.captcha = new_captcha()
    if not good_cap:
        st.session_state.flash = ("err", "Wrong captcha. A new one is shown - please try again.")
    elif not valid_id(login_id):
        st.session_state.flash = ("err", "Enter a valid email address or a 10-digit phone number.")
    elif kind == "signup":
        if len(pw) < 6:
            st.session_state.flash = ("err", "Password must be at least 6 characters.")
        elif not create_user(login_id, pw):
            st.session_state.flash = ("err", "This email/phone is already registered. Please log in.")
        else:
            u = check_login(login_id, pw)
            st.session_state.user = u
            st.session_state.view = "new"
    else:
        u = check_login(login_id, pw)
        if u:
            st.session_state.user = u
            st.session_state.view = "new"
        else:
            st.session_state.flash = ("err", "Invalid login ID or password.")
    st.rerun()


# ================================================================== SIDEBAR (history like ChatGPT)
def sidebar():
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">{svg_img(APP_LOGO, 40)}'
                    '<span style="font-size:1.25rem;font-weight:800">CV Analyzer Pro</span></div>', unsafe_allow_html=True)
        st.button("➕  New Analysis", on_click=go_view, args=("new",), type="primary", key="btn_new")
        st.markdown("**Recent analyses**")
        rows = run("SELECT id,filename,name,score,grade,created FROM analyses WHERE user_id=? "
                   "ORDER BY id DESC LIMIT 30", (u["id"],), "all")
        if not rows:
            st.caption("No analyses yet. Upload your first CV!")
        for r in rows:
            label = f"📄 {(r['name'] or r['filename'])[:22]}  ·  {r['score']:.0f} ({r['grade']})"
            st.button(label, key=f"h{r['id']}", on_click=open_analysis, args=(r["id"],), help=r["created"])
        st.divider()
        st.button("🕘  Login History", on_click=go_view, args=("account",), key="btn_acc")
        if u["role"] == "admin":
            st.button("🛡  Admin Panel", on_click=go_view, args=("admin",), key="btn_admin")
        st.caption(f"Signed in as **{u['login_id']}**")
        st.button("🚪  Logout", on_click=logout, key="btn_out")


# ================================================================== PAGE: UPLOAD (first page)
def upload_page():
    st.markdown(f'<div style="text-align:center">{svg_img(APP_LOGO, 72)}</div>'
                '<div class="center-title">What CV shall we analyze today?</div>'
                '<div class="center-sub">Upload a PDF, Word file or a photo of your resume - we scan it step by step, '
                'find mistakes and show how to improve.</div>', unsafe_allow_html=True)
    who = st.session_state.user["login_id"].split("@")[0]
    st.markdown(f'<div class="center-sub" style="margin:-10px 0 14px">👋 Welcome, <b>{who}</b></div>' + feature_strip(),
                unsafe_allow_html=True)
    with st.expander("🎯 Paste a job description for ATS keyword matching (optional)"):
        jd = st.text_area("Job description", height=140, key="jd_text")
    tab_file, tab_text = st.tabs(["📎 Upload file or photo", "✍️ Paste text"])
    text, source, fname = None, "", ""
    with tab_file:
        up = st.file_uploader("Drop your resume here (PDF, DOCX, TXT, PNG, JPG, WEBP)",
                              type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "webp", "bmp"],
                              key=f"up{st.session_state.uk}")
        if up is not None and up.name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")) and Image:
            try:
                st.image(Image.open(io.BytesIO(up.getvalue())), width=320, caption="Preview")
            except Exception:
                st.warning("Preview not available for this image.")
        go_file = st.button("🔍 Analyze CV", type="primary", key="go_file")
    with tab_text:
        pasted = st.text_area("Paste your resume text", height=220, key="pasted")
        go_text = st.button("🔍 Analyze pasted text", type="primary", key="go_text")

    go_sample = st.button("✨ Try with a sample CV (no file needed)", key="go_sample")
    if not (go_file or go_text or go_sample):
        if not ocr_ready():
            st.info("ℹ️ Photo/scanned resumes need Tesseract OCR installed. PDF, DOCX, TXT and pasted text work without it.")
        return
    try:
        if go_file:
            if up is None:
                st.warning("Please choose a file first.")
                return
            fname = up.name
            with st.status("Scanning your resume...", expanded=True) as status:
                st.write("⏳ Opening file and extracting text...")
                text, source = read_upload(up)
                result = analyze(text, source, fname, log=lambda t, d: st.write(f"✅ **{t}** - {d}"), jd=jd)
                status.update(label="Scan complete!", state="complete", expanded=True)
        elif go_sample:
            fname = "Sample CV.txt"
            with st.status("Scanning your resume...", expanded=True) as status:
                result = analyze(SAMPLE_CV, "Plain text", fname, log=lambda t, d: st.write(f"✅ **{t}** - {d}"), jd=jd)
                status.update(label="Scan complete!", state="complete", expanded=True)
        else:
            if len(pasted.split()) < 30:
                st.warning("Please paste at least 30 words of resume text.")
                return
            fname = "Pasted text"
            with st.status("Scanning your resume...", expanded=True) as status:
                result = analyze(pasted, "Pasted text", fname, log=lambda t, d: st.write(f"✅ **{t}** - {d}"), jd=jd)
                status.update(label="Scan complete!", state="complete", expanded=True)
    except ReadError as e:
        st.error(str(e))
        return
    except Exception as e:  # never crash the demo
        st.error(f"Could not analyze this file: {e}")
        return
    aid = run("INSERT INTO analyses(user_id,filename,name,field,score,grade,data,created) VALUES(?,?,?,?,?,?,?,?)",
              (st.session_state.user["id"], fname, result["contact"]["name"], result["field"],
               result["score"], result["grade"], json.dumps(result), now()))
    st.session_state.result, st.session_state.result_id, st.session_state.view = result, aid, "result"
    st.session_state.uk += 1
    time.sleep(1.0)
    st.rerun()


# ================================================================== PAGE: RESULT
def result_page():
    r = st.session_state.result
    if not r:
        go_view("new")
        st.rerun()
    c = r["contact"]
    hero(f"📊 {c['name'] or 'Resume'} - {r['grade']} ({r['score']}%)",
         f"{r['verdict']}  |  File: {r['meta']['filename']}  |  Scanned: {r['meta']['created']}")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("CV Score", f"{r['score']} / 100")
    m2.metric("Percentage", f"{r['score']}%")
    m3.metric("Grade", r["grade"])
    m4.metric("Skills", len(r["skills"]))
    m5.metric("Issues", len(r["issues"]))
    m6.metric("ATS Score", f"{(r.get('ats') or {}).get('score', '-')}")
    st.progress(int(min(r["score"], 100)), text=f"CV Strength: {r['score']}%")

    t1, t_ats, t2, t3, t4, t5, t6, t7 = st.tabs(["📊 Dashboard", "🤖 ATS Check", "🧾 Extracted Data", "⚠️ Mistakes", "🚀 Improvements",
                                          "🎯 Jobs & Projects", "🔬 Scan Log", "⬇️ Download"])
    comp, maxes = r["components"], r["maxes"]
    cats = list(comp)
    with t1:
        a, b = st.columns(2)
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=r["score"], title={"text": "Overall CV Score"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#4f46e5"},
                   "steps": [{"range": [0, 50], "color": "#fee2e2"}, {"range": [50, 75], "color": "#fef9c3"},
                             {"range": [75, 100], "color": "#dcfce7"}]}))
        a.plotly_chart(style_fig(gauge))
        pct = [round(100 * comp[k] / maxes[k]) for k in cats]
        radar = go.Figure(go.Scatterpolar(r=pct + pct[:1], theta=cats + cats[:1], fill="toself",
                                          line_color="#06b6d4"))
        radar.update_layout(title="Section Strength (%)", polar=dict(radialaxis=dict(range=[0, 100])))
        b.plotly_chart(style_fig(radar))
        a2, b2 = st.columns(2)
        bar = go.Figure()
        bar.add_bar(x=cats, y=[maxes[k] for k in cats], name="Maximum", marker_color="#e2e8f0")
        bar.add_bar(x=cats, y=[comp[k] for k in cats], name="Your score", marker_color="#4f46e5")
        bar.update_layout(title="Score Breakdown (points)", barmode="overlay")
        a2.plotly_chart(style_fig(bar))
        sev = {s: sum(i["sev"] == s for i in r["issues"]) for s in ("Critical", "Warning", "Info")}
        pie = go.Figure(go.Pie(labels=list(sev), values=list(sev.values()), hole=.5,
                               marker=dict(colors=["#dc2626", "#f59e0b", "#3b82f6"])))
        pie.update_layout(title="Issues by Severity")
        b2.plotly_chart(style_fig(pie))
    with t_ats:
        ats = r.get("ats")
        if not ats:
            st.info("This older analysis was saved before the ATS check existed. Run a new analysis to see it.")
        else:
            h1, h2 = st.columns([1, 4])
            h1.markdown(f'<div style="text-align:center">{svg_img(SHIELD_SVG, 90)}</div>', unsafe_allow_html=True)
            h2.markdown(f"### ATS Score: {ats['score']} / 100 - {ats['verdict']}")
            h2.progress(int(min(ats["score"], 100)), text="ATS compatibility")
            cols = {"pass": "#16a34a", "warn": "#f59e0b", "fail": "#dc2626"}
            fig = go.Figure(go.Bar(x=[k["name"] for k in ats["checks"]],
                                   y=[round(100 * k["points"] / k["max"]) for k in ats["checks"]],
                                   marker_color=[cols[k["status"]] for k in ats["checks"]]))
            fig.update_layout(title="ATS Checks (% of points earned)", yaxis_range=[0, 100])
            st.plotly_chart(style_fig(fig))
            icons = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
            for k in ats["checks"]:
                fix = "" if k["status"] == "pass" else f"<br>🔧 <b>Fix:</b> {k['fix']}"
                st.markdown(f'<div class="issue sev-{k["status"]}"><b>{icons[k["status"]]} {k["name"]}</b> '
                            f'({k["points"]}/{k["max"]})<br>{k["detail"]}{fix}</div>', unsafe_allow_html=True)
            jdi = ats.get("jd")
            if jdi:
                st.subheader(f"Job keyword match: {jdi['percent']}%")
                st.markdown("**Matched keywords:** " + "".join(f'<span class="chip">{w}</span>' for w in jdi["matched"]),
                            unsafe_allow_html=True)
                st.markdown("**Missing keywords:** " + "".join(
                    f'<span class="chip" style="background:#fee2e2;color:#991b1b">{w}</span>' for w in jdi["missing"]),
                    unsafe_allow_html=True)
            else:
                st.info("Paste a job description on the upload page (optional box) to get an exact keyword match.")
    with t2:
        st.markdown(f'<div class="card">👤 <b>{c["name"] or "Not found"}</b> &nbsp;|&nbsp; 📧 <b>{c["email"] or "Not found"}</b>'
                    f' &nbsp;|&nbsp; 📞 <b>{c["phone"] or "Not found"}</b><br>🔗 LinkedIn: {c["linkedin"] or "Not found"}'
                    f' &nbsp;|&nbsp; GitHub: {c["github"] or "Not found"}</div>', unsafe_allow_html=True)
        st.markdown(f"**Best-fit field:** {r['field']}  |  **Years mentioned:** {r['years'] or 'Not stated'}")
        st.markdown("**Skills**")
        st.markdown("".join(f'<span class="chip">{s}</span>' for s in r["skills"]) or "No recognised skills found.")
        for label, key in (("🎓 Education", "education"), ("💼 Experience", "experience"),
                           ("🚀 Projects", "projects"), ("📜 Certifications", "certifications")):
            with st.expander(label, expanded=False):
                st.text(r["sections"].get(key) or "Not found in your CV.")
    with t3:
        if not r["issues"]:
            st.success("No major mistakes found. Great job!")
        for i in r["issues"]:
            st.markdown(f'<div class="issue sev-{i["sev"]}"><b>[{i["sev"]}] {i["title"]}</b><br>'
                        f'{i["detail"]}<br>✅ <b>Fix:</b> {i["fix"]}</div>', unsafe_allow_html=True)
    with t4:
        if r.get("strengths"):
            st.subheader("What is already good")
            for sg in r["strengths"]:
                st.markdown(f'<div class="issue sev-pass">✅ {sg}</div>', unsafe_allow_html=True)
        st.subheader("Priority action plan")
        for n, t in enumerate(r["plan"], 1):
            st.markdown(f"**{n}.** {t}")
        st.subheader("Rewrite weak bullets like this")
        for weak, strong in r["examples"]:
            st.markdown(f'<div class="card">❌ <i>{weak}</i><br>✅ <b>{strong}</b></div>', unsafe_allow_html=True)
        s = r["stats"]
        st.caption(f"Writing stats: {s['bullets']} bullets, {s['metrics']} measurable results, "
                   f"{s['action_verbs']} action-verb bullets, {s['cliches']} buzzwords.")
    with t5:
        jobs = r["jobs"]
        fig = go.Figure(go.Bar(x=[j["match"] for j in jobs][::-1], y=[j["title"] for j in jobs][::-1],
                               orientation="h", marker_color="#4f46e5"))
        fig.update_layout(title="Job Match (%)", xaxis_range=[0, 100])
        st.plotly_chart(style_fig(fig))
        for j in jobs[:3]:
            miss = ", ".join(j["missing"]) or "none - you cover everything!"
            st.markdown(f'<div class="card">🎯 <b>{j["title"]}</b> - {j["match"]}% match<br>'
                        f'Skills to add: {miss}</div>', unsafe_allow_html=True)
        st.subheader("Project topic ideas")
        for t in r["topics"]:
            st.markdown(f'<div class="card">📌 {t}</div>', unsafe_allow_html=True)
    with t6:
        st.caption("Exactly what the scanner did, step by step:")
        for n, s in enumerate(r["log"], 1):
            st.markdown(f"**Step {n}: {s['step']}**  \n{s['detail']}")
    with t7:
        base = re.sub(r"\W+", "_", (c["name"] or "CV")).strip("_") or "CV"
        d1, d2, d3 = st.columns(3)
        try:
            d1.download_button("⬇️ PDF Report", make_pdf(r), f"{base}_analysis.pdf", "application/pdf", type="primary")
        except Exception as e:  # PDF problems must never break the page
            d1.warning(f"PDF could not be built ({e}). Use the Text or JSON report.")
        d2.download_button("⬇️ Text Report", make_txt(r), f"{base}_analysis.txt", "text/plain")
        d3.download_button("⬇️ JSON Data", json.dumps(r, indent=2), f"{base}_analysis.json", "application/json")
        if st.session_state.result_id:
            st.button("🗑 Delete this analysis", on_click=delete_analysis, args=(st.session_state.result_id,))


# ================================================================== PAGE: LOGIN HISTORY
def account_page():
    u = st.session_state.user
    hero("🕘 Login History", "Your sign-in activity and all your CV analyses.")
    logins = run("SELECT ts FROM logins WHERE user_id=? ORDER BY id DESC", (u["id"],), "all")
    an = run("SELECT created,filename,field,score,grade FROM analyses WHERE user_id=? ORDER BY id DESC",
             (u["id"],), "all")
    a, b, c = st.columns(3)
    a.metric("Total logins", len(logins))
    b.metric("Last login", logins[0]["ts"] if logins else "-")
    c.metric("CVs analysed", len(an))
    if len(an) > 1:
        fig = go.Figure(go.Scatter(x=[x["created"] for x in an][::-1], y=[x["score"] for x in an][::-1],
                                   mode="lines+markers", line_color="#4f46e5"))
        fig.update_layout(title="Your CV Score Progress", yaxis_range=[0, 100])
        st.plotly_chart(style_fig(fig))
    st.subheader("Login times")
    st.dataframe(pd.DataFrame(logins, columns=["ts"]).rename(columns={"ts": "Login Time"}))
    st.subheader("Analyses")
    st.dataframe(pd.DataFrame(an, columns=["created", "filename", "field", "score", "grade"]).rename(
        columns={"created": "Date", "filename": "File", "field": "Field", "score": "Score", "grade": "Grade"}))


# ================================================================== PAGE: ADMIN
def admin_page():
    if st.session_state.user["role"] != "admin":
        st.error("Admins only.")
        return
    hero("🛡 Admin Panel", "Who logs in, how many times, and how they use the app.")
    rows = run("""SELECT u.login_id AS user, u.created AS registered,
                  (SELECT COUNT(*) FROM logins l WHERE l.user_id=u.id) AS logins,
                  (SELECT MAX(ts) FROM logins l WHERE l.user_id=u.id) AS last_login,
                  (SELECT COUNT(*) FROM analyses a WHERE a.user_id=u.id) AS analyses
                  FROM users u ORDER BY logins DESC""", (), "all")
    df = pd.DataFrame(rows, columns=["user", "registered", "logins", "last_login", "analyses"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Total users", len(df))
    m2.metric("Total logins", int(df["logins"].sum()) if len(df) else 0)
    avg = run("SELECT AVG(score) AS s FROM analyses", (), "one")["s"]
    m3.metric("Average CV score", f"{avg:.1f}" if avg else "-")
    if len(df):
        fig = go.Figure(go.Bar(x=df["user"], y=df["logins"], marker_color="#4f46e5"))
        fig.update_layout(title="Logins per User")
        st.plotly_chart(style_fig(fig))
    st.dataframe(df.rename(columns={"user": "User", "registered": "Registered", "logins": "Logins",
                                    "last_login": "Last Login", "analyses": "CVs Analysed"}))
    st.subheader("Recent login activity")
    recent = run("SELECT u.login_id AS user, l.ts AS time FROM logins l JOIN users u ON u.id=l.user_id "
                 "ORDER BY l.id DESC LIMIT 100", (), "all")
    st.dataframe(pd.DataFrame(recent, columns=["user", "time"]).rename(columns={"user": "User", "time": "Time"}))


# ================================================================== MAIN
def main():
    st.set_page_config(page_title="CV Analyzer Pro", page_icon="📄", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    init_db()
    setup_tesseract()
    init_state()
    if not st.session_state.user:
        auth_page()
        return
    sidebar()
    view = st.session_state.view
    if view == "result":
        result_page()
    elif view == "account":
        account_page()
    elif view == "admin":
        admin_page()
    else:
        upload_page()


if __name__ == "__main__":
    main()
