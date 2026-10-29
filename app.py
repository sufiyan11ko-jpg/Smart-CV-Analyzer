"""
CV Analyser - secure resume analysis app (Streamlit, single file)
Login: email or mobile + password + OTP  |  OCR for scanned PDFs/images  |  SQLite  |  PDF reports
Run: streamlit run app.py
"""
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import smtplib
import sqlite3
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta
from email.message import EmailMessage
from xml.sax.saxutils import escape

import streamlit as st

st.set_page_config(page_title="CV Analyser", page_icon="📄", layout="centered", initial_sidebar_state="auto")

# ============================== SETTINGS ==============================
DB_FILE = "cv_analyser.db"
OTP_TTL_MIN = 5            # OTP expires after 5 minutes
OTP_MAX_ATTEMPTS = 5       # wrong OTP entries allowed per OTP
OTP_COOLDOWN_SEC = 30      # minimum gap between two OTP requests
OTP_MAX_PER_HOUR = 5       # OTP requests allowed per hour per account
MAX_LOGIN_FAILS = 5        # wrong passwords before the account is locked
LOCK_MIN = 10              # lock duration in minutes
SESSION_DAYS = 3           # "stay logged in" after refresh
PBKDF2_ITERS = 200_000
MAX_OCR_PAGES = 10


def cfg(name, default=""):
    """Read a setting from environment variables or Streamlit secrets."""
    v = os.environ.get(name)
    if v:
        return str(v)
    try:
        v = st.secrets.get(name)
        if v:
            return str(v)
    except Exception:
        pass
    return default


# ============================== KNOWLEDGE BASE ==============================
INDUSTRIES = {
    "IT & Software": {
        "skills": ["python","java","c++","c#","c programming","javascript","typescript","html","css","react","angular","vue","node.js","django","flask","spring boot","sql","mysql","postgresql","mongodb","git","github","docker","kubernetes","aws","azure","linux","rest api","ci/cd","agile","scrum","junit","selenium","android","flutter","devops","responsive design","oop","data structures","algorithms"],
        "roles": {
            "Software Developer": ["python","java","javascript","git","sql","rest api","oop","data structures","agile"],
            "Frontend Developer": ["html","css","javascript","react","typescript","git","responsive design","angular"],
            "Backend Developer": ["python","java","node.js","django","flask","sql","mongodb","rest api","docker"],
            "DevOps / Cloud Engineer": ["aws","azure","docker","kubernetes","linux","ci/cd","git","devops"],
            "QA / Test Engineer": ["selenium","junit","sql","agile","python","java","git"]}},
    "Data Science & AI": {
        "skills": ["python","sql","machine learning","deep learning","nlp","computer vision","pandas","numpy","scikit-learn","tensorflow","pytorch","keras","statistics","data visualization","data analysis","power bi","tableau","excel","matplotlib","spark","hadoop","etl","feature engineering","llm","generative ai","jupyter","a/b testing","big data","data mining","regression"],
        "roles": {
            "Data Scientist": ["python","machine learning","pandas","numpy","scikit-learn","statistics","sql","deep learning"],
            "Data Analyst": ["sql","excel","power bi","tableau","python","data analysis","data visualization","statistics"],
            "ML / AI Engineer": ["python","tensorflow","pytorch","deep learning","nlp","computer vision","machine learning","llm"],
            "BI Analyst": ["power bi","tableau","sql","excel","etl","data visualization","data analysis"]}},
    "Finance & Accounting": {
        "skills": ["accounting","bookkeeping","financial analysis","financial modeling","budgeting","forecasting","auditing","taxation","gst","tally","quickbooks","sap","excel","accounts payable","accounts receivable","reconciliation","financial reporting","risk management","valuation","investment analysis","ifrs","gaap","cost accounting","payroll","compliance","treasury"],
        "roles": {
            "Accountant": ["accounting","bookkeeping","tally","gst","reconciliation","accounts payable","accounts receivable","excel"],
            "Financial Analyst": ["financial analysis","financial modeling","forecasting","budgeting","valuation","excel","financial reporting"],
            "Auditor": ["auditing","compliance","risk management","ifrs","gaap","financial reporting"],
            "Tax Consultant": ["taxation","gst","compliance","accounting","tally","financial reporting"]}},
    "Marketing & Sales": {
        "skills": ["seo","sem","content marketing","social media","google analytics","email marketing","copywriting","branding","ppc","market research","campaign management","google ads","facebook ads","crm","hubspot","lead generation","b2b sales","negotiation","cold calling","salesforce","a/b testing","public relations","influencer marketing","product marketing","business development"],
        "roles": {
            "Digital Marketer": ["seo","sem","social media","google analytics","email marketing","ppc","content marketing"],
            "SEO / Content Specialist": ["seo","content marketing","copywriting","google analytics","social media"],
            "Sales Executive": ["lead generation","negotiation","crm","b2b sales","cold calling","business development"],
            "Brand Manager": ["branding","market research","campaign management","public relations","product marketing"]}},
    "Human Resources": {
        "skills": ["recruitment","talent acquisition","onboarding","employee relations","payroll","performance management","hris","training and development","compensation","interviewing","labor law","hr policies","employee engagement","conflict resolution","workforce planning","sourcing","hr analytics","applicant tracking","succession planning","diversity and inclusion"],
        "roles": {
            "HR Executive": ["recruitment","onboarding","hr policies","employee engagement","payroll","hris"],
            "Recruiter / Talent Acquisition": ["recruitment","talent acquisition","sourcing","interviewing","applicant tracking"],
            "HR Generalist": ["employee relations","performance management","labor law","hr policies","conflict resolution"],
            "Payroll Specialist": ["payroll","compensation","hris","labor law","compliance"]}},
    "Healthcare & Pharma": {
        "skills": ["patient care","clinical research","nursing","diagnosis","pharmacology","medical coding","ehr","emr","hipaa","first aid","cpr","phlebotomy","radiology","surgery","public health","healthcare management","gmp","pharmacovigilance","medical devices","patient safety","telemedicine","anatomy","laboratory","clinical trials"],
        "roles": {
            "Clinical Research Associate": ["clinical research","clinical trials","gmp","pharmacovigilance","laboratory"],
            "Registered Nurse": ["nursing","patient care","first aid","cpr","patient safety","emr"],
            "Pharmacist": ["pharmacology","gmp","pharmacovigilance","patient care","medical devices"],
            "Healthcare Administrator": ["healthcare management","ehr","hipaa","medical coding","public health"]}},
    "Education & Training": {
        "skills": ["curriculum development","lesson planning","classroom management","teaching","tutoring","e-learning","instructional design","assessment","student counselling","lms","moodle","training delivery","mentoring","public speaking","edtech","special education","academic writing","google classroom","pedagogy","research"],
        "roles": {
            "Teacher": ["teaching","lesson planning","classroom management","assessment","pedagogy","curriculum development"],
            "Instructional Designer": ["instructional design","e-learning","lms","curriculum development","edtech"],
            "Corporate Trainer": ["training delivery","public speaking","mentoring","assessment","e-learning"],
            "Academic Counsellor": ["student counselling","mentoring","assessment","public speaking"]}},
    "Engineering (Mech / Civil / Electrical)": {
        "skills": ["autocad","solidworks","catia","ansys","matlab","plc","scada","cad","3d modeling","thermodynamics","hvac","structural analysis","staad pro","revit","estimation","surveying","circuit design","embedded systems","vlsi","robotics","iot","six sigma","lean manufacturing","quality control","project management","cnc","welding"],
        "roles": {
            "Mechanical Design Engineer": ["autocad","solidworks","catia","ansys","cad","3d modeling","thermodynamics"],
            "Civil / Site Engineer": ["autocad","staad pro","revit","estimation","surveying","structural analysis","project management"],
            "Electrical / Automation Engineer": ["plc","scada","circuit design","matlab","embedded systems","iot"],
            "Manufacturing Engineer": ["lean manufacturing","six sigma","quality control","cnc","welding","project management"]}},
    "Design & Creative": {
        "skills": ["figma","adobe photoshop","adobe illustrator","adobe xd","indesign","after effects","premiere pro","ui/ux","wireframing","prototyping","typography","branding","graphic design","motion graphics","video editing","illustration","canva","sketch","user research","design systems","blender","photography","storyboarding","color theory"],
        "roles": {
            "UI/UX Designer": ["figma","ui/ux","wireframing","prototyping","user research","design systems","adobe xd"],
            "Graphic Designer": ["adobe photoshop","adobe illustrator","indesign","typography","graphic design","branding","canva"],
            "Video Editor": ["premiere pro","after effects","video editing","storyboarding","motion graphics"],
            "Motion Designer": ["after effects","motion graphics","blender","illustration","storyboarding"]}},
    "Operations & Supply Chain": {
        "skills": ["supply chain","logistics","inventory management","procurement","vendor management","warehouse management","demand planning","erp","sap","lean","six sigma","process improvement","kpi","forecasting","quality control","project management","scheduling","shipping","import export","negotiation","mis reporting","operations management","supplier management","kaizen","5s"],
        "roles": {
            "Operations Manager": ["operations management","process improvement","kpi","project management","lean","six sigma"],
            "Supply Chain Analyst": ["supply chain","demand planning","forecasting","inventory management","erp","sap"],
            "Procurement Executive": ["procurement","vendor management","negotiation","supplier management","erp"],
            "Logistics Coordinator": ["logistics","shipping","warehouse management","import export","scheduling","inventory management"]}},
}
SOFT_SKILLS = ["communication","leadership","teamwork","problem solving","time management","critical thinking","adaptability","creativity","collaboration","presentation","analytical skills","decision making","negotiation"]
ALIASES = {r"\bnodejs\b": "node.js", r"\breact\.?js\b": "react", r"\bsklearn\b": "scikit-learn",
           r"\b(?:ms|microsoft) excel\b": "excel", r"\bpowerbi\b": "power bi", r"\bphotoshop\b": "adobe photoshop",
           r"\billustrator\b": "adobe illustrator", r"\bproblem-solving\b": "problem solving", r"\bteam work\b": "teamwork"}
