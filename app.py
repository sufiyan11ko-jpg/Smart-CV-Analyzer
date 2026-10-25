"""
CV Analyzer - Streamlit Mini Project
Run:  streamlit run app.py
"""
import io
import re
from xml.sax.saxutils import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# PAGE CONFIG + CSS
# ----------------------------------------------------------------------------
st.set_page_config(page_title="CV Analyzer", page_icon="📄", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem;}
.hero {background: linear-gradient(120deg,#4f46e5,#7c3aed,#db2777); padding: 28px 32px;
       border-radius: 18px; color: white; margin-bottom: 18px;}
.hero h1 {margin: 0; font-size: 2.2rem;} .hero p {margin: 6px 0 0; opacity: .9;}
.card {background: #ffffff10; border: 1px solid #8884; border-radius: 14px; padding: 16px 18px;}
.chip {display:inline-block; padding:4px 12px; margin:3px; border-radius:999px;
       background:#4f46e522; border:1px solid #4f46e566; font-size:.85rem;}
.chip.miss {background:#dc262622; border-color:#dc262666;}
.metric-big {font-size:2.4rem; font-weight:800;}
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# KNOWLEDGE BASE
# ----------------------------------------------------------------------------
SKILLS_DB = {
    "Programming": ["python", "java", "c++", "c#", "javascript", "typescript", "kotlin", "swift",
                    "php", "ruby", "scala", "matlab", "c", "r", "go", "dart", "bash"],
    "Web": ["html", "css", "react", "angular", "vue", "node.js", "nodejs", "express", "django",
            "flask", "fastapi", "spring boot", "bootstrap", "tailwind", "next.js", "rest api",
            "streamlit", "wordpress", "jquery"],
    "Data & AI": ["machine learning", "deep learning", "nlp", "computer vision", "pandas", "numpy",
                  "scikit-learn", "tensorflow", "keras", "pytorch", "opencv", "power bi", "tableau",
                  "data analysis", "data visualization", "matplotlib", "seaborn", "excel",
                  "statistics", "generative ai", "llm", "langchain", "data science"],
    "Database": ["sql", "mysql", "postgresql", "mongodb", "sqlite", "oracle", "firebase", "redis",
                 "nosql"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "ci/cd", "linux",
                       "terraform", "git", "github", "devops"],
    "Mobile & Other": ["android", "flutter", "react native", "ios", "cyber security", "networking",
                       "iot", "blockchain", "selenium", "junit", "jira", "figma", "ui/ux", "dsa",
                       "data structures", "algorithms", "oop"],
    "Soft Skills": ["communication", "leadership", "teamwork", "problem solving",
                    "time management", "critical thinking", "adaptability", "creativity",
                    "collaboration", "presentation"],
}
AMBIGUOUS = {"c", "r", "go"}  # matched only inside the Skills section

SECTION_ALIASES = {
    "education": ["education", "academic qualification", "academic qualifications", "academics",
                  "qualifications", "academic background", "educational qualification"],
    "experience": ["experience", "work experience", "professional experience", "employment history",
                   "internship", "internships", "work history", "internship experience",
                   "training"],
    "projects": ["projects", "academic projects", "personal projects", "project work",
                 "key projects", "major projects", "project experience"],
    "skills": ["skills", "technical skills", "key skills", "core competencies", "skills & tools",
               "technical proficiency", "it skills"],
    "other": ["summary", "objective", "career objective", "profile", "professional summary",
              "certifications", "certificates", "achievements", "awards", "hobbies", "interests",
              "languages", "references", "declaration", "personal details", "extracurricular",
              "activities", "courses"],
}

JOB_ROLES = {
    "Data Scientist": {
        "skills": ["python", "machine learning", "pandas", "numpy", "scikit-learn", "sql",
                   "statistics", "deep learning", "data visualization"],
        "companies": ["Google", "Amazon", "Microsoft", "Fractal Analytics", "Mu Sigma",
                      "Tiger Analytics", "LatentView", "Flipkart", "Accenture AI"]},
    "Data Analyst": {
        "skills": ["sql", "excel", "power bi", "tableau", "python", "pandas", "data analysis",
                   "data visualization"],
        "companies": ["Deloitte", "EY", "KPMG", "Genpact", "WNS", "Swiggy", "Zomato",
                      "Paytm", "Cognizant"]},
    "AI / ML Engineer": {
        "skills": ["python", "tensorflow", "pytorch", "deep learning", "nlp", "computer vision",
                   "machine learning", "docker", "llm"],
        "companies": ["NVIDIA", "OpenAI", "Samsung R&D", "Qualcomm", "Wipro AI", "TCS Research",
                      "Uber", "Adobe", "Intel"]},
    "Python / Backend Developer": {
        "skills": ["python", "django", "flask", "fastapi", "sql", "postgresql", "rest api",
                   "git", "docker"],
        "companies": ["Infosys", "Zoho", "Freshworks", "Razorpay", "Postman", "Atlassian",
                      "Capgemini", "Mindtree", "Persistent Systems"]},
    "Frontend Developer": {
        "skills": ["html", "css", "javascript", "react", "typescript", "bootstrap", "tailwind",
                   "git", "figma"],
        "companies": ["Flipkart", "Myntra", "Cred", "Meesho", "PhonePe", "Swiggy",
                      "Adobe", "Wipro", "HCL Tech"]},
    "Full Stack Developer": {
        "skills": ["html", "css", "javascript", "react", "node.js", "mongodb", "express", "sql",
                   "git", "rest api"],
        "companies": ["TCS", "Infosys", "Accenture", "Cognizant", "Paytm", "Ola",
                      "ThoughtWorks", "EPAM", "Tech Mahindra"]},
    "Java Developer": {
        "skills": ["java", "spring boot", "mysql", "sql", "rest api", "oop", "git", "junit"],
        "companies": ["TCS", "Infosys", "Wipro", "IBM", "Oracle", "Capgemini", "Amdocs",
                      "Goldman Sachs", "JPMorgan"]},
    "DevOps / Cloud Engineer": {
        "skills": ["aws", "azure", "docker", "kubernetes", "linux", "jenkins", "ci/cd",
                   "terraform", "git", "bash"],
        "companies": ["Amazon AWS", "Microsoft Azure", "Red Hat", "Cisco", "VMware", "HCL Tech",
                      "Tech Mahindra", "LTIMindtree"]},
    "Android / Mobile Developer": {
        "skills": ["android", "kotlin", "java", "flutter", "dart", "firebase", "react native"],
        "companies": ["Google", "Samsung", "PhonePe", "Dream11", "Byju's", "Zomato",
                      "Paytm", "Ola"]},
    "Software Tester / QA": {
        "skills": ["selenium", "junit", "jira", "sql", "java", "python", "git"],
        "companies": ["Capgemini", "Cognizant", "Infosys", "Tech Mahindra", "Mphasis",
                      "Wipro", "Accenture", "Hexaware"]},
}

PROJECT_IDEAS = {
    "Data & AI": [
        "Resume–Job Description Matcher using NLP embeddings",
        "Customer Churn Prediction Dashboard with Explainable AI (SHAP)",
        "Sentiment Analysis of Product Reviews using Transformers",
        "Sales Forecasting System using Time-Series (Prophet / LSTM)",
        "Fake News Detection using BERT",
    ],
    "Web": [
        "Full-Stack Job Portal with Role-based Authentication",
        "Real-time Chat Application using WebSockets",
        "E-commerce Platform with Payment Gateway Integration",
        "Personal Finance Tracker with Interactive Charts",
        "Online Examination System with Auto-evaluation",
    ],
    "Programming": [
        "Smart Library Management System with Recommendation Engine",
        "Algorithm Visualizer (Sorting, Graphs, DP)",
        "Code Plagiarism Detector",
        "Command-line Task Automation Toolkit",
        "Multiplayer Game with Leaderboard",
    ],
    "Database": [
        "Hospital Management System with Optimized SQL Schema",
        "Inventory Management with Analytics Dashboard",
        "NoSQL-based Social Media Feed Engine",
    ],
    "Cloud & DevOps": [
        "CI/CD Pipeline for a Dockerized Web App on AWS",
        "Kubernetes-based Auto-scaling Microservices Demo",
        "Infrastructure-as-Code using Terraform",
    ],
    "Mobile & Other": [
        "Flutter Expense Tracker with Cloud Sync",
        "IoT Smart Home Monitoring System",
        "Face-recognition Attendance Application",
        "Network Intrusion Detection System",
    ],
}
GENERIC_IDEAS = [
    "Portfolio Website with Blog and Analytics",
    "AI Chatbot for College / Company FAQs (LLM + RAG)",
    "Weather & Air-Quality Dashboard using Public APIs",
]

# ----------------------------------------------------------------------------
# TEXT EXTRACTION
# ----------------------------------------------------------------------------
def read_cv(uploaded) -> str:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    return data.decode("utf-8", errors="ignore")


# ----------------------------------------------------------------------------
# INFORMATION EXTRACTION
# ----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.I)


def extract_email(text):
    m = EMAIL_RE.search(text)
    return m.group(0) if m else "Not found"


def extract_phone(text):
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 10 <= len(digits) <= 13 and not re.fullmatch(r"(19|20)\d{2}(19|20)\d{2}", digits):
            return m.group(0).strip()
    return "Not found"


def extract_name(text, email):
    skip = ("resume", "curriculum", "vitae", "cv", "profile", "objective", "summary", "contact",
            "address", "email", "phone", "mobile", "github", "linkedin")
    for line in [l.strip() for l in text.splitlines() if l.strip()][:12]:
        low = line.lower()
        if "@" in line or any(w in low for w in skip) or re.search(r"\d", line):
            continue
        words = re.sub(r"[^A-Za-z .'-]", " ", line).split()
        if 2 <= len(words) <= 4 and all(w[0].isalpha() for w in words):
            return " ".join(w.capitalize() if w.isupper() else w for w in words)
    if email != "Not found":
        guess = re.sub(r"[\d._-]+", " ", email.split("@")[0]).title().strip()
        if guess:
            return guess
    return "Not found"


def split_sections(text):
    lookup = {a: k for k, v in SECTION_ALIASES.items() for a in v}
    sections, current = {k: [] for k in SECTION_ALIASES}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = re.sub(r"[^a-z &]", "", line.lower()).strip()
        if len(line) < 40 and key in lookup:
            current = lookup[key]
            continue
        if current:
            sections[current].append(line)
    return sections


def find_pattern(text, pattern):
    return re.search(r"(?<![A-Za-z0-9+#.])" + re.escape(pattern) + r"(?![A-Za-z0-9+#])", text, re.I)


def extract_skills(text, skills_section):
    found = {}
    for cat, items in SKILLS_DB.items():
        for s in items:
            hay = skills_section if s in AMBIGUOUS else text
            if hay and find_pattern(hay, s):
                found.setdefault(cat, [])
                label = s.upper() if len(s) <= 3 or s in ("nlp", "sql", "aws", "gcp") else s.title()
                if label not in found[cat]:
                    found[cat].append(label)
    return found


DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|m\.?\s?tech|b\.?\s?e\.?|m\.?\s?e\.?|bca|mca|bba|mba|b\.?\s?sc|m\.?\s?sc|"
    r"b\.?\s?com|m\.?\s?com|b\.?\s?a\.?|m\.?\s?a\.?|ph\.?d|diploma|bachelor|master|doctorate|"
    r"12th|10th|hsc|ssc|intermediate|higher secondary|secondary|cbse|icse|polytechnic)\b", re.I)


def extract_education(text, section_lines):
    lines = section_lines[:] or [l.strip() for l in text.splitlines() if DEGREE_RE.search(l)]
    lines = [l for l in lines if len(l) > 3]
    return lines[:10]


def estimate_experience_years(text, exp_lines):
    years = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", text, re.I)]
    best = max(years) if years and max(years) < 40 else 0
    span = 0.0
    for a, b in re.findall(r"((?:19|20)\d{2})\s*[-–to]+\s*((?:19|20)\d{2}|present|current)",
                           "\n".join(exp_lines), re.I):
        end = 2026 if b.lower() in ("present", "current") else int(b)
        span += max(0, end - int(a))
    return round(max(best, span), 1)


def extract_experience(section_lines):
    return [l for l in section_lines if len(l) > 3][:12]


def extract_projects(section_lines):
    out = []
    for l in section_lines:
        if len(l) < 4:
            continue
        is_title = (not l.startswith(("•", "-", "*", "●", "▪"))) and len(l.split()) <= 12
        if is_title or not out:
            out.append(l.lstrip("•-*●▪ ").strip())
    return out[:8]


def extract_links(text):
    ln, gh = LINKEDIN_RE.search(text), GITHUB_RE.search(text)
    return (ln.group(0) if ln else None), (gh.group(0) if gh else None)


# ----------------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------------
def calculate_score(d):
    bd, tips = {}, []
    # Contact (15)
    c = 0
    c += 4 if d["name"] != "Not found" else 0
    c += 4 if d["email"] != "Not found" else 0
    c += 4 if d["phone"] != "Not found" else 0
    c += 3 if (d["linkedin"] or d["github"]) else 0
    bd["Contact Info"] = (c, 15)
    if not (d["linkedin"] or d["github"]):
        tips.append("Add LinkedIn / GitHub links to your header.")
    if c < 12:
        tips.append("Make sure name, email and phone are clearly visible at the top.")
    # Skills (25)
    n = sum(len(v) for k, v in d["skills"].items() if k != "Soft Skills")
    cats = len([k for k, v in d["skills"].items() if v and k != "Soft Skills"])
    s = min(18, n * 1.5) + min(5, cats * 1.25) + (2 if d["skills"].get("Soft Skills") else 0)
    bd["Skills"] = (round(min(s, 25), 1), 25)
    if n < 8:
        tips.append("List at least 8–10 relevant technical skills, grouped by category.")
    if not d["skills"].get("Soft Skills"):
        tips.append("Mention a few soft skills (communication, teamwork, leadership).")
    # Education (15)
    e = min(15, 6 + len(d["education"]) * 3) if d["education"] else 0
    bd["Education"] = (e, 15)
    if not d["education"]:
        tips.append("Add an Education section with degree, college and year.")
    # Experience (20)
    x = 0
    if d["experience"]:
        x = min(20, 8 + len(d["experience"]) * 1.5 + d["exp_years"] * 2)
    bd["Experience"] = (round(x, 1), 20)
    if not d["experience"]:
        tips.append("Add internships / training / part-time work, even short ones.")
    # Projects (15)
    p = min(15, len(d["projects"]) * 5) if d["projects"] else 0
    bd["Projects"] = (p, 15)
    if len(d["projects"]) < 3:
        tips.append("Include 3+ projects with tech stack and measurable outcomes.")
    # Formatting / length (10)
    w = len(d["text"].split())
    f = 10 if 250 <= w <= 900 else 6 if 150 <= w < 250 or 900 < w <= 1300 else 3
    nums = len(re.findall(r"\d+%|\d+\+|\$\d+|₹\d+", d["text"]))
    f = min(10, f + (1 if nums else 0))
    bd["Formatting & Impact"] = (f, 10)
    if not nums:
        tips.append("Use numbers to show impact (e.g. 'improved accuracy by 12%').")
    if w < 250:
        tips.append("Your CV looks short — add more detail on projects and achievements.")
    if w > 900:
        tips.append("Your CV is long — keep it to 1–2 pages.")
    total = round(sum(v for v, _ in bd.values()))
    return total, bd, tips


def grade(score):
    return ("Excellent 🌟", "#16a34a") if score >= 80 else ("Good 👍", "#2563eb") if score >= 65 \
        else ("Average ⚠️", "#d97706") if score >= 45 else ("Needs Work ❌", "#dc2626")


# ----------------------------------------------------------------------------
# JOB MATCHING + PROJECT TOPICS
# ----------------------------------------------------------------------------
def match_jobs(all_skills):
    have = {s.lower() for s in all_skills}
    rows = []
    for role, info in JOB_ROLES.items():
        req = info["skills"]
        hit = [s for s in req if s in have]
        miss = [s for s in req if s not in have]
        rows.append({"Role": role, "Match %": round(100 * len(hit) / len(req)),
                     "Matched": hit, "Missing": miss, "Companies": info["companies"]})
    return sorted(rows, key=lambda r: r["Match %"], reverse=True)


def suggest_projects(skills_by_cat):
    ideas, seen = [], set()
    order = sorted(skills_by_cat.items(), key=lambda kv: -len(kv[1]))
    for cat, _ in order:
        for idea in PROJECT_IDEAS.get(cat, []):
            if idea not in seen:
                ideas.append((cat, idea)); seen.add(idea)
    for idea in GENERIC_IDEAS:
        ideas.append(("General", idea))
    return ideas[:10]


# ----------------------------------------------------------------------------
# PDF REPORT
# ----------------------------------------------------------------------------
def build_pdf(d, total, bd, tips, jobs, ideas):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=colors.HexColor("#4f46e5"))
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor("#4f46e5"),
                        spaceBefore=12)
    body = ss["BodyText"]
    P = lambda t, s=body: Paragraph(escape(str(t)), s)

    def table(data, widths, header=True):
        t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7c7d9")),
                 ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4fb")])]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        t.setStyle(TableStyle(style))
        return t

    s = [Paragraph("CV Analysis Report", h1), P(f"Candidate: {d['name']}"), Spacer(1, 6)]
    s.append(table([["Email", d["email"]], ["Phone", d["phone"]],
                    ["LinkedIn", d["linkedin"] or "-"], ["GitHub", d["github"] or "-"]],
                   [3.5 * cm, 13 * cm], header=False))
    g, _ = grade(total)
    s += [Paragraph("Overall CV Score", h2),
          P(f"{total} / 100  -  {re.sub(r'[^A-Za-z ]', '', g).strip()}")]
    s.append(Spacer(1, 4))
    s.append(table([["Category", "Score", "Max"]] + [[k, v, m] for k, (v, m) in bd.items()],
                   [9 * cm, 3 * cm, 3 * cm]))

    s.append(Paragraph("Skills", h2))
    if d["skills"]:
        for cat, items in d["skills"].items():
            s.append(P(f"{cat}: {', '.join(items)}"))
    else:
        s.append(P("No skills detected."))

    for title, key in (("Education", "education"), ("Experience", "experience"),
                       ("Projects", "projects")):
        s.append(Paragraph(title, h2))
        for line in (d[key] or ["Not found"]):
            s.append(P("• " + line))

    s.append(Paragraph("Best Matching Job Roles & Companies", h2))
    s.append(table([["Role", "Match", "Companies"]] +
                   [[Paragraph(escape(j["Role"]), body), f"{j['Match %']}%",
                     Paragraph(escape(", ".join(j["Companies"][:6])), body)] for j in jobs[:5]],
                   [5 * cm, 2 * cm, 9.5 * cm]))

    s.append(Paragraph("Suggested Project Topics", h2))
    for cat, idea in ideas:
        s.append(P(f"• [{cat}] {idea}"))

    s.append(Paragraph("Improvement Tips", h2))
    for t in (tips or ["Great CV! Keep it updated."]):
        s.append(P("• " + t))
    doc.build(s)
    return buf.getvalue()


# ----------------------------------------------------------------------------
# ANALYSIS PIPELINE
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def analyze(file_name, file_bytes):
    class _F:  # tiny wrapper so read_cv works with cached bytes
        name, _b = file_name, file_bytes
        def read(self): return self._b
    text = read_cv(_F())
    sections = split_sections(text)
    email, phone = extract_email(text), extract_phone(text)
    linkedin, github = extract_links(text)
    exp = extract_experience(sections["experience"])
    d = {
        "text": text,
        "name": extract_name(text, email), "email": email, "phone": phone,
        "linkedin": linkedin, "github": github,
        "skills": extract_skills(text, "\n".join(sections["skills"])),
        "education": extract_education(text, sections["education"]),
        "experience": exp,
        "exp_years": estimate_experience_years(text, exp),
        "projects": extract_projects(sections["projects"]),
    }
    d["all_skills"] = [s for v in d["skills"].values() for s in v]
    total, bd, tips = calculate_score(d)
    jobs = match_jobs(d["all_skills"])
    ideas = suggest_projects(d["skills"])
    return d, total, bd, tips, jobs, ideas


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
st.markdown(
    '<div class="hero"><h1>📄 CV Analyzer</h1>'
    "<p>Upload your CV and get instant extraction, score, job-role matches, company "
    "suggestions, project ideas and a downloadable PDF report.</p></div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("📤 Upload CV")
    up = st.file_uploader("PDF, DOCX or TXT", type=["pdf", "docx", "txt"])
    st.caption("Tip: text-based PDFs work best (scanned images need OCR).")
    st.divider()
    st.markdown("**Features**\n- Name / Email / Phone\n- Skills, Education, Experience, Projects\n"
                "- CV Score & Charts\n- Job roles & Companies\n- Project Topics\n- PDF Report")

if not up:
    st.info("👈 Sidebar se apna CV upload karo (PDF / DOCX / TXT) to analysis start ho jayega.")
    st.stop()

try:
    with st.spinner("Analyzing your CV..."):
        d, total, bd, tips, jobs, ideas = analyze(up.name, up.getvalue())
except Exception as ex:
    st.error(f"CV read nahi ho paya: {ex}")
    st.stop()

if len(d["text"].strip()) < 50:
    st.warning("CV se text extract nahi hua. Shayad ye scanned image PDF hai.")
    st.stop()

label, color = grade(total)
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Dashboard", "👤 Extracted Info", "🧮 Score Breakdown", "💼 Jobs & Companies",
     "💡 Project Topics & Report"])

