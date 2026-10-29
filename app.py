"""
Smart CV Analyzer Pro - Auth + History + Advanced CV Analysis (single file)
Install: pip install -r requirements.txt   (OCR also needs the Tesseract program)
Run:     streamlit run app.py
"""
import io, re, json, os, sqlite3, hashlib, zipfile, shutil
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Smart CV Analyzer Pro", page_icon="📄", layout="wide", initial_sidebar_state="expanded")
DB = "resume_analyzer.db"

# ============================== DATABASE ==============================
def db():
    return sqlite3.connect(DB)

def q(sql, args=(), one=False, commit=False):
    c = db()
    try:
        cur = c.execute(sql, args)
        r = cur.fetchone() if one else cur.fetchall()
        if commit:
            c.commit()
        return r
    finally:
        c.close()

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password_hash TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS resume_history(id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, file_name TEXT, category TEXT, ats_score REAL, found_skills TEXT,
        missing_skills TEXT, extracted_text TEXT, analysis_date TEXT)""")
    cols = [r[1] for r in c.execute("PRAGMA table_info(resume_history)")]
    if "full_json" not in cols:
        c.execute("ALTER TABLE resume_history ADD COLUMN full_json TEXT")
    c.commit(); c.close()

def hp(p):
    return hashlib.sha256(p.encode()).hexdigest()

init_db()

# ============================== THEME / UI HELPERS ==============================
st.session_state.setdefault("theme", "Dark")

def get_css(theme):
    if theme == "Dark":
        bg, card, border, text, sub = "#0b1020", "#111827", "#2b3245", "#e5e7eb", "#9ca3af"
    else:
        bg, card, border, text, sub = "#f8fafc", "#ffffff", "#e2e8f0", "#0f172a", "#475569"
    return f"""<style>