ACTION_VERBS = ["developed","designed","built","created","implemented","improved","optimized","automated","led","managed","analyzed","deployed","tested","reduced","increased","achieved","collaborated","integrated","maintained","researched","launched","delivered","coordinated"]
METRIC_RE = re.compile(r"\d+\s?%|\d+\+|\$\s?\d+|₹\s?\d+")
STOPWORDS = set("""the and for are with you your our will this that from have has had not but all any can who their they them its was were been being into over under about able more most such than then also etc per job role work team join looking candidate candidates years year plus must should would could may might shall including include includes using use used within across strong good great well new responsible responsibilities requirements required preferred skills skill ability experience""".split())

# ============================== PARSING ==============================
SECTION_ALIASES = {
    "education": ["education","academic qualification","academic qualifications","academics","qualifications","academic background","educational qualification"],
    "experience": ["experience","work experience","professional experience","employment history","internship","internships","work history","internship experience","training"],
    "projects": ["projects","academic projects","personal projects","project work","key projects","major projects","project experience"],
    "skills": ["skills","technical skills","key skills","core competencies","skills & tools","technical proficiency","it skills"],
    "certifications": ["certifications","certificates","courses","training & certifications","certifications & courses"],
    "other": ["summary","objective","career objective","profile","professional summary","achievements","awards","hobbies","interests","languages","references","declaration","personal details","extracurricular","activities"],
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.I)
DEGREE_RE = re.compile(r"\b(b\.?\s?tech|m\.?\s?tech|b\.\s?e\.?|m\.\s?e\.?|bca|mca|bba|mba|b\.?\s?sc|m\.?\s?sc|b\.?\s?com|m\.?\s?com|b\.\s?a\.?|m\.\s?a\.?|ph\.?\s?d|diploma|bachelor|master|doctorate|12th|10th|hsc|ssc|intermediate|higher secondary|secondary|cbse|icse|polytechnic)\b", re.I)

def extract_email(t):
    m = EMAIL_RE.search(t); return m.group(0) if m else "Not found"

def extract_phone(t):
    for m in PHONE_RE.finditer(t):
        d = re.sub(r"\D", "", m.group(0))
        if 10 <= len(d) <= 13 and not re.fullmatch(r"(19|20)\d{2}(19|20)\d{2}", d):
            return m.group(0).strip()
    return "Not found"

def extract_name(text, email):
    skip = ("resume","curriculum","vitae","cv","profile","objective","summary","contact","address","email","phone","mobile","github","linkedin")
    for line in [l.strip() for l in text.splitlines() if l.strip()][:15]:
        if "@" in line or any(w in line.lower() for w in skip) or re.search(r"\d", line):
            continue
        words = re.sub(r"[^A-Za-z .'-]", " ", line).split()
        if 2 <= len(words) <= 4 and all(w[0].isalpha() for w in words):
            return " ".join(w.capitalize() if not w.isupper() else w for w in words)
    if email != "Not found":
        g = re.sub(r"[\d._-]+", " ", email.split("@")[0]).title().strip()
        if g:
            return g
    return "Not found"

def split_sections(text):
    lookup = {a: k for k, al in SECTION_ALIASES.items() for a in al}
    sections = {k: [] for k in SECTION_ALIASES}
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = re.sub(r"[^a-z &]", "", line.lower()).strip()
        if len(line) < 45 and key in lookup:
            cur = lookup[key]; continue
        if cur:
            sections[cur].append(line)
    return sections

def find_pattern(text, pattern):
    return re.search(r"(?<![A-Za-z0-9+#.])" + re.escape(pattern) + r"(?![A-Za-z0-9+#])", text or "", re.I)

def extract_education(text, lines):
    lines = lines[:] if lines else [l.strip() for l in text.splitlines() if DEGREE_RE.search(l)]
    return [l for l in lines if len(l) > 3][:12]

def extract_experience(lines):
    return [l for l in lines if len(l) > 3][:15]

def extract_projects(lines):
    out = []
    for line in lines:
        c = line.strip()
        if len(c) < 4:
            continue
        is_title = not c.startswith(("•", "-", "*", "●", "▪")) and len(c.split()) <= 14
        if is_title or not out:
            out.append(c.lstrip("•-*●▪ ").strip())
    return out[:10]

def extract_certifications(text, lines):
    lines = lines[:] if lines else []
    if not lines:
        for l in text.splitlines():
            if re.search(r"\b(certified|certification|certificate|course|specialization|nanodegree|bootcamp)\b", l, re.I):
                lines.append(l.strip())
    return [l.strip("•-*●▪ ") for l in lines if len(l.strip()) > 4][:12]

def extract_links(text):
    li, gh = LINKEDIN_RE.search(text), GITHUB_RE.search(text)
    return (li.group(0) if li else None, gh.group(0) if gh else None)


# ============================== OCR ==============================
def _get_tesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR library missing. Run: pip install pytesseract pillow") from exc
    if shutil.which("tesseract") is None:
        for path in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                     "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/usr/bin/tesseract"):
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
    return pytesseract

def _prepare_image(img):
    from PIL import Image, ImageOps
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    img = ImageOps.autocontrast(img.convert("L"))
    longest = max(img.size)
    if longest < 2000:
        s = 2000 / longest
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    elif longest > 5000:
        s = 5000 / longest
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    return img

def ocr_image(img):
    pytesseract = _get_tesseract()
    try:
        prepared = _prepare_image(img)
        try:
            osd = pytesseract.image_to_osd(prepared, config="--psm 0")
            m = re.search(r"Rotate:\s*(\d+)", osd)
            if m and int(m.group(1)) % 360:
                prepared = prepared.rotate(-int(m.group(1)), expand=True, fillcolor=255)
        except Exception:
            pass
        try:
            langs = set(pytesseract.get_languages(config=""))
            lang = "eng+hin" if {"eng", "hin"} <= langs else "eng"
        except Exception:
            lang = "eng"
        best = ""
        for psm in (3, 6, 4):
            t = pytesseract.image_to_string(prepared, lang=lang, config=f"--psm {psm}")
            if len(t.strip()) > len(best.strip()):
                best = t
            if len(best.strip()) >= 200:
                break
        return best
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR is not installed. Windows: UB-Mannheim installer | Linux: sudo apt install tesseract-ocr | Mac: brew install tesseract") from exc


# ============================== FILE READING ==============================
def detect_kind(file_name, b):
    """Work out the real file type from its content, so a wrong extension does not break anything."""
    lower = file_name.lower()
    if b"%PDF-" in b[:1024]:
        return "pdf"
    if b[:4] == b"\xd0\xcf\x11\xe0":
        raise RuntimeError("Old .doc files are not supported. Please save the file as DOCX or PDF.")
    if b[:2] == b"PK":
        try:
            if "word/document.xml" in zipfile.ZipFile(io.BytesIO(b)).namelist():
                return "docx"
        except Exception:
            pass
        raise RuntimeError("Unsupported file type. Please upload PDF, DOCX, TXT, JPG or PNG.")
    try:
        from PIL import Image
        Image.open(io.BytesIO(b)).verify()
        return "image"
    except Exception:
        pass
    if lower.endswith((".png", ".jpg", ".jpeg")):
        raise RuntimeError("This image could not be opened (it may be corrupt).")
    if lower.endswith((".pdf", ".docx")):
        raise RuntimeError("This file looks damaged and could not be opened.")
    if b"\x00" in b[:2000]:
        raise RuntimeError("Unsupported file type. Please upload PDF, DOCX, TXT, JPG or PNG.")
    return "txt"


def extract_text(file_name, b):
    """Return (text, ocr_used). Scanned PDFs and images are read with OCR."""
    kind = detect_kind(file_name, b)
    if kind == "txt":
        return b.decode("utf-8", errors="ignore"), False
    if kind == "docx":
        import docx
        d = docx.Document(io.BytesIO(b))
        parts = [p.text for p in d.paragraphs]
        for tb in d.tables:
            for row in tb.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts), False
    if kind == "image":
        from PIL import Image
        return ocr_image(Image.open(io.BytesIO(b))), True
    import pdfplumber  # pdf
    pages, used_ocr, ocr_error = [], False, None
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if len(t.strip()) < 30 and i < MAX_OCR_PAGES:  # scanned page -> OCR
                try:
                    t = ocr_image(page.to_image(resolution=200).original)
                    used_ocr = True
                except RuntimeError as exc:
                    ocr_error = str(exc)
                except Exception:
                    pass
            pages.append(t)
    text = "\n".join(pages)
    if len(text.strip()) < 50 and ocr_error:
        raise RuntimeError(ocr_error)
    return text, used_ocr


# ============================== ANALYSIS ==============================
def norm_text(t):
    t = (t or "").lower()
    for pat, rep in ALIASES.items():
        t = re.sub(pat, rep, t)
    return t