# ---- Dashboard
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CV Score", f"{total}/100")
    c2.metric("Skills Found", len(d["all_skills"]))
    c3.metric("Projects", len(d["projects"]))
    c4.metric("Experience (yrs)", d["exp_years"])

    left, right = st.columns([1, 1.2])
    with left:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=total, title={"text": f"{label}"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
                   "steps": [{"range": [0, 45], "color": "#fee2e2"},
                             {"range": [45, 65], "color": "#fef3c7"},
                             {"range": [65, 80], "color": "#dbeafe"},
                             {"range": [80, 100], "color": "#dcfce7"}]}))
        fig.update_layout(height=320, margin=dict(t=60, b=10, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        cats = list(bd.keys())
        pct = [round(100 * v / m) for v, m in bd.values()]
        radar = go.Figure(go.Scatterpolar(r=pct + pct[:1], theta=cats + cats[:1], fill="toself",
                                          line_color="#7c3aed"))
        radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=320,
                            margin=dict(t=30, b=10, l=40, r=40), showlegend=False)
        st.plotly_chart(radar, use_container_width=True)

    a, b = st.columns(2)
    with a:
        if d["skills"]:
            df = pd.DataFrame({"Category": list(d["skills"].keys()),
                               "Count": [len(v) for v in d["skills"].values()]})
            st.plotly_chart(px.pie(df, names="Category", values="Count", hole=0.5,
                                   title="Skills by Category"), use_container_width=True)
    with b:
        jdf = pd.DataFrame(jobs[:6])[["Role", "Match %"]].sort_values("Match %")
        st.plotly_chart(px.bar(jdf, x="Match %", y="Role", orientation="h", range_x=[0, 100],
                               title="Top Job-Role Matches"), use_container_width=True)

# ---- Extracted info
with tab2:
    st.subheader("Contact Details")
    a, b, c = st.columns(3)
    a.markdown(f'<div class="card"><b>👤 Name</b><br>{escape(d["name"])}</div>',
               unsafe_allow_html=True)
    b.markdown(f'<div class="card"><b>📧 Email</b><br>{escape(d["email"])}</div>',
               unsafe_allow_html=True)
    c.markdown(f'<div class="card"><b>📱 Phone</b><br>{escape(d["phone"])}</div>',
               unsafe_allow_html=True)
    st.write("")
    st.markdown(f"🔗 LinkedIn: {d['linkedin'] or '—'} &nbsp;&nbsp; 💻 GitHub: {d['github'] or '—'}")

    st.subheader("Skills")
    if d["skills"]:
        for cat, items in d["skills"].items():
            st.markdown(f"**{cat}**")
            st.markdown("".join(f'<span class="chip">{escape(i)}</span>' for i in items),
                        unsafe_allow_html=True)
    else:
        st.warning("Koi skill detect nahi hui.")

    e1, e2 = st.columns(2)
    with e1:
        st.subheader("🎓 Education")
        for l in d["education"] or ["Not found"]:
            st.write("• " + l)
    with e2:
        st.subheader("💼 Experience")
        for l in d["experience"] or ["Not found"]:
            st.write("• " + l)
    st.subheader("🚀 Projects")
    for l in d["projects"] or ["Not found"]:
        st.write("• " + l)

    with st.expander("Raw extracted text"):
        st.text(d["text"])

# ---- Score breakdown
with tab3:
    st.subheader(f"Total Score: {total}/100  —  {label}")
    for k, (v, m) in bd.items():
        st.write(f"**{k}** — {v}/{m}")
        st.progress(min(1.0, v / m))
    bdf = pd.DataFrame({"Category": list(bd.keys()), "Score": [v for v, _ in bd.values()],
                        "Max": [m for _, m in bd.values()]})
    fig = go.Figure()
    fig.add_bar(x=bdf["Category"], y=bdf["Max"], name="Max", marker_color="#e5e7eb")
    fig.add_bar(x=bdf["Category"], y=bdf["Score"], name="Your Score", marker_color="#7c3aed")
    fig.update_layout(barmode="overlay", title="Score Chart", height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("✅ Improvement Tips")
    for t in tips or ["Great CV! Bas ise updated rakho."]:
        st.write("• " + t)

# ---- Jobs & companies
with tab4:
    st.subheader("Best Matching Roles & Hiring Companies")
    for j in jobs[:6]:
        with st.expander(f"{j['Role']} — {j['Match %']}% match", expanded=j is jobs[0]):
            st.progress(j["Match %"] / 100)
            st.markdown("**Companies:** " + ", ".join(j["Companies"]))
            st.markdown("**Matched skills:** " + ("".join(
                f'<span class="chip">{escape(s.title())}</span>' for s in j["Matched"]) or "—"),
                unsafe_allow_html=True)
            st.markdown("**Skills to learn:** " + ("".join(
                f'<span class="chip miss">{escape(s.title())}</span>' for s in j["Missing"]) or "—"),
                unsafe_allow_html=True)

# ---- Project topics + PDF
with tab5:
    st.subheader("💡 Suggested Project Topics")
    for cat, idea in ideas:
        st.markdown(f"- **[{cat}]** {idea}")
    st.divider()
    st.subheader("📥 Download Report")
    try:
        pdf_bytes = build_pdf(d, total, bd, tips, jobs, ideas)
        st.download_button("⬇️ Download PDF Report", data=pdf_bytes,
                           file_name=f"CV_Report_{re.sub(r'[^A-Za-z]', '_', d['name'])}.pdf",
                           mime="application/pdf", type="primary")
    except Exception as ex:
        st.error(f"PDF generate nahi hua: {ex}")