.stApp {{ background:{bg}; color:{text}; }}
.block-container {{ padding-top:1.2rem; max-width:1400px; }}
h1,h2,h3,h4,h5,h6,p,span,label,div {{ color:{text}; }}
.hero {{ background:linear-gradient(120deg,#4f46e5,#7c3aed,#db2777); padding:30px 34px; border-radius:20px; margin-bottom:18px; box-shadow:0 12px 30px rgba(124,58,237,.25); }}
.hero h1,.hero p {{ color:white !important; margin:0; }}
.hero h1 {{ font-size:2.2rem; }} .hero p {{ margin-top:8px; opacity:.92; }}
.card {{ background:{card}; border:1px solid {border}; border-radius:16px; padding:18px 20px; box-shadow:0 4px 18px rgba(0,0,0,.08); margin-bottom:8px; }}
.kpi {{ background:{card}; border:1px solid {border}; border-radius:16px; padding:18px; text-align:center; }}
.kpi .label {{ font-size:.85rem; color:{sub}; font-weight:600; }}
.kpi .value {{ font-size:2rem; font-weight:800; margin-top:4px; }}
.chip {{ display:inline-block; padding:5px 12px; margin:3px; border-radius:999px; background:rgba(124,58,237,.14); border:1px solid rgba(124,58,237,.38); font-size:.84rem; font-weight:500; }}
.chip.miss {{ background:rgba(220,38,38,.12); border-color:rgba(220,38,38,.38); }}
.chip.ok {{ background:rgba(22,163,74,.12); border-color:rgba(22,163,74,.38); }}
.section-title {{ font-size:1.15rem; font-weight:800; margin:14px 0 8px; }}
.small {{ color:{sub}; font-size:.88rem; }}
.stTabs [data-baseweb="tab-list"] {{ gap:8px; }}
.stTabs [data-baseweb="tab"] {{ border-radius:12px 12px 0 0; padding:10px 18px; }}
.stDownloadButton button,.stButton button {{ border-radius:12px; font-weight:700; }}
</style>"""

def chart_font_color():
    return "#e5e7eb" if st.session_state.get("theme") == "Dark" else "#0f172a"

def show_chart(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)

def show_df(df):
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)

def kpi(label, value):
    return f'<div class="kpi"><div class="label">{escape(str(label))}</div><div class="value">{escape(str(value))}</div></div>'

def chips(items, cls=""):
    return "".join(f'<span class="chip {cls}">{escape(str(i))}</span>' for i in items)

def footer():
    st.markdown("---")
    st.markdown("<p style='text-align:center'>Built with ❤️ by Sufiyan</p>", unsafe_allow_html=True)

# ============================== KNOWLEDGE BASE ==============================
SKILLS_DB = {
    "Programming": ["python","java","c++","c#","javascript","typescript","kotlin","swift","php","ruby","scala","matlab","c","r","go","dart","bash"],
    "Web": ["html","css","react","angular","vue","node.js","nodejs","express","django","flask","fastapi","spring boot","bootstrap","tailwind","next.js","rest api","streamlit","wordpress","jquery"],
    "Data & AI": ["machine learning","deep learning","nlp","computer vision","pandas","numpy","scikit-learn","tensorflow","keras","pytorch","opencv","power bi","tableau","data analysis","data visualization","matplotlib","seaborn","excel","statistics","generative ai","llm","langchain","data science"],
    "Database": ["sql","mysql","postgresql","mongodb","sqlite","oracle","firebase","redis","nosql"],
    "Cloud & DevOps": ["aws","azure","gcp","docker","kubernetes","jenkins","ci/cd","linux","terraform","git","github","devops"],
    "Mobile & Other": ["android","flutter","react native","ios","cyber security","networking","iot","blockchain","selenium","junit","jira","figma","ui/ux","dsa","data structures","algorithms","oop"],
    "Soft Skills": ["communication","leadership","teamwork","problem solving","time management","critical thinking","adaptability","creativity","collaboration","presentation"],
}
AMBIGUOUS = {"c", "r", "go"}
LABEL_OVERRIDES = {"node.js":"Node.js","nodejs":"Node.js","next.js":"Next.js","ci/cd":"CI/CD","ui/ux":"UI/UX","power bi":"Power BI","rest api":"REST API","scikit-learn":"Scikit-learn","c++":"C++","c#":"C#","ios":"iOS","nosql":"NoSQL","mysql":"MySQL","postgresql":"PostgreSQL","mongodb":"MongoDB","javascript":"JavaScript","typescript":"TypeScript","tensorflow":"TensorFlow","pytorch":"PyTorch","opencv":"OpenCV","fastapi":"FastAPI","github":"GitHub","wordpress":"WordPress","jquery":"jQuery","langchain":"LangChain","sqlite":"SQLite","spring boot":"Spring Boot","react native":"React Native"}

def pretty(skill):
    low = skill.lower()
    if low in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[low]
    return skill.upper() if len(skill) <= 3 else skill.title()

SECTION_ALIASES = {
    "education": ["education","academic qualification","academic qualifications","academics","qualifications","academic background","educational qualification"],
    "experience": ["experience","work experience","professional experience","employment history","internship","internships","work history","internship experience","training"],
    "projects": ["projects","academic projects","personal projects","project work","key projects","major projects","project experience"],
    "skills": ["skills","technical skills","key skills","core competencies","skills & tools","technical proficiency","it skills"],
    "certifications": ["certifications","certificates","courses","training & certifications","certifications & courses"],
    "other": ["summary","objective","career objective","profile","professional summary","achievements","awards","hobbies","interests","languages","references","declaration","personal details","extracurricular","activities"],
}
JOB_ROLES = {
    "Data Scientist": {"skills": ["python","machine learning","pandas","numpy","scikit-learn","sql","statistics","deep learning","data visualization"], "companies": ["Google","Amazon","Microsoft","Fractal Analytics","Mu Sigma","Tiger Analytics","LatentView","Flipkart","Accenture AI"]},
    "Data Analyst": {"skills": ["sql","excel","power bi","tableau","python","pandas","data analysis","data visualization"], "companies": ["Deloitte","EY","KPMG","Genpact","WNS","Swiggy","Zomato","Paytm","Cognizant"]},
    "AI / ML Engineer": {"skills": ["python","tensorflow","pytorch","deep learning","nlp","computer vision","machine learning","docker","llm"], "companies": ["NVIDIA","OpenAI","Samsung R&D","Qualcomm","Wipro AI","TCS Research","Uber","Adobe","Intel"]},
    "Python / Backend Developer": {"skills": ["python","django","flask","fastapi","sql","postgresql","rest api","git","docker"], "companies": ["Infosys","Zoho","Freshworks","Razorpay","Postman","Atlassian","Capgemini","Mindtree","Persistent Systems"]},
    "Frontend Developer": {"skills": ["html","css","javascript","react","typescript","bootstrap","tailwind","git","figma"], "companies": ["Flipkart","Myntra","Cred","Meesho","PhonePe","Swiggy","Adobe","Wipro","HCL Tech"]},
    "Full Stack Developer": {"skills": ["html","css","javascript","react","node.js","mongodb","express","sql","git","rest api"], "companies": ["TCS","Infosys","Accenture","Cognizant","Paytm","Ola","ThoughtWorks","EPAM","Tech Mahindra"]},
    "Java Developer": {"skills": ["java","spring boot","mysql","sql","rest api","oop","git","junit"], "companies": ["TCS","Infosys","Wipro","IBM","Oracle","Capgemini","Amdocs","Goldman Sachs","JPMorgan"]},
    "DevOps / Cloud Engineer": {"skills": ["aws","azure","docker","kubernetes","linux","jenkins","ci/cd","terraform","git","bash"], "companies": ["Amazon AWS","Microsoft Azure","Red Hat","Cisco","VMware","HCL Tech","Tech Mahindra","LTIMindtree"]},
    "Android / Mobile Developer": {"skills": ["android","kotlin","java","flutter","dart","firebase","react native"], "companies": ["Google","Samsung","PhonePe","Dream11","Zomato","Paytm","Ola"]},
    "Software Tester / QA": {"skills": ["selenium","junit","jira","sql","java","python","git"], "companies": ["Capgemini","Cognizant","Infosys","Tech Mahindra","Mphasis","Wipro","Accenture","Hexaware"]},
}
PROJECT_IDEAS = {
    "Data & AI": ["Resume–Job Description Matcher using NLP embeddings","Customer Churn Prediction Dashboard with Explainable AI","Sentiment Analysis of Product Reviews using Transformers","Sales Forecasting System using Time-Series Models","Fake News Detection using BERT"],
    "Web": ["Full-Stack Job Portal with Role-based Authentication","Real-time Chat Application using WebSockets","E-commerce Platform with Payment Gateway Integration","Personal Finance Tracker with Interactive Charts","Online Examination System with Auto-evaluation"],
    "Programming": ["Smart Library Management System with Recommendation Engine","Algorithm Visualizer for Sorting, Graphs and DP","Code Plagiarism Detector","Command-line Task Automation Toolkit","Multiplayer Game with Leaderboard"],
    "Database": ["Hospital Management System with Optimized SQL Schema","Inventory Management with Analytics Dashboard","NoSQL-based Social Media Feed Engine"],
    "Cloud & DevOps": ["CI/CD Pipeline for a Dockerized Web App on AWS","Kubernetes-based Auto-scaling Microservices Demo","Infrastructure-as-Code using Terraform"],
    "Mobile & Other": ["Flutter Expense Tracker with Cloud Sync","IoT Smart Home Monitoring System","Face-recognition Attendance Application","Network Intrusion Detection System"],
}
GENERIC_IDEAS = ["Portfolio Website with Blog and Analytics","AI Chatbot for College / Company FAQs using RAG","Weather and Air-Quality Dashboard using Public APIs"]
ATS_ACTION_VERBS = ["developed","designed","built","created","implemented","improved","optimized","automated","led","managed","analyzed","deployed","tested","reduced","increased","achieved","collaborated","integrated","maintained","researched"]
METRIC_RE = re.compile(r"\d+\s?%|\d+\+|\$\s?\d+|₹\s?\d+")

# ============================== TEXT EXTRACTION ==============================
IMAGE_EXTS = (".png",".jpg",".jpeg",".jfif",".webp",".bmp",".tif",".tiff",".gif",".heic",".heif")
MAX_OCR_PAGES, MAX_OCR_FRAMES = 15, 8

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

def _detect_name(file_name, b):
    lower = file_name.lower()
    if b"%PDF-" in b[:1024]:
        return "file.pdf"
    if b[:4] == b"\xd0\xcf\x11\xe0":
        raise RuntimeError("Old .doc files are not supported. Save as DOCX or PDF and upload again.")
    if b[:2] == b"PK":
        try:
            if "word/document.xml" in zipfile.ZipFile(io.BytesIO(b)).namelist():
                return "file.docx"
        except Exception:
            pass
        raise RuntimeError("Unsupported file type. Upload PDF, DOCX, TXT or an image.")
    try:
        from PIL import Image
        Image.open(io.BytesIO(b)).verify()
        return "file.png"
    except Exception:
        pass
    if lower.endswith(IMAGE_EXTS) or lower.endswith((".pdf", ".docx")):
        return lower
    if b"\x00" in b[:2000]:
        raise RuntimeError("Unsupported file type. Upload PDF, DOCX, TXT or an image.")
    return "file.txt"

def read_cv(file_name, b):
    name = _detect_name(file_name, b)
    if name.endswith(".pdf"):
        import pdfplumber
        ocr_error, pages = None, []
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if len(t.strip()) < 30 and i < MAX_OCR_PAGES:
                    try:
                        t = ocr_image(page.to_image(resolution=200).original)
                    except RuntimeError as exc:
                        ocr_error = str(exc)
                    except Exception:
                        pass
                pages.append(t)
        text = "\n".join(pages)
        if len(text.strip()) < 50 and ocr_error:
            raise RuntimeError(ocr_error)
        return text
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(b))
        parts = [p.text for p in d.paragraphs]
        for tb in d.tables:
            for row in tb.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if name.endswith(IMAGE_EXTS):
        from PIL import Image, ImageSequence
        if name.endswith((".heic", ".heif")):
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except ImportError as exc:
                raise RuntimeError("For HEIC images run: pip install pillow-heif") from exc
        try:
            image = Image.open(io.BytesIO(b)); image.load()
        except Exception as exc:
            raise RuntimeError(f"Could not open the image (corrupt or unsupported): {exc}") from exc
        frames = []
        for n, fr in enumerate(ImageSequence.Iterator(image)):
            if n >= MAX_OCR_FRAMES:
                break
            frames.append(fr.copy())
        return "\n".join(ocr_image(f) for f in (frames or [image]))
    return b.decode("utf-8", errors="ignore")

# ============================== PARSING ==============================
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

def extract_skills(text, skills_section):
    found = {}
    for cat, skills in SKILLS_DB.items():
        for s in skills:
            hay = skills_section if s in AMBIGUOUS else text
            if hay and find_pattern(hay, s):
                lab = pretty(s)
                found.setdefault(cat, [])
                if lab not in found[cat]:
                    found[cat].append(lab)
    return found

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

def estimate_experience_years(text, exp_lines):
    years = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", text, re.I)]
    best = max(years) if years and max(years) < 40 else 0.0
    span, joined, cy = 0.0, "\n".join(exp_lines), datetime.now().year
    for s, e in re.findall(r"((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)", joined, re.I):
        ey = cy if e.lower() in ("present", "current") else int(e)
        span += max(0, ey - int(s))
    return round(min(max(best, span), 40.0), 1)

# ============================== SCORING (max 100) ==============================
def calculate_score(d):
    bd, tips = {}, []
    c = (3 if d["name"] != "Not found" else 0) + (3 if d["email"] != "Not found" else 0) + (2 if d["phone"] != "Not found" else 0) + (2 if d["linkedin"] or d["github"] else 0)
    bd["Contact Info"] = (c, 10)
    if not (d["linkedin"] or d["github"]): tips.append("Add LinkedIn and GitHub links at the top of your CV.")
    if c < 8: tips.append("Keep name, email and phone clearly visible in the header.")

    tech = sum(len(i) for k, i in d["skills"].items() if k != "Soft Skills")
    cats = len([k for k, i in d["skills"].items() if i and k != "Soft Skills"])
    ss = min(18, tech * 1.5) + min(5, cats * 1.25) + (2 if d["skills"].get("Soft Skills") else 0)
    bd["Skills"] = (round(min(ss, 25), 1), 25)
    if tech < 8: tips.append("List at least 8–10 relevant technical skills, grouped by category.")
    if not d["skills"].get("Soft Skills"): tips.append("Add soft skills such as communication, teamwork and leadership.")

    bd["Education"] = (min(10, 4 + len(d["education"]) * 2) if d["education"] else 0, 10)
    if not d["education"]: tips.append("Add an Education section with degree, institution and year.")

    es = min(20, 8 + len(d["experience"]) * 1.2 + d["experience_years"] * 2) if d["experience"] else 0
    bd["Experience"] = (round(es, 1), 20)
    if not d["experience"]: tips.append("Add internships, training, freelance work or part-time experience.")

    bd["Projects"] = (min(15, len(d["projects"]) * 5) if d["projects"] else 0, 15)
    if len(d["projects"]) < 3: tips.append("Include at least 3 projects with tech stack and measurable outcomes.")

    bd["Certifications"] = (round(min(5, len(d["certifications"]) * 1.5), 1) if d["certifications"] else 0, 5)
    if not d["certifications"]: tips.append("Add relevant certifications or online courses.")

    words = len(d["text"].split())
    fmt = 10 if 250 <= words <= 900 else 6 if (150 <= words < 250 or 900 < words <= 1300) else 3
    metrics = METRIC_RE.search(d["text"])
    fmt = min(15, fmt + (2 if metrics else 0))
    av = sum(1 for v in ATS_ACTION_VERBS if find_pattern(d["text"], v))
    fmt = min(15, fmt + (3 if av >= 3 else 1 if av else 0))
    bd["Formatting & Impact"] = (fmt, 15)
    if not metrics: tips.append("Use measurable impact, for example: improved accuracy by 12%.")
    if av < 3: tips.append("Start bullet points with strong action verbs such as built, developed or optimized.")
    if words < 250: tips.append("Your CV looks short. Add more detail to projects, skills and achievements.")
    if words > 900: tips.append("Your CV is long. Keep it concise, ideally 1–2 pages.")

    total = max(0, min(100, round(sum(v for v, _ in bd.values()))))
    return total, bd, tips

def grade(score):
    if score >= 80: return "Excellent 🌟", "#16a34a"
    if score >= 65: return "Good 👍", "#2563eb"
    if score >= 45: return "Average ⚠️", "#d97706"
    return "Needs Work ❌", "#dc2626"

def match_jobs(all_skills):
    have = {s.lower() for s in all_skills}
    rows = []
    for role, info in JOB_ROLES.items():
        req = info["skills"]
        matched = [s for s in req if s in have]
        rows.append({"Role": role, "Match %": round(100 * len(matched) / len(req)), "Matched": matched,
                     "Missing": [s for s in req if s not in matched], "Companies": info["companies"]})
    return sorted(rows, key=lambda r: r["Match %"], reverse=True)

def extract_jd_skills(jd):
    found = []
    for cat, skills in SKILLS_DB.items():
        if cat == "Soft Skills":
            continue
        for s in skills:
            if s in AMBIGUOUS:
                continue
            if find_pattern(jd, s):
                c = "node.js" if s == "nodejs" else s
                if c not in found:
                    found.append(c)
    return found

def match_job_description(cv, jd):
    jd_skills = extract_jd_skills(jd)
    if not jd_skills:
        return {"jd_skills": [], "matched": [], "missing": [], "match_percent": 0, "priority": []}
    def in_cv(s):
        if s == "node.js":
            return bool(find_pattern(cv, "node.js") or find_pattern(cv, "nodejs"))
        return bool(find_pattern(cv, s))
    matched = [s for s in jd_skills if in_cv(s)]
    missing = [s for s in jd_skills if s not in matched]
    pr = sorted(missing, key=lambda s: (0 if s in ("python","sql","machine learning","javascript","aws") else 1, s))
    return {"jd_skills": jd_skills, "matched": matched, "missing": missing, "match_percent": round(100 * len(matched) / len(jd_skills)), "priority": pr}

def ats_checks(d):
    t, words = d["text"], len(d["text"].split())
    P = lambda ok: "Pass" if ok else "Warning"
    return [
        {"Check": "Contact details", "Status": P(d["email"] != "Not found" and d["phone"] != "Not found"), "Detail": "Email and phone should be clearly present."},
        {"Check": "LinkedIn / GitHub", "Status": P(d["linkedin"] or d["github"]), "Detail": "Add professional profile links."},
        {"Check": "Skills section", "Status": P(d["skills"]), "Detail": "Add a clearly labelled Technical Skills section."},
        {"Check": "Education section", "Status": P(d["education"]), "Detail": "Add degree, institution and year."},
        {"Check": "Projects section", "Status": P(len(d["projects"]) >= 2), "Detail": "Add at least 2–3 strong projects."},
        {"Check": "Measurable achievements", "Status": P(METRIC_RE.search(t)), "Detail": "Use numbers, percentages or business impact."},
        {"Check": "Action verbs", "Status": P(any(find_pattern(t, v) for v in ATS_ACTION_VERBS)), "Detail": "Use verbs such as developed, built, optimized and deployed."},
        {"Check": "CV length", "Status": P(250 <= words <= 900), "Detail": f"Current word count: {words}. Ideal range: 250–900 words."},
    ]

def suggest_projects(skills_by_cat):
    ideas, seen = [], set()
    for cat, _ in sorted(skills_by_cat.items(), key=lambda i: len(i[1]), reverse=True):
        for idea in PROJECT_IDEAS.get(cat, []):
            if idea not in seen:
                ideas.append((cat, idea)); seen.add(idea)
    for idea in GENERIC_IDEAS:
        ideas.append(("General", idea))
    return ideas[:12]

# ============================== PDF REPORT ==============================
def pdf_safe(v):
    return str(v).encode("cp1252", "ignore").decode("cp1252")

def build_pdf(data, total, breakdown, tips, jobs, ideas, jd_result=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1x", parent=ss["Heading1"], textColor=colors.HexColor("#4f46e5"))
    h2 = ParagraphStyle("h2x", parent=ss["Heading2"], textColor=colors.HexColor("#4f46e5"), spaceBefore=12)
    body = ParagraphStyle("bodyx", parent=ss["BodyText"], wordWrap="CJK")
    cell = ParagraphStyle("cellx", parent=body, fontSize=9, leading=11)
    head = ParagraphStyle("headx", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    para = lambda v, s=body: Paragraph(escape(pdf_safe(v)), s)

    def table(rows, widths, header=True):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        st_ = [("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#c7c7d9")), ("VALIGN", (0,0), (-1,-1), "TOP"),
               ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1,-1), [colors.white, colors.HexColor("#f3f4fb")])]
        if header:
            st_.append(("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4f46e5")))
        t.setStyle(TableStyle(st_)); return t

    story = [Paragraph("CV Analysis Report", h1), para(f"Generated on: {datetime.now().strftime('%d %b %Y')}"), Spacer(1, 8),
             table([[para(k, cell), para(v or "-", cell)] for k, v in
                    [("Name", data["name"]), ("Email", data["email"]), ("Phone", data["phone"]), ("LinkedIn", data["linkedin"]), ("GitHub", data["github"])]],
                   [3.5*cm, 13*cm], header=False)]
    gl, _ = grade(total)
    rows = [[para("Category", head), para("Score", head), para("Max", head)]]
    for k, (v, m) in breakdown.items():
        rows.append([para(k, cell), para(v, cell), para(m, cell)])
    story += [Paragraph("Overall CV Score", h2), para(f"{total} / 100 - {gl.strip()}"), Spacer(1, 6), table(rows, [9*cm, 3*cm, 3*cm])]
    story.append(Paragraph("Skills", h2))
    if data["skills"]:
        for c, items in data["skills"].items():
            story.append(para(f"{c}: {', '.join(items)}"))
    else:
        story.append(para("No skills detected."))
    for title, key in [("Education","education"),("Experience","experience"),("Projects","projects"),("Certifications","certifications")]:
        story.append(Paragraph(title, h2))
        for line in data[key] or ["Not found"]:
            story.append(para("• " + line))
    story.append(Paragraph("Best Matching Job Roles", h2))
    jr = [[para("Role", head), para("Match", head), para("Companies", head)]]
    for j in jobs[:6]:
        jr.append([para(j["Role"], cell), para(f"{j['Match %']}%", cell), para(", ".join(j["Companies"][:6]), cell)])
    story.append(table(jr, [5*cm, 2*cm, 9.5*cm]))
    if jd_result and jd_result.get("jd_skills"):
        story += [Paragraph("Job Description Match", h2), para(f"JD Match Score: {jd_result['match_percent']}%"),
                  para("Matched skills: " + (", ".join(pretty(s) for s in jd_result["matched"]) or "-")),
                  para("Missing skills: " + (", ".join(pretty(s) for s in jd_result["missing"]) or "-"))]
    story.append(Paragraph("Suggested Project Topics", h2))
    for c, idea in ideas:
        story.append(para(f"• [{c}] {idea}"))
    story.append(Paragraph("Improvement Tips", h2))
    for t in tips or ["Great CV! Keep it updated."]:
        story.append(para("• " + t))
    doc.build(story)
    return buf.getvalue()

def txt_report(file_name, date, category, score, found, missing, tips=None):
    r = f"""SMART CV ANALYZER - REPORT
===========================
File: {file_name}
Date: {date}
Best Matching Role: {category}
CV Score: {score}/100

Found Skills ({len(found)}):
{', '.join(found) if found else 'None'}

Skills to learn for best-match role ({len(missing)}):
{', '.join(missing) if missing else 'None'}
"""
    if tips:
        r += "\nImprovement Tips:\n- " + "\n- ".join(tips) + "\n"
    return r

# ============================== ANALYSIS PIPELINE ==============================
@st.cache_data(show_spinner=False)
def analyze(file_name, file_bytes):
    text = read_cv(file_name, file_bytes)
    sec = split_sections(text)
    email, phone = extract_email(text), extract_phone(text)
    li, gh = extract_links(text)
    exp = extract_experience(sec["experience"])
    data = {"text": text, "name": extract_name(text, email), "email": email, "phone": phone, "linkedin": li, "github": gh,
            "skills": extract_skills(text, "\n".join(sec["skills"])), "education": extract_education(text, sec["education"]),
            "experience": exp, "experience_years": estimate_experience_years(text, exp),
            "projects": extract_projects(sec["projects"]), "certifications": extract_certifications(text, sec["certifications"])}
    allk = []
    for items in data["skills"].values():
        for s in items:
            if s not in allk:
                allk.append(s)
    data["all_skills"] = allk
    total, bd, tips = calculate_score(data)
    return data, total, bd, tips, match_jobs(allk), suggest_projects(data["skills"])

# ============================== AUTH ==============================
for k, v in {"logged_in": False, "user_id": None, "user_name": "", "user_email": ""}.items():
    st.session_state.setdefault(k, v)

st.markdown(get_css(st.session_state["theme"]), unsafe_allow_html=True)

def login_page():
    st.markdown('<div class="hero"><h1>📄 Smart CV Analyzer Pro</h1><p>AI resume screening — login to analyze, track and improve your CV.</p></div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        t1, t2, t3 = st.tabs(["🔐 Login", "📝 Sign Up", "🔑 Forgot Password"])
        with t1:
            e = st.text_input("Email", key="le"); p = st.text_input("Password", type="password", key="lp")
            if st.button("Login", key="b_login"):
                u = q("SELECT id,name,email FROM users WHERE email=? AND password_hash=?", (e.strip().lower(), hp(p)), one=True)
                if u:
                    st.session_state.update(logged_in=True, user_id=u[0], user_name=u[1], user_email=u[2]); st.rerun()
                else:
                    st.error("Invalid email or password.")
        with t2:
            n = st.text_input("Full Name", key="sn"); e2 = st.text_input("Email", key="se")
            p1 = st.text_input("Password", type="password", key="sp1"); p2 = st.text_input("Confirm Password", type="password", key="sp2")
            if st.button("Create Account", key="b_signup"):
                e2 = e2.strip().lower()
                if not (n.strip() and e2 and p1): st.error("Please fill all fields.")
                elif not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", e2): st.error("Invalid email address.")
                elif len(p1) < 6: st.error("Password must be at least 6 characters.")
                elif p1 != p2: st.error("Passwords do not match.")
                elif q("SELECT id FROM users WHERE email=?", (e2,), one=True): st.error("Email already registered.")
                else:
                    q("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)", (n.strip(), e2, hp(p1), datetime.now().strftime("%Y-%m-%d")), commit=True)
                    st.success("✅ Account created! Please log in.")
        with t3:
            e3 = st.text_input("Registered Email", key="fe"); np1 = st.text_input("New Password", type="password", key="fp1")
            if st.button("Reset Password", key="b_reset"):
                if not q("SELECT id FROM users WHERE email=?", (e3.strip().lower(),), one=True): st.error("Email not found.")
                elif len(np1) < 6: st.error("Password must be at least 6 characters.")
                else:
                    q("UPDATE users SET password_hash=? WHERE email=?", (hp(np1), e3.strip().lower()), commit=True)
                    st.success("✅ Password updated. You can log in now.")

if not st.session_state.logged_in:
    login_page(); footer(); st.stop()

uid = st.session_state.user_id

def logout():
    for k in list(st.session_state.keys()):
        if k != "theme":
            del st.session_state[k]
    st.session_state["logged_in"] = False

# ============================== SIDEBAR ==============================
with st.sidebar:
    st.success(f"👋 Welcome, {st.session_state.user_name}")
    page = st.radio("Menu", ["🔍 Analyzer (New Scan)", "📚 History / My Resumes", "👤 Profile"], key="page")
    st.radio("Theme", ["Dark", "Light"], horizontal=True, key="theme")
    if st.button("🚪 Logout", key="b_logout"):
        logout(); st.rerun()
    st.divider()

# ============================== PAGE A: ANALYZER ==============================
ED_KEYS = ["name", "email", "phone", "linkedin", "github", "education", "experience", "projects", "certifications"]

def ed_lines(key):
    return [l.strip() for l in str(st.session_state.get("ed_" + key, "")).splitlines() if l.strip()]

def page_analyzer():
    with st.sidebar:
        st.header("📤 Input")
        mode = st.radio("Input type", ["Upload File", "Camera", "Paste Text"], key="mode")
        name, fbytes = None, None
        if mode == "Upload File":
            f = st.file_uploader("PDF, DOCX, TXT or Image")
            if f: name, fbytes = f.name, f.getvalue()
        elif mode == "Camera":
            cam = st.camera_input("Take a photo of your CV")
            if cam: name, fbytes = "camera_photo.png", cam.getvalue()
        else:
            txt = st.text_area("Paste resume text", height=200, key="paste_box")
            if st.button("Analyze Text", key="b_paste"):
                st.session_state["pasted"] = txt
            if st.session_state.get("pasted", "").strip():
                name, fbytes = "Pasted Text.txt", st.session_state["pasted"].encode("utf-8")
        st.caption("Text-based PDF works best. Scanned/image CVs need Tesseract OCR.")

    st.markdown('<div class="hero"><h1>📄 Smart CV Analyzer</h1><p>Upload your CV, analyze it instantly, match it with job descriptions and download a professional report.</p></div>', unsafe_allow_html=True)
    if not fbytes:
        st.info("👈 Choose a CV in the sidebar — PDF, DOCX, TXT, image, camera photo or pasted text.")
        return
    try:
        with st.spinner("Analyzing your CV..."):
            data, total, breakdown, tips, jobs, ideas = analyze(name, fbytes)
    except Exception as e:
        st.error(f"Could not read the CV: {e}"); return
    if len(data["text"].strip()) < 50:
        st.warning("Not enough text could be extracted. For scanned CVs install pytesseract + Tesseract, or upload a clearer file.")
        return

    sig = f"{name}:{len(fbytes)}:{hashlib.md5(fbytes).hexdigest()}"
    if st.session_state.get("file_sig") != sig:
        init = {"name": data["name"], "email": data["email"], "phone": data["phone"], "linkedin": data["linkedin"] or "",
                "github": data["github"] or "", "education": "\n".join(data["education"]), "experience": "\n".join(data["experience"]),
                "projects": "\n".join(data["projects"]), "certifications": "\n".join(data["certifications"])}
        for k in ED_KEYS:
            st.session_state["ed_" + k] = init[k]
        st.session_state.pop("jd_result", None)
        st.session_state["file_sig"] = sig
    # ---- auto-save to history (once per file) ----
    if st.session_state.get("saved_sig") != sig:
        payload = {"data": data, "total": total, "breakdown": breakdown, "tips": tips, "jobs": jobs, "ideas": ideas}
        top = jobs[0]
        q("INSERT INTO resume_history(user_id,file_name,category,ats_score,found_skills,missing_skills,extracted_text,analysis_date,full_json) VALUES(?,?,?,?,?,?,?,?,?)",
          (uid, name, top["Role"], total, json.dumps(data["all_skills"]), json.dumps([pretty(s) for s in top["Missing"]]),
           data["text"], datetime.now().strftime("%Y-%m-%d %H:%M"), json.dumps(payload)), commit=True)
        st.session_state["saved_sig"] = sig
        st.session_state["just_saved"] = True
    if st.session_state.pop("just_saved", False):
        st.success("✅ Saved to History")

    label, color = grade(total)
    tabs = st.tabs(["📊 Dashboard", "👤 Extracted Info", "🧮 Score & ATS", "💼 Jobs & Companies", "🎯 JD Matcher", "💡 Projects & Report"])

    with tabs[0]:
        cols = st.columns(4)
        for col, (lab, val) in zip(cols, [("CV Score", f"{total}/100"), ("Skills Found", len(data["all_skills"])), ("Projects", len(data["projects"])), ("Experience", f"{data['experience_years']} yrs")]):
            col.markdown(kpi(lab, val), unsafe_allow_html=True)
        l, r = st.columns([1, 1.2])
        with l:
            g = go.Figure(go.Indicator(mode="gauge+number", value=total, title={"text": label},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}, "steps": [
                    {"range": [0, 45], "color": "#fee2e2"}, {"range": [45, 65], "color": "#fef3c7"},
                    {"range": [65, 80], "color": "#dbeafe"}, {"range": [80, 100], "color": "#dcfce7"}]}))
            g.update_layout(height=340, margin=dict(t=70, b=10, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", font_color=chart_font_color())
            show_chart(g)
        with r:
            cats = list(breakdown.keys()); pct = [round(100 * v / m) for v, m in breakdown.values()]
            rd = go.Figure(go.Scatterpolar(r=pct + pct[:1], theta=cats + cats[:1], fill="toself", line_color="#7c3aed"))
            rd.update_layout(polar={"radialaxis": {"range": [0, 100]}}, height=340, margin=dict(t=40, b=20, l=50, r=50), showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font_color=chart_font_color())
            show_chart(rd)
        cl, cr = st.columns(2)
        with cl:
            if data["skills"]:
                sdf = pd.DataFrame({"Category": list(data["skills"].keys()), "Count": [len(i) for i in data["skills"].values()]})
                pie = px.pie(sdf, names="Category", values="Count", hole=0.55, title="Skills by Category")
                pie.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", font_color=chart_font_color())
                show_chart(pie)
            else:
                st.info("No skills detected for the chart.")
        with cr:
            jdf = pd.DataFrame(jobs[:8])[["Role", "Match %"]].sort_values("Match %")
            bar = px.bar(jdf, x="Match %", y="Role", orientation="h", range_x=[0, 100], title="Top Job-Role Matches")
            bar.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", font_color=chart_font_color())
            show_chart(bar)

    with tabs[1]:
        st.subheader("✏️ Edit Extracted Details")
        st.caption("Correct anything that was detected wrongly — the PDF report uses these values.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("Name", key="ed_name"); c2.text_input("Email", key="ed_email"); c3.text_input("Phone", key="ed_phone")
        c4, c5 = st.columns(2)
        c4.text_input("LinkedIn URL", key="ed_linkedin"); c5.text_input("GitHub URL", key="ed_github")
        st.markdown('<div class="section-title">🎓 Education</div>', unsafe_allow_html=True)
        st.text_area("Education", key="ed_education", height=130, label_visibility="collapsed")
        c6, c7 = st.columns(2)
        with c6:
            st.markdown('<div class="section-title">💼 Experience</div>', unsafe_allow_html=True)
            st.text_area("Experience", key="ed_experience", height=180, label_visibility="collapsed")
        with c7:
            st.markdown('<div class="section-title">🚀 Projects</div>', unsafe_allow_html=True)
            st.text_area("Projects", key="ed_projects", height=180, label_visibility="collapsed")
        st.markdown('<div class="section-title">📜 Certifications</div>', unsafe_allow_html=True)
        st.text_area("Certifications", key="ed_certifications", height=130, label_visibility="collapsed")
        st.divider(); st.subheader("🧠 Detected Skills")
        if data["skills"]:
            for cat, items in data["skills"].items():
                st.markdown(f"**{cat}**"); st.markdown(chips(items), unsafe_allow_html=True)
        else:
            st.warning("No skills detected.")
        with st.expander("📄 View Extracted Text"):
            st.text(data["text"])

    with tabs[2]:
        st.subheader(f"Total CV Score: {total}/100 — {label}")
        for cat, (v, m) in breakdown.items():
            st.write(f"**{cat}** — {v}/{m}"); st.progress(max(0.0, min(1.0, float(v) / m)))
        sc = go.Figure()
        sc.add_bar(x=list(breakdown.keys()), y=[m for _, m in breakdown.values()], name="Maximum", marker_color="#9ca3af")
        sc.add_bar(x=list(breakdown.keys()), y=[v for v, _ in breakdown.values()], name="Your Score", marker_color="#7c3aed")
        sc.update_layout(barmode="overlay", title="Score Breakdown", height=420, paper_bgcolor="rgba(0,0,0,0)", font_color=chart_font_color())
        show_chart(sc)
        st.divider(); st.subheader("🤖 ATS-style Checks")
        for row in ats_checks(data):
            badge = '<span class="chip ok">PASS</span>' if row["Status"] == "Pass" else '<span class="chip miss">WARNING</span>'
            st.markdown(f'<div class="card"><b>{escape(row["Check"])}</b> {badge}<div class="small">{escape(row["Detail"])}</div></div>', unsafe_allow_html=True)
        st.divider(); st.subheader("✅ Improvement Tips")
        for t in tips or ["Great CV! Keep it updated."]:
            st.write("• " + t)

    with tabs[3]:
        st.subheader("💼 Best Matching Roles & Hiring Companies")
        for i, job in enumerate(jobs[:8]):
            with st.expander(f"{job['Role']} — {job['Match %']}% match", expanded=(i == 0)):
                st.progress(max(0.0, min(1.0, job["Match %"] / 100)))
                st.markdown("**Companies:** " + ", ".join(job["Companies"]))
                st.markdown("**Matched skills:**")
                st.markdown(chips([pretty(s) for s in job["Matched"]], "ok") if job["Matched"] else "—", unsafe_allow_html=True)
                st.markdown("**Skills to learn:**")
                st.markdown(chips([pretty(s) for s in job["Missing"]], "miss") if job["Missing"] else "—", unsafe_allow_html=True)

    with tabs[4]:
        st.subheader("🎯 Job Description Matcher")
        st.caption("Paste a job description to get a match percentage and prioritized missing skills.")
        jd_text = st.text_area("Paste Job Description", height=260, placeholder="Paste the full job description here...", key="jd_text")
        if st.button("🔍 Match CV with Job Description", type="primary", key="b_jd"):
            if not jd_text.strip(): st.warning("Paste a job description first.")
            else: st.session_state["jd_result"] = match_job_description(data["text"], jd_text)
        jr = st.session_state.get("jd_result")
        if jr:
            if not jr["jd_skills"]:
                st.warning("No known technical skills were found in the job description.")
            else:
                a, b, c = st.columns(3)
                a.markdown(kpi("JD Match", f"{jr['match_percent']}%"), unsafe_allow_html=True)
                b.markdown(kpi("Matched Skills", len(jr["matched"])), unsafe_allow_html=True)
                c.markdown(kpi("Missing Skills", len(jr["missing"])), unsafe_allow_html=True)
                st.progress(max(0.0, min(1.0, jr["match_percent"] / 100)))
                st.markdown('<div class="section-title">✅ Matched Skills</div>', unsafe_allow_html=True)
                st.markdown(chips([pretty(s) for s in jr["matched"]], "ok") if jr["matched"] else "—", unsafe_allow_html=True)
                st.markdown('<div class="section-title">⚠️ Missing Skills — Priority Order</div>', unsafe_allow_html=True)
                if jr["priority"]:
                    for n, s in enumerate(jr["priority"], 1):
                        st.markdown(f'<div class="card">{n}. <b>{escape(pretty(s))}</b> <span class="chip miss">Learn / Add</span></div>', unsafe_allow_html=True)
                else:
                    st.success("Excellent! Your CV already covers the important skills.")

    with tabs[5]:
        st.subheader("💡 Suggested Project Topics")
        for cat, idea in ideas:
            st.markdown(f"- **[{cat}]** {idea}")
        st.divider(); st.subheader("📥 Download Report")
        ed = dict(data)
        ed["name"] = st.session_state.get("ed_name") or data["name"]
        ed["email"] = st.session_state.get("ed_email") or data["email"]
        ed["phone"] = st.session_state.get("ed_phone") or data["phone"]
        ed["linkedin"] = st.session_state.get("ed_linkedin") or None
        ed["github"] = st.session_state.get("ed_github") or None
        for k in ("education", "experience", "projects", "certifications"):
            ed[k] = ed_lines(k)
        try:
            pdf = build_pdf(ed, total, breakdown, tips, jobs, ideas, st.session_state.get("jd_result"))
            safe = re.sub(r"[^A-Za-z0-9]+", "_", str(ed["name"])).strip("_") or "CV"
            st.download_button("⬇️ Download PDF Report", data=pdf, file_name=f"CV_Report_{safe}.pdf", mime="application/pdf", type="primary")
        except Exception as e:
            st.error(f"Could not generate the PDF: {e}")
        st.download_button("⬇️ Download TXT Report", txt_report(name, datetime.now().strftime("%Y-%m-%d %H:%M"), jobs[0]["Role"], total,
                           data["all_skills"], [pretty(s) for s in jobs[0]["Missing"]], tips), file_name="cv_report.txt", key="dl_txt_now")

# ============================== PAGE B: HISTORY ==============================
def page_history():
    st.markdown('<div class="hero"><h1>📚 History / My Resumes</h1><p>Every CV you analyze is saved here.</p></div>', unsafe_allow_html=True)
    rows = q("SELECT id,analysis_date,file_name,category,ats_score,found_skills,missing_skills,extracted_text,full_json FROM resume_history WHERE user_id=?", (uid,))
    df = pd.DataFrame(rows, columns=["ID", "Date", "File Name", "Category", "CV Score", "found", "missing", "text", "full"])
    a, b, c = st.columns(3)
    a.metric("📁 Total Scans", len(df))
    b.metric("📊 Average Score", f"{df['CV Score'].mean():.1f}" if len(df) else "0")
    c.metric("🏆 Best Category", df.groupby("Category")["CV Score"].mean().idxmax() if len(df) else "N/A")
    if df.empty:
        st.info("No resumes analyzed yet. Go to the Analyzer to start!"); return
    s1, s2, s3 = st.columns([2, 1, 1])
    search = s1.text_input("🔎 Search by file name or category")
    cat = s2.selectbox("Category", ["All"] + sorted(df["Category"].dropna().unique().tolist()))
    sort = s3.selectbox("Sort by", ["Date (Newest)", "Date (Oldest)", "Score (High)", "Score (Low)"])
    if search:
        df = df[df["File Name"].str.contains(search, case=False, na=False, regex=False) | df["Category"].str.contains(search, case=False, na=False, regex=False)]
    if cat != "All":
        df = df[df["Category"] == cat]
    keys = {"Date (Newest)": ["Date", "ID"], "Date (Oldest)": ["Date", "ID"], "Score (High)": ["CV Score"], "Score (Low)": ["CV Score"]}[sort]
    df = df.sort_values(keys, ascending=sort in ("Date (Oldest)", "Score (Low)"))
    show_df(df[["Date", "File Name", "Category", "CV Score"]])
    st.markdown("### 📂 Records")
    for _, r in df.iterrows():
        rid = int(r["ID"])
        with st.expander(f"👁️ View Details — {r['File Name']} | {r['Category']} | {r['CV Score']} | {r['Date']}"):
            try: found, missing = json.loads(r["found"] or "[]"), json.loads(r["missing"] or "[]")
            except Exception: found, missing = [], []
            st.progress(max(0.0, min(1.0, float(r["CV Score"] or 0) / 100)))
            st.markdown("**Found skills**"); st.markdown(chips(found, "ok") if found else "None", unsafe_allow_html=True)
            st.markdown("**Missing skills**"); st.markdown(chips(missing, "miss") if missing else "None", unsafe_allow_html=True)
            st.text_area("Extracted Text", r["text"] or "", height=150, key=f"t{rid}", disabled=True)
            payload = None
            if r["full"]:
                try: payload = json.loads(r["full"])
                except Exception: payload = None
            b1, b2, b3 = st.columns(3)
            b1.download_button("⬇️ TXT Report", txt_report(r["File Name"], r["Date"], r["Category"], r["CV Score"], found, missing, payload["tips"] if payload else None), file_name=f"report_{rid}.txt", key=f"d{rid}")
            if payload:
                if b2.button("📄 Prepare PDF", key=f"p{rid}"):
                    try:
                        bd = {k: tuple(v) for k, v in payload["breakdown"].items()}
                        ideas = [tuple(i) for i in payload["ideas"]]
                        st.session_state[f"pdf{rid}"] = build_pdf(payload["data"], payload["total"], bd, payload["tips"], payload["jobs"], ideas)
                    except Exception as e:
                        st.error(f"PDF failed: {e}")
                if f"pdf{rid}" in st.session_state:
                    b2.download_button("⬇️ Download PDF", st.session_state[f"pdf{rid}"], file_name=f"CV_Report_{rid}.pdf", mime="application/pdf", key=f"dp{rid}")
            if b3.button("🗑️ Delete", key=f"x{rid}"):
                q("DELETE FROM resume_history WHERE id=? AND user_id=?", (rid, uid), commit=True)
                st.session_state.pop("saved_sig", None); st.rerun()
    st.markdown("---")
    confirm = st.checkbox("I confirm I want to delete ALL my history", key="confirm_clear")
    if st.button("🧹 Clear All History", key="b_clear"):
        if confirm:
            q("DELETE FROM resume_history WHERE user_id=?", (uid,), commit=True)
            st.session_state.pop("saved_sig", None); st.rerun()
        else:
            st.warning("Tick the confirmation box first.")

# ============================== PAGE C: PROFILE ==============================
def page_profile():
    st.markdown('<div class="hero"><h1>👤 Profile</h1><p>Manage your account.</p></div>', unsafe_allow_html=True)
    since = q("SELECT created_at FROM users WHERE id=?", (uid,), one=True)
    total = q("SELECT COUNT(*) FROM resume_history WHERE user_id=?", (uid,), one=True)[0]
    c1, c2 = st.columns(2)
    c1.metric("Name", st.session_state.user_name); c2.metric("Email", st.session_state.user_email)
    c3, c4 = st.columns(2)
    c3.metric("Resumes Analyzed", total); c4.metric("Member Since", since[0] if since and since[0] else "N/A")
    st.markdown("### 🔒 Change Password")
    old = st.text_input("Current Password", type="password", key="op")
    n1 = st.text_input("New Password", type="password", key="n1"); n2 = st.text_input("Confirm New Password", type="password", key="n2")
    if st.button("Update Password", key="b_pw"):
        if not q("SELECT id FROM users WHERE id=? AND password_hash=?", (uid, hp(old)), one=True): st.error("Current password is incorrect.")
        elif len(n1) < 6: st.error("New password must be at least 6 characters.")
        elif n1 != n2: st.error("Passwords do not match.")
        else:
            q("UPDATE users SET password_hash=? WHERE id=?", (hp(n1), uid), commit=True); st.success("✅ Password updated.")
    st.markdown("### ⚠️ Danger Zone")
    ok = st.checkbox("I understand my account and all history will be permanently deleted", key="confirm_del")
    if st.button("Delete Account", key="b_del"):
        if ok:
            q("DELETE FROM resume_history WHERE user_id=?", (uid,), commit=True)
            q("DELETE FROM users WHERE id=?", (uid,), commit=True)
            logout(); st.rerun()
        else:
            st.warning("Tick the confirmation box first.")

# ============================== ROUTER ==============================
if page.startswith("🔍"):
    page_analyzer()
elif page.startswith("📚"):
    page_history()
else:
    page_profile()
footer()