def keywords(text):
    return {w for w in re.findall(r"[a-z0-9+#]{4,}", (text or "").lower()) if w not in STOPWORDS and not w.isdigit()}


EDU_LEVELS = [
    ("PhD / Doctorate", r"\b(ph\.?\s?d|doctorate)\b"),
    ("Master's degree", r"\b(m\.?\s?tech|m\.\s?e\.?|mca|mba|m\.?\s?sc|m\.?\s?com|m\.\s?a\.?|master)\b"),
    ("Bachelor's degree", r"\b(b\.?\s?tech|b\.\s?e\.?|bca|bba|b\.?\s?sc|b\.?\s?com|b\.\s?a\.?|bachelor)\b"),
    ("Diploma", r"\b(diploma|polytechnic)\b"),
    ("12th / Higher Secondary", r"\b(12th|hsc|intermediate|higher secondary)\b"),
    ("10th / Secondary", r"\b(10th|ssc|secondary|cbse|icse)\b"),
]


def highest_education(lines, text):
    blob = " ".join(lines) if lines else text
    for label, pat in EDU_LEVELS:
        if re.search(pat, blob, re.I):
            return label
    return "Not found"


def score_cv(d, hard, soft, n_ind):
    bd, tips = {}, []
    c = (3 if d["name"] != "Not found" else 0) + (3 if d["email"] != "Not found" else 0) + (2 if d["phone"] != "Not found" else 0) + (2 if d["linkedin"] or d["github"] else 0)
    bd["Contact Info"] = [c, 10]
    if not (d["linkedin"] or d["github"]): tips.append("Add your LinkedIn (and GitHub / portfolio) link in the header.")
    if c < 8: tips.append("Keep your name, email and phone number clearly visible at the top.")
    ss = min(18, hard * 1.2) + min(5, n_ind * 1.25) + (2 if soft else 0)
    bd["Skills"] = [round(min(ss, 25), 1), 25]
    if hard < 8: tips.append("List at least 8-10 relevant skills / tools, grouped under a 'Skills' heading.")
    if not soft: tips.append("Add soft skills such as communication, teamwork and leadership.")
    bd["Education"] = [min(10, 4 + len(d["education"]) * 2) if d["education"] else 0, 10]
    if not d["education"]: tips.append("Add an Education section with degree, institute and year.")
    es = min(20, 8 + len(d["experience"]) * 1.2 + d["experience_years"] * 2) if d["experience"] else 0
    bd["Experience"] = [round(es, 1), 20]
    if not d["experience"]: tips.append("Add internships, training, freelance or part-time work with dates.")
    bd["Projects"] = [min(15, len(d["projects"]) * 5) if d["projects"] else 0, 15]
    if len(d["projects"]) < 3: tips.append("Add at least 3 projects with the tools used and measurable results.")
    bd["Certifications"] = [round(min(5, len(d["certifications"]) * 1.5), 1) if d["certifications"] else 0, 5]
    if not d["certifications"]: tips.append("Add relevant certifications or online courses.")
    words = len(d["text"].split())
    fmt = 10 if 250 <= words <= 900 else 6 if (150 <= words < 250 or 900 < words <= 1300) else 3
    metrics = METRIC_RE.search(d["text"])
    fmt = min(15, fmt + (2 if metrics else 0))
    av = sum(1 for v in ACTION_VERBS if find_pattern(d["text"], v))
    fmt = min(15, fmt + (3 if av >= 3 else 1 if av else 0))
    bd["Formatting & Impact"] = [fmt, 15]
    if not metrics: tips.append("Show impact with numbers, e.g. 'improved accuracy by 12%'.")
    if av < 3: tips.append("Start bullet points with action verbs like built, developed, optimized.")
    if words < 250: tips.append("Your CV looks short - add more detail about projects and achievements.")
    if words > 900: tips.append("Your CV is long - keep it concise (1-2 pages).")
    total = max(0, min(100, round(sum(v for v, _ in bd.values()))))
    return total, bd, tips


def analyze_text(text, file_name="Pasted Text", jd="", ocr_used=False):
    low = norm_text(text)
    sec = split_sections(text)
    email, phone = extract_email(text), extract_phone(text)
    li, gh = extract_links(text)
    exp_lines = extract_experience(sec["experience"])
    d = {"text": text, "name": extract_name(text, email), "email": email, "phone": phone, "linkedin": li, "github": gh,
         "education": extract_education(text, sec["education"]), "experience": exp_lines,
         "experience_years": estimate_experience_years(text, exp_lines), "projects": extract_projects(sec["projects"]),
         "certifications": extract_certifications(text, sec["certifications"])}

    found_by_ind = {name: [s for s in info["skills"] if find_pattern(low, s)] for name, info in INDUSTRIES.items()}
    ranked = sorted(found_by_ind.items(), key=lambda kv: len(kv[1]), reverse=True)
    fits = [{"industry": n, "hits": len(f), "fit": min(100, len(f) * 10)} for n, f in ranked]
    primary = ranked[0][0] if ranked and len(ranked[0][1]) > 0 else "General"
    hard = []
    for _, f in ranked:
        for s in f:
            if s not in hard:
                hard.append(s)
    soft = [s for s in SOFT_SKILLS if find_pattern(low, s)]
    n_ind = len([1 for _, f in ranked if len(f) >= 2])

    roles = []
    for name, f in ranked[:3]:
        if not f:
            continue
        for role, req in INDUSTRIES[name]["roles"].items():
            matched = [s for s in req if find_pattern(low, s)]
            roles.append({"role": role, "industry": name, "match": round(100 * len(matched) / len(req)),
                          "matched": matched, "missing": [s for s in req if s not in matched]})
    roles.sort(key=lambda r: r["match"], reverse=True)
    roles = roles[:8]

    jd_info = None
    if jd.strip():
        jl = norm_text(jd)
        jd_skills = []
        for info in INDUSTRIES.values():
            for s in info["skills"]:
                if s not in jd_skills and find_pattern(jl, s):
                    jd_skills.append(s)
        cv_kw, jd_kw = keywords(text), keywords(jd)
        overlap = round(100 * len(cv_kw & jd_kw) / len(jd_kw)) if jd_kw else 0
        matched = [s for s in jd_skills if find_pattern(low, s)]
        percent = round(100 * len(matched) / len(jd_skills)) if jd_skills else min(92, overlap * 2)
        jd_info = {"skills": jd_skills, "matched": matched, "missing": [s for s in jd_skills if s not in matched],
                   "percent": percent, "keyword_overlap": overlap,
                   "missing_keywords": sorted(jd_kw - cv_kw)[:15]}

    total, breakdown, tips = score_cv(d, len(hard), soft, n_ind)
    if roles and roles[0]["missing"]:
        tips.insert(0, f"To fit '{roles[0]['role']}' better, add: " + ", ".join(roles[0]["missing"][:5]) + ".")
    if jd_info and jd_info["missing"]:
        tips.insert(0, "Add these skills from the job description: " + ", ".join(jd_info["missing"][:6]) + ".")
    job_match = jd_info["percent"] if jd_info else (roles[0]["match"] if roles else 0)

    return {
        "file_name": file_name, "ocr_used": bool(ocr_used), "words": len(text.split()),
        "contact": {"name": d["name"], "email": email, "phone": phone, "linkedin": li, "github": gh},
        "industry": primary, "industry_fit": fits[:6], "skills": hard, "soft_skills": soft,
        "education": d["education"], "highest_education": highest_education(d["education"], text),
        "experience": exp_lines, "experience_years": d["experience_years"],
        "certifications": d["certifications"], "projects": d["projects"],
        "score": total, "breakdown": breakdown, "tips": tips, "roles": roles, "jd": jd_info,
        "job_match": job_match, "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def grade(score):
    if score >= 80: return "Excellent", "#16a34a"
    if score >= 65: return "Good", "#2563eb"
    if score >= 45: return "Average", "#d97706"
    return "Needs Work", "#dc2626"


def report_txt(a):
    c = a["contact"]
    L = ["CV ANALYSER - REPORT", "=" * 30, f"File: {a['file_name']}", f"Date: {a['created']}", "",
         f"Name: {c['name']}", f"Email: {c['email']}", f"Phone: {c['phone']}", "",
         f"CV Score: {a['score']}/100 ({grade(a['score'])[0]})", f"Industry: {a['industry']}",
         f"Job-match estimate: {a['job_match']}%", f"Highest education: {a['highest_education']}",
         f"Experience: {a['experience_years']} years", "", "Skills: " + (", ".join(a["skills"]) or "None"),
         "Soft skills: " + (", ".join(a["soft_skills"]) or "None"), "", "Score breakdown:"]
    L += [f"  {k}: {v[0]}/{v[1]}" for k, v in a["breakdown"].items()]
    L += ["", "Best matching roles:"] + [f"  - {r['role']} ({r['match']}%)" for r in a["roles"][:5]]
    L += ["", "Improvement suggestions:"] + [f"  - {t}" for t in a["tips"]]
    return "\n".join(L)


# ============================== CHARTS (matplotlib, light theme) ==============================
PURPLE, PINK, GREY = "#6e56ff", "#ff5a8a", "#e5e7eb"


def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except:
        return None


def _style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors="#374151", labelsize=8)


def chart_score(score):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(3.4, 3.2), facecolor="white")
    color = grade(score)[1]
    ax.pie([max(score, 0.01), max(100 - score, 0.01)], colors=[color, GREY], startangle=90, counterclock=False,
           wedgeprops=dict(width=0.28, edgecolor="white"))
    ax.text(0, 0.05, str(score), ha="center", va="center", fontsize=26, fontweight="bold", color="#1f2937")
    ax.text(0, -0.28, "out of 100", ha="center", va="center", fontsize=8, color="#6b7280")
    ax.set_title("CV Score", fontsize=11, color="#1f2937")
    return fig


def _hbar(labels, values, title, xmax=100, color=PURPLE, fmt="{:.0f}%", height=None):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(4.6, height or max(2.2, 0.42 * len(labels) + 0.9)), facecolor="white")
    y = list(range(len(labels)))[::-1]
    ax.barh(y, values, color=color, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8, color="#374151")
    ax.set_xlim(0, xmax * 1.18)
    for yi, v in zip(y, values):
        ax.text(v + xmax * 0.02, yi, fmt.format(v), va="center", fontsize=8, color="#374151")
    ax.set_title(title, fontsize=11, color="#1f2937", loc="left")
    _style(ax)
    fig.tight_layout()
    return fig


def chart_breakdown(breakdown):
    labels = list(breakdown.keys())
    vals = [round(100 * v[0] / v[1]) for v in breakdown.values()]
    return _hbar(labels, vals, "Score breakdown (% of maximum)")


def chart_industry(fits):
    fits = [f for f in fits if f["fit"] > 0] or fits[:1]
    return _hbar([f["industry"][:26] for f in fits], [f["fit"] for f in fits], "Industry fit", color=PINK)


def chart_roles(roles):
    roles = roles[:6] or [{"role": "No role matched", "match": 0}]
    return _hbar([r["role"][:28] for r in roles], [r["match"] for r in roles], "Role match")


def chart_trend(dates, scores):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(4.8, 2.6), facecolor="white")
    xs = list(range(len(scores)))
    ax.plot(xs, scores, marker="o", color=PURPLE, linewidth=2)
    ax.fill_between(xs, scores, color=PURPLE, alpha=0.08)
    ax.set_ylim(0, 105)
    ax.set_xticks(xs if len(xs) <= 8 else xs[:: max(1, len(xs) // 8)])
    ax.set_xticklabels([dates[i][5:10] for i in ax.get_xticks()], fontsize=7)
    ax.set_title("CV score over time", fontsize=11, color="#1f2937", loc="left")
    _style(ax)
    fig.tight_layout()
    return fig


def fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor="white", bbox_inches="tight")
    _plt().close(fig)
    return buf.getvalue()


# ============================== PDF REPORT ==============================
def pdf_safe(v):
    return str(v).encode("cp1252", "ignore").decode("cp1252")


def build_report_pdf(a):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.6*cm, bottomMargin=1.6*cm,
                            title="CV Analyser Report")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1x", parent=ss["Heading1"], textColor=colors.HexColor("#6e56ff"))
    h2 = ParagraphStyle("h2x", parent=ss["Heading2"], textColor=colors.HexColor("#6e56ff"), spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("bodyx", parent=ss["BodyText"], wordWrap="CJK", fontSize=9.5, leading=13)
    cell = ParagraphStyle("cellx", parent=body, fontSize=9, leading=11)
    head = ParagraphStyle("headx", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    P = lambda v, s=body: Paragraph(escape(pdf_safe(v)), s)

    def table(rows, widths, header=True):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#f5f3ff")])]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6e56ff")))
        t.setStyle(TableStyle(style))
        return t

    def bullets(items, empty="Not found"):
        return [P("• " + x) for x in (items or [empty])]

    c = a["contact"]
    glabel, _ = grade(a["score"])
    story = [Paragraph("CV Analyser - Analysis Report", h1), P(f"File: {a['file_name']}   |   Date: {a['created']}"), Spacer(1, 6),
             table([[P("Name", cell), P(c["name"], cell)], [P("Email", cell), P(c["email"], cell)], [P("Phone", cell), P(c["phone"], cell)],
                    [P("LinkedIn", cell), P(c["linkedin"] or "-", cell)], [P("GitHub", cell), P(c["github"] or "-", cell)],
                    [P("Industry", cell), P(a["industry"], cell)], [P("Highest education", cell), P(a["highest_education"], cell)],
                    [P("Experience", cell), P(f"{a['experience_years']} years", cell)]], [4*cm, 13.4*cm], header=False),
             Paragraph("Scores", h2), P(f"CV score: {a['score']} / 100 ({glabel})   |   Job-match estimate: {a['job_match']}%")]
    rows = [[P("Category", head), P("Score", head), P("Max", head)]] + [[P(k, cell), P(v[0], cell), P(v[1], cell)] for k, v in a["breakdown"].items()]
    story += [Spacer(1, 4), table(rows, [9*cm, 3*cm, 3*cm])]
    try:  # charts are a bonus - the report is still produced without them
        story += [Spacer(1, 8), Image(io.BytesIO(fig_png(chart_score(a["score"]))), width=5.2*cm, height=5*cm),
                  Image(io.BytesIO(fig_png(chart_breakdown(a["breakdown"]))), width=12*cm, height=5.6*cm),
                  Image(io.BytesIO(fig_png(chart_industry(a["industry_fit"]))), width=12*cm, height=5.2*cm)]
    except Exception:
        pass
    story += [Paragraph("Skills", h2), P("Detected: " + (", ".join(a["skills"]) or "None")), P("Soft skills: " + (", ".join(a["soft_skills"]) or "None")),
              Paragraph("Education", h2)] + bullets(a["education"]) + [Paragraph("Experience", h2)] + bullets(a["experience"]) + \
             [Paragraph("Certifications", h2)] + bullets(a["certifications"]) + [Paragraph("Projects", h2)] + bullets(a["projects"])
    rrows = [[P("Role", head), P("Match", head), P("Missing skills", head)]] + [[P(r["role"], cell), P(f"{r['match']}%", cell), P(", ".join(r["missing"][:6]) or "-", cell)] for r in a["roles"][:6]]
    story += [Paragraph("Best matching roles", h2), table(rrows, [6*cm, 2*cm, 9.4*cm]) if a["roles"] else P("No industry skills detected.")]
    if a["jd"]:
        j = a["jd"]
        story += [Paragraph("Job description match", h2), P(f"Match: {j['percent']}%   |   Keyword overlap: {j['keyword_overlap']}%"),
                  P("Matched skills: " + (", ".join(j["matched"]) or "-")), P("Missing skills: " + (", ".join(j["missing"]) or "-"))]
    story += [Paragraph("Improvement suggestions", h2)] + bullets(a["tips"], "Great CV! Keep it updated.")
    doc.build(story)
    return buf.getvalue()


def estimate_experience_years(text, exp_lines):
    """Years of experience: explicit '5 years' phrases or the union of dated ranges (overlaps counted once)."""
    years = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", text, re.I)]
    best = max(years) if years and max(years) < 40 else 0.0
    cy, spans = datetime.now().year, []
    for s, e in re.findall(r"((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)", "\n".join(exp_lines), re.I):
        s, e = int(s), (cy if e.lower() in ("present", "current") else int(e))
        if e >= s:
            spans.append((s, e))
    total, cur_s, cur_e = 0, None, None
    for s, e in sorted(spans):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return round(min(max(best, total), 40.0), 1)


# ============================== DATABASE ==============================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ts_after(**delta):
    return (datetime.now() + timedelta(**delta)).strftime("%Y-%m-%d %H:%M:%S")


def q(sql, args=(), one=False, commit=False, lastrowid=False):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.execute(sql, args)
        out = cur.lastrowid if lastrowid else (cur.fetchone() if one else cur.fetchall())
        if commit:
            conn.commit()
        return out
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE, mobile TEXT UNIQUE,
        password_hash TEXT NOT NULL, created_at TEXT, failed_attempts INTEGER DEFAULT 0, locked_until TEXT);
    CREATE TABLE IF NOT EXISTS otps(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, purpose TEXT, salt TEXT, code_hash TEXT,
        expires_at TEXT, attempts INTEGER DEFAULT 0, used INTEGER DEFAULT 0, created_at TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER, created_at TEXT);
    CREATE TABLE IF NOT EXISTS resume_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, file_name TEXT, industry TEXT,
        cv_score REAL, job_match REAL, ocr_used INTEGER, analysis_json TEXT, extracted_text TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, history_id INTEGER, user_id INTEGER, file_name TEXT,
        pdf BLOB, created_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_history_user ON resume_history(user_id);
    CREATE INDEX IF NOT EXISTS idx_otps_user ON otps(user_id, purpose);
    """)
    conn.execute("DELETE FROM sessions WHERE created_at < ?", (ts_after(days=-SESSION_DAYS),))
    conn.execute("DELETE FROM otps WHERE created_at < ?", (ts_after(days=-1),))
    conn.commit()
    conn.close()


init_db()

# ============================== PASSWORDS ==============================
DUMMY_HASH = "pbkdf2_sha256$200000$00112233445566778899aabbccddeeff$" + "9f35e85b6712643c09d1ab2287a0d0c9ad4262b3242b824d4abc7e1c79910a5c"


def hash_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), PBKDF2_ITERS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERS}${salt}${h}"


def verify_password(pw, stored):
    try:
        _, iters, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(iters)).hex()
        return hmac.compare_digest(calc, h)
    except Exception:
        return False


def password_problem(pw):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain both letters and numbers."
    return None


# ============================== USERS / IDENTIFIERS ==============================
EMAIL_FULL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USER_COLS = "id,name,email,mobile,password_hash,failed_attempts,locked_until"   # indexes 0..6


def normalize_mobile(s):
    d = re.sub(r"\D", "", s or "")
    return d[-10:] if 10 <= len(d) <= 15 else None


def identify(identifier):
    s = (identifier or "").strip()
    if "@" in s:
        return ("email", s.lower()) if EMAIL_FULL.match(s) else (None, None)
    m = normalize_mobile(s)
    return ("mobile", m) if m else (None, None)


def find_user(kind, value):
    col = "email" if kind == "email" else "mobile"
    return q(f"SELECT {USER_COLS} FROM users WHERE {col}=?", (value,), one=True)


def mask_contact(u):
    if u[2]:
        name, dom = u[2].split("@", 1)
        return name[:1] + "***@" + dom
    return "******" + (u[3] or "")[-4:]


# ============================== OTP ==============================
def otp_hash(salt, code):
    return hashlib.sha256((salt + code).encode()).hexdigest()


def send_email(to, subject, body):
    host, port = cfg("SMTP_HOST"), int(cfg("SMTP_PORT", "587"))
    user, pw = cfg("SMTP_USER"), cfg("SMTP_PASSWORD")
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = subject, cfg("SMTP_FROM", user), to
    m.set_content(body)
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as s:
            s.login(user, pw)
            s.send_message(m)
    else:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(m)


def send_sms(to_number, body):
    sid, token, frm = cfg("TWILIO_SID"), cfg("TWILIO_TOKEN"), cfg("TWILIO_FROM")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"To": to_number, "From": frm, "Body": body}).encode()
    req = urllib.request.Request(url, data=data)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    urllib.request.urlopen(req, timeout=15).read()


def deliver_otp(u, code):
    """Send the OTP by email or SMS. Returns 'email', 'sms' or 'demo' (OTP shown on screen)."""
    text = f"Your CV Analyser OTP is {code}. It is valid for {OTP_TTL_MIN} minutes. Do not share it with anyone."
    smtp_ok = bool(cfg("SMTP_HOST") and cfg("SMTP_USER") and cfg("SMTP_PASSWORD"))
    sms_ok = bool(cfg("TWILIO_SID") and cfg("TWILIO_TOKEN") and cfg("TWILIO_FROM"))
    if u[2] and smtp_ok:
        send_email(u[2], "Your CV Analyser OTP", text)
        return "email"
    if u[3] and sms_ok:
        send_sms(cfg("DEFAULT_COUNTRY_CODE", "+91") + u[3], text)
        return "sms"
    if cfg("OTP_DEMO_MODE", "1").lower() in ("0", "false", "no"):
        raise RuntimeError("OTP delivery is not configured for this account.")
    return "demo"


def issue_otp(u, purpose):
    """Create and send an OTP. Returns dict(ok, msg, mode, demo)."""
    uid = u[0]
    recent = q("SELECT created_at FROM otps WHERE user_id=? AND created_at>=? ORDER BY id DESC", (uid, ts_after(hours=-1)))
    if len(recent) >= OTP_MAX_PER_HOUR:
        return {"ok": False, "msg": "Too many OTP requests. Please try again after some time."}
    if recent:
        gap = (datetime.now() - datetime.strptime(recent[0][0], "%Y-%m-%d %H:%M:%S")).total_seconds()
        if gap < OTP_COOLDOWN_SEC:
            return {"ok": False, "msg": f"Please wait {int(OTP_COOLDOWN_SEC - gap) + 1}s before requesting another OTP."}
    code = f"{secrets.randbelow(10 ** 6):06d}"
    salt = secrets.token_hex(8)
    q("UPDATE otps SET used=1 WHERE user_id=? AND purpose=? AND used=0", (uid, purpose), commit=True)
    q("INSERT INTO otps(user_id,purpose,salt,code_hash,expires_at,created_at) VALUES(?,?,?,?,?,?)",
      (uid, purpose, salt, otp_hash(salt, code), ts_after(minutes=OTP_TTL_MIN), now_str()), commit=True)
    try:
        mode = deliver_otp(u, code)
    except Exception as exc:
        q("UPDATE otps SET used=1 WHERE user_id=? AND purpose=? AND used=0", (uid, purpose), commit=True)
        return {"ok": False, "msg": f"Could not send the OTP ({exc}). Please try again."}
    return {"ok": True, "mode": mode, "demo": code if mode == "demo" else None}


def verify_otp(uid, purpose, code):
    row = q("SELECT id,salt,code_hash,expires_at,attempts FROM otps WHERE user_id=? AND purpose=? AND used=0 ORDER BY id DESC LIMIT 1", (uid, purpose), one=True)
    if not row:
        return False, "No active OTP. Please request a new one."
    oid, salt, chash, exp, attempts = row
    if exp < now_str():
        q("UPDATE otps SET used=1 WHERE id=?", (oid,), commit=True)
        return False, "This OTP has expired. Please request a new one."
    if attempts >= OTP_MAX_ATTEMPTS:
        q("UPDATE otps SET used=1 WHERE id=?", (oid,), commit=True)
        return False, "Too many wrong attempts. Please request a new OTP."
    if hmac.compare_digest(otp_hash(salt, (code or "").strip()), chash):
        q("UPDATE otps SET used=1 WHERE id=?", (oid,), commit=True)
        return True, ""
    q("UPDATE otps SET attempts=attempts+1 WHERE id=?", (oid,), commit=True)
    left = OTP_MAX_ATTEMPTS - attempts - 1
    if left <= 0:
        q("UPDATE otps SET used=1 WHERE id=?", (oid,), commit=True)
        return False, "Wrong OTP. No attempts left - please request a new OTP."
    return False, f"Wrong OTP. {left} attempt(s) left."


# ============================== SESSIONS ==============================
for _k, _v in {"logged_in": False, "user_id": None, "user_name": "", "user_email": ""}.items():
    st.session_state.setdefault(_k, _v)


def token_hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


def create_session(uid):
    """Keep the login across a browser refresh using a random token in the URL (?t=...)."""
    token = secrets.token_urlsafe(24)
    q("INSERT INTO sessions(token_hash,user_id,created_at) VALUES(?,?,?)", (token_hash(token), uid, now_str()), commit=True)
    st.session_state["token"] = token
    try:
        st.query_params["t"] = token
    except Exception:
        pass


def restore_session():
    if st.session_state.get("logged_in"):
        return
    try:
        token = st.query_params.get("t")
    except Exception:
        return
    if isinstance(token, (list, tuple)):
        token = token[0] if token else None
    if not token:
        return
    row = q("SELECT u.id,u.name,u.email,u.mobile FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.created_at>=?",
            (token_hash(token), ts_after(days=-SESSION_DAYS)), one=True)
    if row:
        st.session_state.update(logged_in=True, user_id=row[0], user_name=row[1], user_email=row[2] or row[3] or "", token=token)
    else:
        try:
            st.query_params.clear()
        except Exception:
            pass


def logout():
    token = st.session_state.get("token")
    if token:
        q("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),), commit=True)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    try:
        st.query_params.clear()
    except Exception:
        pass


# ============================== HISTORY STORAGE ==============================
def save_analysis(uid, a, text, pdf):
    hid = q("INSERT INTO resume_history(user_id,file_name,industry,cv_score,job_match,ocr_used,analysis_json,extracted_text,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (uid, a["file_name"], a["industry"], a["score"], a["job_match"], 1 if a["ocr_used"] else 0, json.dumps(a), text, now_str()),
            commit=True, lastrowid=True)
    if pdf:
        q("INSERT INTO reports(history_id,user_id,file_name,pdf,created_at) VALUES(?,?,?,?,?)",
          (hid, uid, f"CV_Analyser_Report_{hid}.pdf", sqlite3.Binary(pdf), now_str()), commit=True)
    return hid


def load_report(uid, hid):
    row = q("SELECT pdf FROM reports WHERE history_id=? AND user_id=? ORDER BY id DESC LIMIT 1", (hid, uid), one=True)
    return bytes(row[0]) if row and row[0] else None

# =============================== STYLE (light theme only) ===============================
st.markdown(
    """
<style>
:root, .stApp { color-scheme: light !important; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #f8f9fb !important; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: 760px; }

/* every piece of text stays dark and readable, even if the browser is in dark mode */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] { color: #1f2937; }
[data-testid="stAlert"] * { color: #1f2937 !important; }
a { color: #4f46e5; }

.hero { background: linear-gradient(135deg, #6e56ff, #ff5a8a); border-radius: 18px; padding: 28px 22px;
        text-align: center; box-shadow: 0 10px 28px rgba(110,86,255,.28); margin-bottom: 18px; }
.hero h1 { color: #ffffff !important; font-size: 1.9rem; margin: 0; padding: 0; }
.hero p { color: #ffffff !important; opacity: .95; margin: 8px 0 0; font-size: 1rem; }
.greet { text-align: center; color: #4b5563; margin: -4px 0 12px; font-size: .95rem; }
.mobile-hint { display: none; text-align: center; color: #6b7280; font-size: .8rem; margin-bottom: 10px; }
@media (max-width: 640px) { .mobile-hint { display: block; } }

/* cards */
.st-key-upload_card, .st-key-auth_card, [data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 18px; padding: 18px 18px 8px;
    box-shadow: 0 6px 20px rgba(17,24,39,.07); }
[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }

/* inputs */
textarea, input { background: #ffffff !important; color: #111827 !important; -webkit-text-fill-color: #111827 !important; }
::placeholder { color: #9ca3af !important; -webkit-text-fill-color: #9ca3af !important; opacity: 1; }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"] { background: #ffffff !important; border-color: #d1d5db !important; }
[data-baseweb="select"] > div { background: #ffffff !important; border-color: #d1d5db !important; }
[data-baseweb="select"] *, [data-baseweb="popover"] *, [data-baseweb="menu"] * { color: #111827 !important; }
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #ffffff !important; }
li[role="option"]:hover { background: #eef0ff !important; }
[data-testid="stFileUploaderDropzone"] { background: #f3f4f6 !important; border: 1px dashed #9ca3af; }
[data-testid="stFileUploaderDropzone"] * { color: #374151 !important; }
[data-testid="stFileUploaderDropzone"] [data-testid^="stBaseButton"] { background: #ffffff !important; border: 1px solid #d1d5db !important; box-shadow: none; }
[data-testid="stExpander"] { background: #ffffff !important; border: 1px solid #e5e7eb !important; border-radius: 14px; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: #1f2937 !important; }

/* buttons */
.stButton, .stFormSubmitButton, .stDownloadButton { width: 100%; }
[data-testid^="stBaseButton"] { width: 100%; border-radius: 14px; font-weight: 800; padding: .6rem 1rem; border: none;
    background: linear-gradient(135deg, #6e56ff, #8b6bff) !important; box-shadow: 0 8px 18px rgba(110,86,255,.3); }
[data-testid^="stBaseButton"], [data-testid^="stBaseButton"] * { color: #ffffff !important; }
[data-testid="stFileUploaderDropzone"] [data-testid^="stBaseButton"], [data-testid="stFileUploaderDropzone"] [data-testid^="stBaseButton"] * { color: #374151 !important; }

/* sidebar (shown only after login) */
[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e5e7eb; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div { color: #1f2937; }

/* tabs, metrics */
.stTabs [data-baseweb="tab"] p { color: #374151 !important; }
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: #1f2937 !important; }

/* custom blocks */
.mbox { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px 8px; text-align: center;
        box-shadow: 0 4px 14px rgba(17,24,39,.06); margin-bottom: 10px; }
.mbox .v { font-size: 1.8rem; font-weight: 800; color: #6e56ff; }
.mbox .l { font-size: .85rem; color: #6b7280; font-weight: 600; }
.panel { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 14px 16px; margin-bottom: 12px; }
.panel h4 { margin: 0 0 8px; }
code { background: #eef0ff !important; color: #4f46e5 !important; padding: 3px 8px; border-radius: 8px; margin: 2px; display: inline-block; font-size: .85rem; }
.chip { display: inline-block; padding: 4px 11px; margin: 3px; border-radius: 999px; background: #eef0ff; border: 1px solid #c9c2ff; color: #3b2fb0 !important; font-size: .82rem; }
.chip.ok { background: #e8f8ee; border-color: #a7e3bd; color: #166534 !important; }
.chip.miss { background: #fdecec; border-color: #f5b5b5; color: #991b1b !important; }
.tbl-wrap { overflow-x: auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; margin-bottom: 14px; }
.tbl { width: 100%; border-collapse: collapse; font-size: .88rem; }
.tbl th { background: #eef0ff; color: #3b2fb0; text-align: left; padding: 9px 12px; white-space: nowrap; }
.tbl td { padding: 9px 12px; border-top: 1px solid #eef0f4; color: #1f2937; white-space: nowrap; }
.foot { text-align: center; color: #6b7280; font-size: .85rem; margin-top: 28px; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================== UI HELPERS ==============================
def footer():
    st.markdown('<div class="foot">Made with ❤️ for Students | Visible in Light &amp; Dark Theme</div>', unsafe_allow_html=True)


def make_card(key):
    try:
        return st.container(key=key)
    except TypeError:  # older Streamlit versions
        return st.container(border=True)


def mbox(col, label, value):
    col.markdown(f'<div class="mbox"><div class="v">{escape(str(value))}</div><div class="l">{escape(label)}</div></div>', unsafe_allow_html=True)


def chips(items, cls=""):
    return "".join(f'<span class="chip {cls}">{escape(str(i))}</span>' for i in items) or "—"


def bullets_html(items, empty="Not found"):
    return "".join(f"<div>• {escape(str(x))}</div>" for x in items) or f"<div>{empty}</div>"


def show_fig(fig):
    try:
        st.pyplot(fig)
    except Exception:
        st.info("Chart could not be displayed.")
    finally:
        try:
            _plt().close(fig)
        except Exception:
            pass


def render_analysis(a, key, pdf=None):
    """The full dashboard for one analysed resume (used on the Analyze, Dashboard and History pages)."""
    glabel, _ = grade(a["score"])
    if pdf is None:
        try:
            pdf = build_report_pdf(a)
        except Exception:
            pdf = None
    d1, d2 = st.columns(2)
    if pdf:
        d1.download_button("⬇️ PDF Report", pdf, file_name="CV_Analyser_Report.pdf", mime="application/pdf", key=f"pdf_{key}")
    d2.download_button("⬇️ TXT Report", report_txt(a), file_name="CV_Analyser_Report.txt", mime="text/plain", key=f"txt_{key}")

    t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "🧩 Details", "💼 Roles & Job Match", "💡 Suggestions"])

    with t1:
        cols = st.columns(4)
        for col, (lab, val) in zip(cols, [("CV Score", f"{a['score']}/100"), ("Job Match", f"{a['job_match']}%"),
                                          ("Skills Found", len(a["skills"])), ("Experience", f"{a['experience_years']} yrs")]):
            mbox(col, lab, val)
        st.progress(max(0.0, min(1.0, a["score"] / 100)))
        extra = " · 🔍 OCR used" if a.get("ocr_used") else ""
        st.markdown(f'<div class="panel"><b>Industry:</b> {escape(a["industry"])} · <b>Rating:</b> {glabel} · '
                    f'<b>Education:</b> {escape(a["highest_education"])}{extra}</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            show_fig(chart_score(a["score"]))
        with g2:
            show_fig(chart_breakdown(a["breakdown"]))
        show_fig(chart_industry(a["industry_fit"]))

    with t2:
        c = a["contact"]
        info = (f"<div><b>Name:</b> {escape(c['name'])}</div><div><b>Email:</b> {escape(c['email'])}</div>"
                f"<div><b>Phone:</b> {escape(c['phone'])}</div><div><b>LinkedIn:</b> {escape(c['linkedin'] or '-')}</div>"
                f"<div><b>GitHub:</b> {escape(c['github'] or '-')}</div>")
        st.markdown(f'<div class="panel"><h4>👤 Candidate</h4>{info}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="panel"><h4>🧠 Skills ({escape(a["industry"])})</h4>{chips(a["skills"])}'
                    f'<div style="margin-top:8px"><b>Soft skills:</b> {chips(a["soft_skills"])}</div></div>', unsafe_allow_html=True)
        for title, items in [(f"🎓 Education ({escape(a['highest_education'])})", a["education"]),
                             (f"💼 Experience ({a['experience_years']} yrs)", a["experience"]),
                             ("📜 Certifications", a["certifications"]), ("🚀 Projects", a["projects"])]:
            st.markdown(f'<div class="panel"><h4>{title}</h4>{bullets_html(items)}</div>', unsafe_allow_html=True)

    with t3:
        show_fig(chart_roles(a["roles"]))
        if not a["roles"]:
            st.info("No industry-specific skills were detected, so roles could not be matched. Add a clear Skills section.")
        for i, r in enumerate(a["roles"][:6]):
            with st.expander(f"{r['role']} — {r['match']}% match ({r['industry']})", expanded=(i == 0)):
                st.progress(max(0.0, min(1.0, r["match"] / 100)))
                st.markdown(f"**Matched skills:** {chips(r['matched'], 'ok')}", unsafe_allow_html=True)
                st.markdown(f"**Skills to learn:** {chips(r['missing'], 'miss')}", unsafe_allow_html=True)
        j = a.get("jd")
        if j:
            st.markdown("### 🎯 Job Description Match")
            st.progress(max(0.0, min(1.0, j["percent"] / 100)))
            (st.success if j["percent"] > 75 else st.warning)(f"Your resume matches {j['percent']}% of the job description (keyword overlap {j['keyword_overlap']}%).")
            st.markdown(f"**Matched:** {chips(j['matched'], 'ok')}", unsafe_allow_html=True)
            st.markdown(f"**Missing:** {chips(j['missing'], 'miss')}", unsafe_allow_html=True)
            if j["missing_keywords"]:
                st.markdown(f"**Other missing keywords:** {chips(j['missing_keywords'], 'miss')}", unsafe_allow_html=True)

    with t4:
        st.markdown(f'<div class="panel"><h4>💡 Improvement Suggestions</h4>{bullets_html(a["tips"], "Great CV! Keep it updated.")}</div>', unsafe_allow_html=True)
        st.markdown("**Score breakdown**")
        for cat, (val, mx) in a["breakdown"].items():
            st.write(f"{cat} — {val}/{mx}")
            st.progress(max(0.0, min(1.0, float(val) / mx)))


# ============================== AUTH PAGES ==============================
def auth_state():
    return st.session_state.get("auth")


def start_login(identifier, password):
    """Step 1 of login: check the password, then send an OTP. Returns an error message or None."""
    kind, val = identify(identifier)
    if not kind or not password:
        return "Please enter your email / mobile number and your password."
    u = find_user(kind, val)
    if not u:
        verify_password(password, DUMMY_HASH)          # same timing for unknown accounts
        return "Invalid credentials."
    if u[6] and u[6] > now_str():
        mins = max(1, int((datetime.strptime(u[6], "%Y-%m-%d %H:%M:%S") - datetime.now()).total_seconds() // 60) + 1)
        return f"Account temporarily locked after too many wrong passwords. Try again in about {mins} min."
    if not verify_password(password, u[4]):
        fails = (u[5] or 0) + 1
        if fails >= MAX_LOGIN_FAILS:
            q("UPDATE users SET failed_attempts=0, locked_until=? WHERE id=?", (ts_after(minutes=LOCK_MIN), u[0]), commit=True)
            return f"Too many wrong attempts. The account is locked for {LOCK_MIN} minutes."
        q("UPDATE users SET failed_attempts=? WHERE id=?", (fails, u[0]), commit=True)
        return f"Invalid credentials. {MAX_LOGIN_FAILS - fails} attempt(s) left."
    q("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=?", (u[0],), commit=True)
    return begin_otp(u, "login", "login")


def begin_otp(u, purpose, flow):
    res = issue_otp(u, purpose)
    if not res["ok"]:
        return res["msg"]
    st.session_state["auth"] = {"flow": flow, "uid": u[0], "stage": "otp", "demo": res.get("demo"), "mode": res["mode"], "dest": mask_contact(u)}
    st.rerun()


def otp_screen(auth):
    u = q(f"SELECT {USER_COLS} FROM users WHERE id=?", (auth["uid"],), one=True)
    if not u:
        st.session_state.pop("auth", None)
        st.rerun()
    purpose = "login" if auth["flow"] == "login" else "reset"
    st.markdown("### 🔐 Verify OTP")
    if auth["mode"] == "demo":
        st.warning(f"Demo mode: SMS/email is not configured, so the OTP is shown here: **{auth['demo']}**")
    else:
        st.info(f"A 6-digit OTP was sent to {auth['dest']}. It is valid for {OTP_TTL_MIN} minutes.")
    with st.form("otp_form"):
        code = st.text_input("Enter OTP", max_chars=6, key="otp_code", placeholder="6-digit code")
        ok = st.form_submit_button("Verify OTP", type="primary")
    if ok:
        good, msg = verify_otp(auth["uid"], purpose, code)
        if not good:
            st.error(msg)
        elif auth["flow"] == "login":
            st.session_state.update(logged_in=True, user_id=u[0], user_name=u[1], user_email=u[2] or u[3] or "")
            st.session_state.pop("auth", None)
            create_session(u[0])
            st.rerun()
        else:
            auth["stage"] = "newpass"
            auth["demo"] = None
            st.session_state["auth"] = auth
            st.rerun()
    c1, c2 = st.columns(2)
    if c1.button("🔁 Resend OTP", key="b_resend"):
        res = issue_otp(u, purpose)
        if res["ok"]:
            auth.update(demo=res.get("demo"), mode=res["mode"])
            st.session_state["auth"] = auth
            st.rerun()
        else:
            st.error(res["msg"])
    if c2.button("⬅ Back", key="b_back"):
        st.session_state.pop("auth", None)
        st.rerun()


def new_password_screen(auth):
    st.markdown("### 🔑 Set a new password")
    with st.form("newpass_form"):
        p1 = st.text_input("New password (min 8 characters, letters + numbers)", type="password", key="np1")
        p2 = st.text_input("Confirm new password", type="password", key="np2")
        ok = st.form_submit_button("Update Password", type="primary")
    if ok:
        problem = password_problem(p1)
        if problem:
            st.error(problem)
        elif p1 != p2:
            st.error("Passwords do not match.")
        else:
            q("UPDATE users SET password_hash=?, failed_attempts=0, locked_until=NULL WHERE id=?", (hash_password(p1), auth["uid"]), commit=True)
            q("DELETE FROM sessions WHERE user_id=?", (auth["uid"],), commit=True)
            st.session_state.pop("auth", None)
            st.session_state["flash"] = "✅ Password updated. Please log in with your new password."
            st.rerun()


def login_page():
    flash = st.session_state.pop("flash", None)
    with make_card("auth_card"):
        auth = auth_state()
        if auth and auth["stage"] == "otp":
            otp_screen(auth)
            return
        if auth and auth["stage"] == "newpass":
            new_password_screen(auth)
            return
        if flash:
            st.success(flash)
        t1, t2, t3 = st.tabs(["🔐 Login", "📝 Sign Up", "🔑 Forgot Password"])
        with t1:
            with st.form("login_form"):
                ident = st.text_input("Email or mobile number", key="li", placeholder="you@example.com or 9876543210")
                pw = st.text_input("Password", type="password", key="lp")
                go = st.form_submit_button("Login & send OTP", type="primary")
            if go:
                err = start_login(ident, pw)
                if err:
                    st.error(err)
        with t2:
            with st.form("signup_form"):
                name = st.text_input("Full Name", key="sn")
                email = st.text_input("Email (optional if you give a mobile number)", key="se")
                mobile = st.text_input("Mobile number (optional if you give an email)", key="sm")
                p1 = st.text_input("Password (min 8 characters, letters + numbers)", type="password", key="sp1")
                p2 = st.text_input("Confirm Password", type="password", key="sp2")
                go2 = st.form_submit_button("Create Account", type="primary")
            if go2:
                email, mob = email.strip().lower(), (normalize_mobile(mobile) if mobile.strip() else None)
                if not name.strip():
                    st.error("Please enter your name.")
                elif not email and not mob:
                    st.error("Please enter an email or a valid mobile number.")
                elif email and not EMAIL_FULL.match(email):
                    st.error("Invalid email address.")
                elif mobile.strip() and not mob:
                    st.error("Invalid mobile number (10 digits expected).")
                elif password_problem(p1):
                    st.error(password_problem(p1))
                elif p1 != p2:
                    st.error("Passwords do not match.")
                elif (email and q("SELECT id FROM users WHERE email=?", (email,), one=True)) or (mob and q("SELECT id FROM users WHERE mobile=?", (mob,), one=True)):
                    st.error("An account with this email or mobile already exists. Please log in.")
                else:
                    q("INSERT INTO users(name,email,mobile,password_hash,created_at) VALUES(?,?,?,?,?)",
                      (name.strip(), email or None, mob, hash_password(p1), datetime.now().strftime("%Y-%m-%d")), commit=True)
                    st.success("✅ Account created! Now use the Login tab - you will receive an OTP to verify.")
        with t3:
            with st.form("reset_form"):
                ident2 = st.text_input("Registered email or mobile number", key="fi")
                go3 = st.form_submit_button("Send OTP", type="primary")
            if go3:
                kind, val = identify(ident2)
                u = find_user(kind, val) if kind else None
                if not u:
                    st.error("No account found with these details.")
                else:
                    err = begin_otp(u, "reset", "reset")
                    if err:
                        st.error(err)


# ============================== PAGE: ANALYZE ==============================
def page_analyze(uid):
    with make_card("upload_card"):
        st.markdown("### 📤 Upload Resume")
        mode = st.radio("Input method", ["Upload File", "Paste Text"], horizontal=True, label_visibility="collapsed")
        uploaded, pasted = None, ""
        if mode == "Upload File":
            uploaded = st.file_uploader("Upload resume", type=["pdf", "docx", "txt", "jpg", "jpeg", "png"], label_visibility="collapsed")
            st.caption("PDF, DOCX, TXT, JPG, PNG — scanned PDFs and photos are read with OCR.")
            if uploaded is not None:
                st.success(f"✅ Uploaded: {uploaded.name}")
        else:
            pasted = st.text_area("Paste resume text", height=250, label_visibility="collapsed", placeholder="Paste your resume text here...")
        st.markdown("### 💼 Job Description (Optional)")
        jd_text = st.text_area("Job description", height=120, label_visibility="collapsed", placeholder="Paste a job description to get a job-match score...")
        go = st.button("🔍 Analyze Resume Now", type="primary")

    if go:
        st.session_state.pop("result", None)
        text, fname, ocr, failed = "", "Pasted Text", False, False
        try:
            if mode == "Upload File":
                if uploaded is None:
                    st.warning("Please upload a resume file first, or switch to Paste Text.")
                    failed = True
                else:
                    fname = uploaded.name
                    with st.spinner("Reading your file (OCR may take a few seconds)..."):
                        text, ocr = extract_text(uploaded.name, uploaded.getvalue())
            else:
                text = pasted
                if not text.strip():
                    st.warning("Please paste your resume text first.")
                    failed = True
        except Exception as exc:
            st.error(f"❌ Could not read the file: {exc} You can also use **Paste Text**.")
            failed = True
        if failed:
            pass
        elif len(text.strip()) < 30:
            st.error("❌ Not enough readable text found in this file. Try a clearer scan / photo, or use **Paste Text**.")
        else:
            with st.spinner("Analysing..."):
                a = analyze_text(text, fname, jd_text, ocr)
                try:
                    pdf = build_report_pdf(a)
                except Exception:
                    pdf = None
                save_analysis(uid, a, text, pdf)
            st.session_state["result"] = {"a": a, "pdf": pdf, "text": text}
            st.session_state["saved_msg"] = True

    res = st.session_state.get("result")
    if res:
        if st.session_state.pop("saved_msg", False):
            st.success("✅ Analysis complete and saved to History")
        with st.expander("📄 View Extracted Text"):
            st.text(res["text"][:6000])
        render_analysis(res["a"], "cur", res["pdf"])


# ============================== PAGE: DASHBOARD ==============================
def page_dashboard(uid):
    st.markdown("## 📊 Dashboard")
    rows = q("SELECT id,created_at,cv_score,job_match,industry FROM resume_history WHERE user_id=? ORDER BY id", (uid,))
    if not rows:
        st.info("No resumes analysed yet. Open **Analyze Resume** and upload your CV!")
        return
    scores = [r[2] for r in rows]
    c1, c2, c3, c4 = st.columns(4)
    mbox(c1, "Total Scans", len(rows)); mbox(c2, "Average Score", f"{sum(scores) / len(scores):.0f}")
    mbox(c3, "Best Score", f"{max(scores):.0f}"); mbox(c4, "Latest Job Match", f"{rows[-1][3]:.0f}%")
    if len(rows) >= 2:
        show_fig(chart_trend([r[1] for r in rows], scores))
    st.markdown("### 🕒 Latest analysis")
    row = q("SELECT analysis_json FROM resume_history WHERE id=? AND user_id=?", (rows[-1][0], uid), one=True)
    try:
        a = json.loads(row[0])
    except Exception:
        st.info("The latest record could not be displayed.")
        return
    render_analysis(a, "dash", load_report(uid, rows[-1][0]))


# ============================== PAGE: HISTORY ==============================
def page_history(uid):
    st.markdown("## 📚 History / My Resumes")
    rows = q("SELECT id,created_at,file_name,industry,cv_score,job_match,ocr_used FROM resume_history WHERE user_id=?", (uid,))
    m1, m2, m3 = st.columns(3)
    mbox(m1, "Total Scans", len(rows))
    mbox(m2, "Average Score", f"{sum(r[4] for r in rows) / len(rows):.0f}" if rows else "0")
    best = {}
    for r in rows:
        best.setdefault(r[3], []).append(r[4])
    mbox(m3, "Best Industry", max(best, key=lambda k: sum(best[k]) / len(best[k]))[:18] if best else "N/A")
    if not rows:
        st.info("No resumes analysed yet. Open **Analyze Resume** to start!")
        return
    search = st.text_input("🔎 Search by file name or industry").strip().lower()
    f1, f2 = st.columns(2)
    industry = f1.selectbox("Industry", ["All"] + sorted({r[3] for r in rows if r[3]}))
    sort = f2.selectbox("Sort by", ["Date (Newest)", "Date (Oldest)", "Score (High)", "Score (Low)"])
    if search:
        rows = [r for r in rows if search in (r[2] or "").lower() or search in (r[3] or "").lower()]
    if industry != "All":
        rows = [r for r in rows if r[3] == industry]
    keyf = {"Date (Newest)": lambda r: (r[1], r[0]), "Date (Oldest)": lambda r: (r[1], r[0]), "Score (High)": lambda r: r[4], "Score (Low)": lambda r: r[4]}[sort]
    rows = sorted(rows, key=keyf, reverse=sort in ("Date (Newest)", "Score (High)"))
    rows = rows[:60]
    body = "".join(f"<tr><td>{escape(str(r[1]))[:16]}</td><td>{escape(str(r[2]))}</td><td>{escape(str(r[3]))}</td><td>{r[4]:.0f}</td><td>{r[5]:.0f}%</td></tr>" for r in rows)
    st.markdown(f'<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Date</th><th>File</th><th>Industry</th><th>CV Score</th><th>Job Match</th></tr></thead><tbody>{body}</tbody></table></div>', unsafe_allow_html=True)

    st.markdown("### 📂 Records")
    for r in rows:
        rid = r[0]
        ci, cv, cd, cp = st.columns([3, 1, 1, 1])
        ci.markdown(f"**{escape(str(r[2]))}**  \n{escape(str(r[3]))} · {r[4]:.0f}/100 · {escape(str(r[1]))[:16]}")
        if cv.button("👁️ View", key=f"v{rid}"):
            st.session_state["view_id"] = None if st.session_state.get("view_id") == rid else rid
            st.rerun()
        if cd.button("🗑️ Delete", key=f"x{rid}"):
            q("DELETE FROM reports WHERE history_id=? AND user_id=?", (rid, uid), commit=True)
            q("DELETE FROM resume_history WHERE id=? AND user_id=?", (rid, uid), commit=True)
            if st.session_state.get("view_id") == rid:
                st.session_state["view_id"] = None
            st.rerun()
        pdf = load_report(uid, rid)
        if pdf:
            cp.download_button("⬇️ PDF", pdf, file_name=f"CV_Analyser_Report_{rid}.pdf", mime="application/pdf", key=f"dp{rid}")
        if st.session_state.get("view_id") == rid:
            row = q("SELECT analysis_json,extracted_text FROM resume_history WHERE id=? AND user_id=?", (rid, uid), one=True)
            try:
                render_analysis(json.loads(row[0]), f"h{rid}", pdf)
                with st.expander("📄 Extracted Text"):
                    st.text((row[1] or "")[:6000])
            except Exception:
                st.info("This record could not be displayed.")
        st.markdown("---")
    confirm = st.checkbox("I confirm I want to delete ALL my history", key="confirm_clear")
    if st.button("🧹 Clear All History", key="b_clear"):
        if confirm:
            q("DELETE FROM reports WHERE user_id=?", (uid,), commit=True)
            q("DELETE FROM resume_history WHERE user_id=?", (uid,), commit=True)
            st.session_state["view_id"] = None
            st.rerun()
        else:
            st.warning("Tick the confirmation box first.")


# ============================== PAGE: PROFILE ==============================
def page_profile(uid):
    st.markdown("## 👤 Profile")
    u = q("SELECT name,email,mobile,created_at FROM users WHERE id=?", (uid,), one=True)
    total = q("SELECT COUNT(*) FROM resume_history WHERE user_id=?", (uid,), one=True)[0]
    c1, c2 = st.columns(2)
    mbox(c1, "Name", u[0]); mbox(c2, "Email", u[1] or "-")
    c3, c4 = st.columns(2)
    mbox(c3, "Mobile", u[2] or "-"); mbox(c4, "Resumes Analysed", total)
    st.caption(f"Member since {u[3] or 'N/A'}")
    st.markdown("### 🔒 Change Password")
    with st.form("pw_form"):
        old = st.text_input("Current Password", type="password", key="op")
        n1 = st.text_input("New Password (min 8 characters, letters + numbers)", type="password", key="n1")
        n2 = st.text_input("Confirm New Password", type="password", key="n2")
        go = st.form_submit_button("Update Password", type="primary")
    if go:
        row = q("SELECT password_hash FROM users WHERE id=?", (uid,), one=True)
        if not verify_password(old, row[0]):
            st.error("Current password is incorrect.")
        elif password_problem(n1):
            st.error(password_problem(n1))
        elif n1 != n2:
            st.error("Passwords do not match.")
        else:
            q("UPDATE users SET password_hash=? WHERE id=?", (hash_password(n1), uid), commit=True)
            q("DELETE FROM sessions WHERE user_id=? AND token_hash!=?", (uid, token_hash(st.session_state.get("token") or "")), commit=True)
            st.success("✅ Password updated.")
    st.markdown("### ⚠️ Danger Zone")
    ok = st.checkbox("I understand my account and all history will be permanently deleted", key="confirm_del")
    if st.button("Delete Account", key="b_del"):
        if ok:
            for tbl in ("reports", "resume_history", "otps", "sessions"):
                q(f"DELETE FROM {tbl} WHERE user_id=?", (uid,), commit=True)
            q("DELETE FROM users WHERE id=?", (uid,), commit=True)
            logout()
            st.rerun()
        else:
            st.warning("Tick the confirmation box first.")


# ============================== APP ==============================
HERO = """<div class="hero"><h1>📄 CV Analyser</h1>
<p>Upload your resume and get instant CV Score, Skills Analysis &amp; Job Match Report</p></div>"""

restore_session()

if not st.session_state.get("logged_in"):
    st.markdown('<style>[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }</style>', unsafe_allow_html=True)
    st.markdown(HERO, unsafe_allow_html=True)
    login_page()
    footer()
    st.stop()

_uid = st.session_state["user_id"]
with st.sidebar:
    st.markdown(f'<div class="panel">👋 Welcome,<br><b>{escape(st.session_state.get("user_name", ""))}</b><br>'
                f'<span style="color:#6b7280;font-size:.8rem">{escape(st.session_state.get("user_email", ""))}</span></div>', unsafe_allow_html=True)
    page = st.radio("Menu", ["🔍 Analyze Resume", "📊 Dashboard", "📚 History", "👤 Profile"], key="nav")
    if st.button("🚪 Logout", key="b_logout"):
        logout()
        st.rerun()

st.markdown(HERO, unsafe_allow_html=True)
st.markdown(f'<div class="greet">👋 Welcome, <b>{escape(st.session_state.get("user_name", ""))}</b></div>', unsafe_allow_html=True)
st.markdown('<div class="mobile-hint">☰ Tap the arrow at the top-left to open the menu</div>', unsafe_allow_html=True)

if page.startswith("🔍"):
    page_analyze(_uid)
elif page.startswith("📊"):
    page_dashboard(_uid)
elif page.startswith("📚"):
    page_history(_uid)
else:
    page_profile(_uid)
footer()
