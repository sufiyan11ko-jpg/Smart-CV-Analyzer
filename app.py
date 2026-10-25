"""
CV Analyzer Pro - Streamlit Mini Project
Run: streamlit run app.py
"""

import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="CV Analyzer Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# THEME
# ----------------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

def get_css(theme: str) -> str:
    if theme == "Dark":
        bg = "#0b1020"
        card = "#111827"
        border = "#2b3245"
        text = "#e5e7eb"
        sub = "#9ca3af"
        accent = "#7c3aed"
    else:
        bg = "#f8fafc"
        card = "#ffffff"
        border = "#e2e8f0"
        text = "#0f172a"
        sub = "#475569"
        accent = "#4f46e5"

    return f"""
<style>
.stApp {{ background: {bg}; color: {text}; }}
.block-container {{ padding-top: 1.2rem; max-width: 1400px; }}
h1, h2, h3, h4, h5, h6, p, span, label, div {{ color: {text}; }}
.hero {{
    background: linear-gradient(120deg,#4f46e5,#7c3aed,#db2777);
    padding: 30px 34px; border-radius: 20px; color: white; margin-bottom: 18px;
    box-shadow: 0 12px 30px rgba(124,58,237,.25);
}}
.hero h1 {{ margin: 0; color: white; font-size: 2.25rem; }}
.hero p {{ margin: 8px 0 0; color: rgba(255,255,255,.92); font-size: 1.02rem; }}
.card {{
    background: {card}; border: 1px solid {border}; border-radius: 16px;
    padding: 18px 20px; box-shadow: 0 4px 18px rgba(0,0,0,.08);
}}
.kpi {{
    background: {card}; border: 1px solid {border}; border-radius: 16px;
    padding: 18px; text-align: center;
}}
.kpi .label {{ font-size: .85rem; color: {sub}; font-weight: 600; }}
.kpi .value {{ font-size: 2rem; font-weight: 800; margin-top: 4px; }}
.chip {{
    display: inline-block; padding: 5px 12px; margin: 3px; border-radius: 999px;
    background: rgba(124,58,237,.14); border: 1px solid rgba(124,58,237,.38);
    font-size: .84rem; font-weight: 500;
}}
.chip.miss {{
    background: rgba(220,38,38,.12); border-color: rgba(220,38,38,.38);
}}
.chip.ok {{
    background: rgba(22,163,74,.12); border-color: rgba(22,163,74,.38);
}}
.section-title {{
    font-size: 1.15rem; font-weight: 800; margin: 14px 0 8px;
}}
.small {{ color: {sub}; font-size: .88rem; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 12px 12px 0 0; padding: 10px 18px;
}}
.stDownloadButton button, .stButton button {{
    border-radius: 12px; font-weight: 700;
}}
</style>
"""

# ----------------------------------------------------------------------------
# KNOWLEDGE BASE
# ----------------------------------------------------------------------------
SKILLS_DB = {
    "Programming": [
        "python", "java", "c++", "c#", "javascript", "typescript", "kotlin", "swift",
        "php", "ruby", "scala", "matlab", "c", "r", "go", "dart", "bash"
    ],
    "Web": [
        "html", "css", "react", "angular", "vue", "node.js", "nodejs", "express", "django",
        "flask", "fastapi", "spring boot", "bootstrap", "tailwind", "next.js", "rest api",
        "streamlit", "wordpress", "jquery"
    ],
    "Data & AI": [
        "machine learning", "deep learning", "nlp", "computer vision", "pandas", "numpy",
        "scikit-learn", "tensorflow", "keras", "pytorch", "opencv", "power bi", "tableau",
        "data analysis", "data visualization", "matplotlib", "seaborn", "excel",
        "statistics", "generative ai", "llm", "langchain", "data science", "sql"
    ],
    "Database": [
        "sql", "mysql", "postgresql", "mongodb", "sqlite", "oracle", "firebase", "redis", "nosql"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "ci/cd", "linux",
        "terraform", "git", "github", "devops"
    ],
    "Mobile & Other": [
        "android", "flutter", "react native", "ios", "cyber security", "networking", "iot",
        "blockchain", "selenium", "junit", "jira", "figma", "ui/ux", "dsa",
        "data structures", "algorithms", "oop"
    ],
    "Soft Skills": [
        "communication", "leadership", "teamwork", "problem solving", "time management",
        "critical thinking", "adaptability", "creativity", "collaboration", "presentation"
    ],
}

AMBIGUOUS = {"c", "r", "go"}

SECTION_ALIASES = {
    "education": [
        "education", "academic qualification", "academic qualifications", "academics",
        "qualifications", "academic background", "educational qualification"
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment history",
        "internship", "internships", "work history", "internship experience", "training"
    ],
    "projects": [
        "projects", "academic projects", "personal projects", "project work", "key projects",
        "major projects", "project experience"
    ],
    "skills": [
        "skills", "technical skills", "key skills", "core competencies", "skills & tools",
        "technical proficiency", "it skills"
    ],
    "certifications": [
        "certifications", "certificates", "courses", "training & certifications",
        "certifications & courses"
    ],
    "other": [
        "summary", "objective", "career objective", "profile", "professional summary",
        "achievements", "awards", "hobbies", "interests", "languages", "references",
        "declaration", "personal details", "extracurricular", "activities"
    ],
}

JOB_ROLES = {
    "Data Scientist": {
        "skills": ["python", "machine learning", "pandas", "numpy", "scikit-learn", "sql",
                   "statistics", "deep learning", "data visualization"],
        "companies": ["Google", "Amazon", "Microsoft", "Fractal Analytics", "Mu Sigma",
                      "Tiger Analytics", "LatentView", "Flipkart", "Accenture AI"]
    },
    "Data Analyst": {
        "skills": ["sql", "excel", "power bi", "tableau", "python", "pandas",
                   "data analysis", "data visualization"],
        "companies": ["Deloitte", "EY", "KPMG", "Genpact", "WNS", "Swiggy", "Zomato",
                      "Paytm", "Cognizant"]
    },
    "AI / ML Engineer": {
        "skills": ["python", "tensorflow", "pytorch", "deep learning", "nlp",
                   "computer vision", "machine learning", "docker", "llm"],
        "companies": ["NVIDIA", "OpenAI", "Samsung R&D", "Qualcomm", "Wipro AI",
                      "TCS Research", "Uber", "Adobe", "Intel"]
    },
    "Python / Backend Developer": {
        "skills": ["python", "django", "flask", "fastapi", "sql", "postgresql",
                   "rest api", "git", "docker"],
        "companies": ["Infosys", "Zoho", "Freshworks", "Razorpay", "Postman", "Atlassian",
                      "Capgemini", "Mindtree", "Persistent Systems"]
    },
    "Frontend Developer": {
        "skills": ["html", "css", "javascript", "react", "typescript", "bootstrap",
                   "tailwind", "git", "figma"],
        "companies": ["Flipkart", "Myntra", "Cred", "Meesho", "PhonePe", "Swiggy",
                      "Adobe", "Wipro", "HCL Tech"]
    },
    "Full Stack Developer": {
        "skills": ["html", "css", "javascript", "react", "node.js", "mongodb", "express",
                   "sql", "git", "rest api"],
        "companies": ["TCS", "Infosys", "Accenture", "Cognizant", "Paytm", "Ola",
                      "ThoughtWorks", "EPAM", "Tech Mahindra"]
    },
    "Java Developer": {
        "skills": ["java", "spring boot", "mysql", "sql", "rest api", "oop", "git", "junit"],
        "companies": ["TCS", "Infosys", "Wipro", "IBM", "Oracle", "Capgemini", "Amdocs",
                      "Goldman Sachs", "JPMorgan"]
    },
    "DevOps / Cloud Engineer": {
        "skills": ["aws", "azure", "docker", "kubernetes", "linux", "jenkins", "ci/cd",
                   "terraform", "git", "bash"],
        "companies": ["Amazon AWS", "Microsoft Azure", "Red Hat", "Cisco", "VMware",
                      "HCL Tech", "Tech Mahindra", "LTIMindtree"]
    },
    "Android / Mobile Developer": {
        "skills": ["android", "kotlin", "java", "flutter", "dart", "firebase", "react native"],
        "companies": ["Google", "Samsung", "PhonePe", "Dream11", "Zomato", "Paytm", "Ola"]
    },
    "Software Tester / QA": {
        "skills": ["selenium", "junit", "jira", "sql", "java", "python", "git"],
        "companies": ["Capgemini", "Cognizant", "Infosys", "Tech Mahindra", "Mphasis",
                      "Wipro", "Accenture", "Hexaware"]
    },
}

PROJECT_IDEAS = {
    "Data & AI": [
        "Resume–Job Description Matcher using NLP embeddings",
        "Customer Churn Prediction Dashboard with Explainable AI",
        "Sentiment Analysis of Product Reviews using Transformers",
        "Sales Forecasting System using Time-Series Models",
        "Fake News Detection using BERT"
    ],
    "Web": [
        "Full-Stack Job Portal with Role-based Authentication",
        "Real-time Chat Application using WebSockets",
        "E-commerce Platform with Payment Gateway Integration",
        "Personal Finance Tracker with Interactive Charts",
        "Online Examination System with Auto-evaluation"
    ],
    "Programming": [
        "Smart Library Management System with Recommendation Engine",
        "Algorithm Visualizer for Sorting, Graphs and DP",
        "Code Plagiarism Detector",
        "Command-line Task Automation Toolkit",
        "Multiplayer Game with Leaderboard"
    ],
    "Database": [
        "Hospital Management System with Optimized SQL Schema",
        "Inventory Management with Analytics Dashboard",
        "NoSQL-based Social Media Feed Engine"
    ],
    "Cloud & DevOps": [
        "CI/CD Pipeline for a Dockerized Web App on AWS",
        "Kubernetes-based Auto-scaling Microservices Demo",
        "Infrastructure-as-Code using Terraform"
    ],
    "Mobile & Other": [
        "Flutter Expense Tracker with Cloud Sync",
        "IoT Smart Home Monitoring System",
        "Face-recognition Attendance Application",
        "Network Intrusion Detection System"
    ],
}

GENERIC_IDEAS = [
    "Portfolio Website with Blog and Analytics",
    "AI Chatbot for College / Company FAQs using RAG",
    "Weather and Air-Quality Dashboard using Public APIs"
]

ATS_ACTION_VERBS = [
    "developed", "designed", "built", "created", "implemented", "improved", "optimized",
    "automated", "led", "managed", "analyzed", "deployed", "tested", "reduced", "increased",
    "achieved", "collaborated", "integrated", "maintained", "researched"
]

# ----------------------------------------------------------------------------
# TEXT EXTRACTION
# ----------------------------------------------------------------------------
def read_cv(file_name: str, file_bytes: bytes) -> str:
    name = file_name.lower()

    if name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    pages.append("")
            return "
".join(pages)

    if name.endswith(".docx"):
        import docx
        document = docx.Document(io.BytesIO(file_bytes))
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "
".join(parts)

    return file_bytes.decode("utf-8", errors="ignore")


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:+?d{1,3}[s-]?)?(?:(?d{3,5})?[s.-]?)?d{3,5}[s.-]?d{4,5}"
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www.)?linkedin.com/in/[w-%]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www.)?github.com/[w-]+", re.I)


def extract_email(text: str) -> str:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else "Not found"


def extract_phone(text: str) -> str:
    for match in PHONE_RE.finditer(text):
        digits = re.sub(r"D", "", match.group(0))
        if 10 <= len(digits) <= 13:
            if not re.fullmatch(r"(19|20)d{2}(19|20)d{2}", digits):
                return match.group(0).strip()
    return "Not found"


def extract_name(text: str, email: str) -> str:
    skip_words = (
        "resume", "curriculum", "vitae", "cv", "profile", "objective", "summary",
        "contact", "address", "email", "phone", "mobile", "github", "linkedin"
    )

    for line in [line.strip() for line in text.splitlines() if line.strip()][:15]:
        low = line.lower()
        if "@" in line or any(word in low for word in skip_words) or re.search(r"d", line):
            continue

        words = re.sub(r"[^A-Za-z .'-]", " ", line).split()
        if 2 <= len(words) <= 4 and all(word[0].isalpha() for word in words):
            return " ".join(
                word.capitalize() if not word.isupper() else word for word in words
            )

    if email != "Not found":
        guess = re.sub(r"[d._-]+", " ", email.split("@")[0]).title().strip()
        if guess:
            return guess

    return "Not found"


def split_sections(text: str) -> dict:
    lookup = {
        alias: key
        for key, aliases in SECTION_ALIASES.items()
        for alias in aliases
    }

    sections = {key: [] for key in SECTION_ALIASES}
    current = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        key = re.sub(r"[^a-z &]", "", line.lower()).strip()

        if len(line) < 45 and key in lookup:
            current = lookup[key]
            continue

        if current:
            sections[current].append(line)

    return sections


def find_pattern(text: str, pattern: str):
    return re.search(
        r"(?<![A-Za-z0-9+#.])" + re.escape(pattern) + r"(?![A-Za-z0-9+#])",
        text,
        re.I,
    )


def extract_skills(text: str, skills_section: str) -> dict:
    found = {}

    for category, skills in SKILLS_DB.items():
        for skill in skills:
            hay = skills_section if skill in AMBIGUOUS else text
            if hay and find_pattern(hay, skill):
                label = skill.upper() if len(skill) <= 3 else skill.title()
                found.setdefault(category, [])
                if label not in found[category]:
                    found[category].append(label)

    return found


DEGREE_RE = re.compile(
    r"\b(b.?s?tech|m.?s?tech|b.?s?e.?|m.?s?e.?|bca|mca|bba|mba|b.?s?sc|"
    r"m.?s?sc|b.?s?com|m.?s?com|b.?s?a.?|m.?s?a.?|ph.?d|diploma|bachelor|"
    r"master|doctorate|12th|10th|hsc|ssc|intermediate|higher secondary|secondary|"
    r"cbse|icse|polytechnic)\b",
    re.I,
)


def extract_education(text: str, section_lines: list) -> list:
    lines = section_lines[:] if section_lines else [
        line.strip() for line in text.splitlines() if DEGREE_RE.search(line)
    ]
    lines = [line for line in lines if len(line) > 3]
    return lines[:12]


def extract_experience(section_lines: list) -> list:
    return [line for line in section_lines if len(line) > 3][:15]


def extract_projects(section_lines: list) -> list:
    output = []

    for line in section_lines:
        clean = line.strip()
        if len(clean) < 4:
            continue

        is_title = (
            not clean.startswith(("•", "-", "*", "●", "▪"))
            and len(clean.split()) <= 14
        )

        if is_title or not output:
            output.append(clean.lstrip("•-*●▪ ").strip())

    return output[:10]


def extract_certifications(text: str, section_lines: list) -> list:
    lines = section_lines[:] if section_lines else []

    if not lines:
        for line in text.splitlines():
            if re.search(
                r"\b(certified|certification|certificate|course|specialization|"
                r"nanodegree|bootcamp)\b",
                line,
                re.I,
            ):
                lines.append(line.strip())

    return [line.strip("•-*●▪ ") for line in lines if len(line.strip()) > 4][:12]


def extract_links(text: str):
    linkedin = LINKEDIN_RE.search(text)
    github = GITHUB_RE.search(text)
    return (
        linkedin.group(0) if linkedin else None,
        github.group(0) if github else None,
    )


def estimate_experience_years(text: str, experience_lines: list) -> float:
    years = [
        float(value)
        for value in re.findall(r"(d+(?:.d+)?)+?s*(?:years?|yrs?)", text, re.I)
    ]
    best = max(years) if years and max(years) < 40 else 0.0

    span = 0.0
    joined = "
".join(experience_lines)

    for start, end in re.findall(
        r"((?:19|20)d{2})s*[-–to]+s*((?:19|20)d{2}|present|current)",
        joined,
        re.I,
    ):
        end_year = 2026 if end.lower() in ("present", "current") else int(end)
        span += max(0, end_year - int(start))

    return round(max(best, span), 1)


# ----------------------------------------------------------------------------
# SCORING
# ----------------------------------------------------------------------------
def calculate_score(data: dict):
    breakdown = {}
    tips = []

    # Contact - 15
    contact = 0
    contact += 4 if data["name"] != "Not found" else 0
    contact += 4 if data["email"] != "Not found" else 0
    contact += 4 if data["phone"] != "Not found" else 0
    contact += 3 if data["linkedin"] or data["github"] else 0
    breakdown["Contact Info"] = (contact, 15)

    if not (data["linkedin"] or data["github"]):
        tips.append("Add LinkedIn and GitHub links at the top of your CV.")
    if contact < 12:
        tips.append("Keep name, email and phone clearly visible in the header.")

    # Skills - 25
    technical_skills = sum(
        len(items)
        for category, items in data["skills"].items()
        if category != "Soft Skills"
    )
    skill_categories = len([
        category for category, items in data["skills"].items()
        if items and category != "Soft Skills"
    ])

    skill_score = (
        min(18, technical_skills * 1.5)
        + min(5, skill_categories * 1.25)
        + (2 if data["skills"].get("Soft Skills") else 0)
    )
    breakdown["Skills"] = (round(min(skill_score, 25), 1), 25)

    if technical_skills < 8:
        tips.append("List at least 8–10 relevant technical skills, grouped by category.")
    if not data["skills"].get("Soft Skills"):
        tips.append("Add soft skills such as communication, teamwork and leadership.")

    # Education - 15
    education_score = min(15, 6 + len(data["education"]) * 3) if data["education"] else 0
    breakdown["Education"] = (education_score, 15)

    if not data["education"]:
        tips.append("Add an Education section with degree, institution and year.")

    # Experience - 20
    experience_score = 0
    if data["experience"]:
        experience_score = min(
            20,
            8 + len(data["experience"]) * 1.2 + data["experience_years"] * 2,
        )
    breakdown["Experience"] = (round(experience_score, 1), 20)

    if not data["experience"]:
        tips.append("Add internships, training, freelance work or part-time experience.")

    # Projects - 15
    project_score = min(15, len(data["projects"]) * 5) if data["projects"] else 0
    breakdown["Projects"] = (project_score, 15)

    if len(data["projects"]) < 3:
        tips.append("Include at least 3 projects with tech stack and measurable outcomes.")

    # Certifications - 5
    cert_score = min(5, len(data["certifications"]) * 1.5) if data["certifications"] else 0
    breakdown["Certifications"] = (cert_score, 5)

    if not data["certifications"]:
        tips.append("Add relevant certifications or online courses.")

    # Formatting and impact - 15
    words = len(data["text"].split())

    if 250 <= words <= 900:
        formatting = 10
    elif 150 <= words < 250 or 900 < words <= 1300:
        formatting = 6
    else:
        formatting = 3

    metrics = len(re.findall(r"d+%|d++|$d+|₹d+", data["text"]))
    formatting = min(15, formatting + (2 if metrics else 0))

    action_verbs = sum(
        1 for verb in ATS_ACTION_VERBS if find_pattern(data["text"], verb)
    )
    formatting = min(15, formatting + (3 if action_verbs >= 3 else 1 if action_verbs else 0))

    breakdown["Formatting & Impact"] = (formatting, 15)

    if not metrics:
        tips.append("Use measurable impact, for example: improved accuracy by 12%.")
    if action_verbs < 3:
        tips.append("Start bullet points with strong action verbs such as built, developed or optimized.")
    if words < 250:
        tips.append("Your CV looks short. Add more detail to projects, skills and achievements.")
    if words > 900:
        tips.append("Your CV is long. Keep it concise, ideally 1–2 pages.")

    total = round(sum(value for value, _ in breakdown.values()))
    return total, breakdown, tips


def grade(score: int):
    if score >= 80:
        return "Excellent 🌟", "#16a34a"
    if score >= 65:
        return "Good 👍", "#2563eb"
    if score >= 45:
        return "Average ⚠️", "#d97706"
    return "Needs Work ❌", "#dc2626"


# ----------------------------------------------------------------------------
# JOB MATCHING
# ----------------------------------------------------------------------------
def match_jobs(all_skills: list) -> list:
    have = {skill.lower() for skill in all_skills}
    rows = []

    for role, info in JOB_ROLES.items():
        required = info["skills"]
        matched = [skill for skill in required if skill in have]
        missing = [skill for skill in required if skill not in have]

        rows.append({
            "Role": role,
            "Match %": round(100 * len(matched) / len(required)),
            "Matched": matched,
            "Missing": missing,
            "Companies": info["companies"],
        })

    return sorted(rows, key=lambda row: row["Match %"], reverse=True)


# ----------------------------------------------------------------------------
# JOB DESCRIPTION MATCHER
# ----------------------------------------------------------------------------
def extract_jd_skills(jd_text: str) -> list:
    jd_lower = jd_text.lower()
    found = []

    for category, skills in SKILLS_DB.items():
        if category == "Soft Skills":
            continue
        for skill in skills:
            if find_pattern(jd_lower, skill) and skill not in found:
                found.append(skill)

    return found


def match_job_description(cv_text: str, jd_text: str) -> dict:
    jd_skills = extract_jd_skills(jd_text)

    if not jd_skills:
        return {
            "jd_skills": [],
            "matched": [],
            "missing": [],
            "match_percent": 0,
            "priority": [],
        }

    matched = [skill for skill in jd_skills if find_pattern(cv_text, skill)]
    missing = [skill for skill in jd_skills if skill not in matched]
    match_percent = round(100 * len(matched) / len(jd_skills))

    priority = sorted(
        missing,
        key=lambda skill: (
            0 if skill in ("python", "sql", "machine learning", "javascript", "aws") else 1,
            skill
        )
    )

    return {
        "jd_skills": jd_skills,
        "matched": matched,
        "missing": missing,
        "match_percent": match_percent,
        "priority": priority,
    }


# ----------------------------------------------------------------------------
# ATS CHECKS
# ----------------------------------------------------------------------------
def ats_checks(data: dict) -> list:
    checks = []
    text = data["text"]
    words = len(text.split())

    checks.append({
        "Check": "Contact details",
        "Status": "Pass" if data["email"] != "Not found" and data["phone"] != "Not found" else "Warning",
        "Detail": "Email and phone should be clearly present."
    })

    checks.append({
        "Check": "LinkedIn / GitHub",
        "Status": "Pass" if data["linkedin"] or data["github"] else "Warning",
        "Detail": "Add professional profile links."
    })

    checks.append({
        "Check": "Skills section",
        "Status": "Pass" if data["skills"] else "Warning",
        "Detail": "Add a clearly labelled Technical Skills section."
    })

    checks.append({
        "Check": "Education section",
        "Status": "Pass" if data["education"] else "Warning",
        "Detail": "Add degree, institution and year."
    })

    checks.append({
        "Check": "Projects section",
        "Status": "Pass" if len(data["projects"]) >= 2 else "Warning",
        "Detail": "Add at least 2–3 strong projects."
    })

    checks.append({
        "Check": "Measurable achievements",
        "Status": "Pass" if re.search(r"d+%|d++|$d+|₹d+", text) else "Warning",
        "Detail": "Use numbers, percentages or business impact."
    })

    checks.append({
        "Check": "Action verbs",
        "Status": "Pass" if any(find_pattern(text, verb) for verb in ATS_ACTION_VERBS) else "Warning",
        "Detail": "Use verbs such as developed, built, optimized and deployed."
    })

    checks.append({
        "Check": "CV length",
        "Status": "Pass" if 250 <= words <= 900 else "Warning",
        "Detail": f"Current word count: {words}. Ideal range: 250–900 words."
    })

    return checks


# ----------------------------------------------------------------------------
# PROJECT SUGGESTIONS
# ----------------------------------------------------------------------------
def suggest_projects(skills_by_category: dict) -> list:
    ideas = []
    seen = set()

    ordered = sorted(
        skills_by_category.items(),
        key=lambda item: len(item[1]),
        reverse=True
    )

    for category, _ in ordered:
        for idea in PROJECT_IDEAS.get(category, []):
            if idea not in seen:
                ideas.append((category, idea))
                seen.add(idea)

    for idea in GENERIC_IDEAS:
        ideas.append(("General", idea))

    return ideas[:12]


# ----------------------------------------------------------------------------
# PDF REPORT
# ----------------------------------------------------------------------------
def build_pdf(data: dict, total: int, breakdown: dict, tips: list,
              jobs: list, ideas: list, jd_result: dict = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=colors.HexColor("#4f46e5"))
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#4f46e5"),
        spaceBefore=12,
    )
    body = styles["BodyText"]

    def paragraph(value, style=body):
        return Paragraph(escape(str(value)), style)

    def make_table(rows, widths, header=True):
        table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7c7d9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4fb")]),
        ]

        if header:
            style += [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]

        table.setStyle(TableStyle(style))
        return table

    story = [
        Paragraph("CV Analysis Report", h1),
        paragraph(f"Generated on: {datetime.now().strftime('%d %b %Y')}"),
        Spacer(1, 8),
    ]

    story.append(
        make_table(
            [
                ["Name", data["name"]],
                ["Email", data["email"]],
                ["Phone", data["phone"]],
                ["LinkedIn", data["linkedin"] or "-"],
                ["GitHub", data["github"] or "-"],
            ],
            [3.5 * cm, 13 * cm],
            header=False,
        )
    )

    grade_label, _ = grade(total)
    story += [
        Paragraph("Overall CV Score", h2),
        paragraph(f"{total} / 100 — {grade_label}"),
        Spacer(1, 6),
        make_table(
            [["Category", "Score", "Max"]]
            + [[key, value, maximum] for key, (value, maximum) in breakdown.items()],
            [9 * cm, 3 * cm, 3 * cm],
        ),
    ]

    story.append(Paragraph("Skills", h2))
    if data["skills"]:
        for category, items in data["skills"].items():
            story.append(paragraph(f"{category}: {', '.join(items)}"))
    else:
        story.append(paragraph("No skills detected."))

    for title, key in [
        ("Education", "education"),
        ("Experience", "experience"),
        ("Projects", "projects"),
        ("Certifications", "certifications"),
    ]:
        story.append(Paragraph(title, h2))
        for line in data[key] or ["Not found"]:
            story.append(paragraph("• " + line))

    story.append(Paragraph("Best Matching Job Roles", h2))
    story.append(
        make_table(
            [["Role", "Match", "Companies"]]
            + [
                [
                    Paragraph(escape(job["Role"]), body),
                    f"{job['Match %']}%",
                    Paragraph(escape(", ".join(job["Companies"][:6])), body),
                ]
                for job in jobs[:6]
            ],
            [5 * cm, 2 * cm, 9.5 * cm],
        )
    )

    if jd_result and jd_result["jd_skills"]:
        story.append(Paragraph("Job Description Match", h2))
        story.append(paragraph(f"JD Match Score: {jd_result['match_percent']}%"))
        story.append(paragraph("Matched skills: " + ", ".join(jd_result["matched"])))
        story.append(paragraph("Missing skills: " + ", ".join(jd_result["missing"])))

    story.append(Paragraph("Suggested Project Topics", h2))
    for category, idea in ideas:
        story.append(paragraph(f"• [{category}] {idea}"))

    story.append(Paragraph("Improvement Tips", h2))
    for tip in tips or ["Great CV! Keep it updated."]:
        story.append(paragraph("• " + tip))

    document.build(story)
    return buffer.getvalue()


# ----------------------------------------------------------------------------
# ANALYSIS PIPELINE
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def analyze(file_name: str, file_bytes: bytes):
    text = read_cv(file_name, file_bytes)
    sections = split_sections(text)

    email = extract_email(text)
    phone = extract_phone(text)
    linkedin, github = extract_links(text)
    experience = extract_experience(sections["experience"])

    data = {
        "text": text,
        "name": extract_name(text, email),
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "skills": extract_skills(text, "
".join(sections["skills"])),
        "education": extract_education(text, sections["education"]),
        "experience": experience,
        "experience_years": estimate_experience_years(text, experience),
        "projects": extract_projects(sections["projects"]),
        "certifications": extract_certifications(text, sections["certifications"]),
    }

    data["all_skills"] = [
        skill for items in data["skills"].values() for skill in items
    ]

    total, breakdown, tips = calculate_score(data)
    jobs = match_jobs(data["all_skills"])
    ideas = suggest_projects(data["skills"])

    return data, total, breakdown, tips, jobs, ideas


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Settings")

    st.session_state.theme = st.radio(
        "Theme",
        ["Dark", "Light"],
        horizontal=True,
        key="theme_selector",
    )

    st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

    st.divider()
    st.header("📤 Upload CV")
    uploaded_file = st.file_uploader(
        "Upload your CV",
        type=["pdf", "docx", "txt"],
    )

    st.caption("Tip: text-based PDF works best. Scanned PDFs need OCR.")

    st.divider()
    st.markdown(
        "**Features**
"
        "- Premium dashboard
"
        "- Advanced CV parsing
"
        "- Editable extracted details
"
        "- Job Description Matcher
"
        "- ATS keyword checks
"
        "- Job roles and companies
"
        "- Project topic suggestions
"
        "- PDF report"
    )

st.markdown(
    """
<div class="hero">
    <h1>📄 CV Analyzer Pro</h1>
    <p>Upload your CV, analyze it instantly, match it with job descriptions and download a professional improvement report.</p>
</div>
""",
    unsafe_allow_html=True,
)

if not uploaded_file:
    st.info("👈 Sidebar se apna CV upload karo — PDF, DOCX ya TXT.")
    st.stop()

try:
    with st.spinner("Analyzing your CV..."):
        data, total, breakdown, tips, jobs, ideas = analyze(
            uploaded_file.name,
            uploaded_file.getvalue(),
        )
except Exception as error:
    st.error(f"CV read nahi ho paya: {error}")
    st.stop()

if len(data["text"].strip()) < 50:
    st.warning("CV se text extract nahi hua. Ye scanned image PDF ho sakti hai.")
    st.stop()

# Initialize editable values
if "editable" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
    st.session_state.editable = {
        "name": data["name"],
        "email": data["email"],
        "phone": data["phone"],
        "linkedin": data["linkedin"] or "",
        "github": data["github"] or "",
        "education": "
".join(data["education"]),
        "experience": "
".join(data["experience"]),
        "projects": "
".join(data["projects"]),
        "certifications": "
".join(data["certifications"]),
    }
    st.session_state.last_file = uploaded_file.name

label, color = grade(total)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard",
    "👤 Extracted Info",
    "🧮 Score & ATS",
    "💼 Jobs & Companies",
    "🎯 JD Matcher",
    "💡 Projects & Report",
])

# ----------------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------------
with tab1:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f'<div class="kpi"><div class="label">CV Score</div>'
            f'<div class="value">{total}/100</div></div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f'<div class="kpi"><div class="label">Skills Found</div>'
            f'<div class="value">{len(data["all_skills"])}</div></div>',
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f'<div class="kpi"><div class="label">Projects</div>'
            f'<div class="value">{len(data["projects"])}</div></div>',
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f'<div class="kpi"><div class="label">Experience</div>'
            f'<div class="value">{data["experience_years"]} yrs</div></div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns([1, 1.2])

    with left:
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=total,
                title={"text": label},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": color},
                    "steps": [
                        {"range": [0, 45], "color": "#fee2e2"},
                        {"range": [45, 65], "color": "#fef3c7"},
                        {"range": [65, 80], "color": "#dbeafe"},
                        {"range": [80, 100], "color": "#dcfce7"},
                    ],
                },
            )
        )
        gauge.update_layout(
            height=340,
            margin=dict(t=70, b=10, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e7eb" if st.session_state.theme == "Dark" else "#0f172a",
        )
        st.plotly_chart(gauge, use_container_width=True)

    with right:
        categories = list(breakdown.keys())
        percentages = [
            round(100 * value / maximum)
            for value, maximum in breakdown.values()
        ]

        radar = go.Figure(
            go.Scatterpolar(
                r=percentages + percentages[:1],
                theta=categories + categories[:1],
                fill="toself",
                line_color="#7c3aed",
            )
        )
        radar.update_layout(
            polar={"radialaxis": {"range": [0, 100]}},
            height=340,
            margin=dict(t=40, b=20, l=50, r=50),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e7eb" if st.session_state.theme == "Dark" else "#0f172a",
        )
        st.plotly_chart(radar, use_container_width=True)

    chart_left, chart_right = st.columns(2)

    with chart_left:
        if data["skills"]:
            skill_df = pd.DataFrame({
                "Category": list(data["skills"].keys()),
                "Count": [len(items) for items in data["skills"].values()],
            })
            pie = px.pie(
                skill_df,
                names="Category",
                values="Count",
                hole=0.55,
                title="Skills by Category",
            )
            pie.update_layout(
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e5e7eb" if st.session_state.theme == "Dark" else "#0f172a",
            )
            st.plotly_chart(pie, use_container_width=True)

    with chart_right:
        job_df = pd.DataFrame(jobs[:8])[["Role", "Match %"]].sort_values("Match %")
        bar = px.bar(
            job_df,
            x="Match %",
            y="Role",
            orientation="h",
            range_x=[0, 100],
            title="Top Job-Role Matches",
        )
        bar.update_layout(
            height=380,
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e7eb" if st.session_state.theme == "Dark" else "#0f172a",
        )
        st.plotly_chart(bar, use_container_width=True)

# ----------------------------------------------------------------------------
# EXTRACTED INFO
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("✏️ Edit Extracted Details")
    st.caption("Agar koi detail galat detect hui ho to yahan correct kar sakte ho.")

    edit_col1, edit_col2, edit_col3 = st.columns(3)

    with edit_col1:
        st.session_state.editable["name"] = st.text_input(
            "Name",
            value=st.session_state.editable["name"],
        )

    with edit_col2:
        st.session_state.editable["email"] = st.text_input(
            "Email",
            value=st.session_state.editable["email"],
        )

    with edit_col3:
        st.session_state.editable["phone"] = st.text_input(
            "Phone",
            value=st.session_state.editable["phone"],
        )

    edit_col4, edit_col5 = st.columns(2)

    with edit_col4:
        st.session_state.editable["linkedin"] = st.text_input(
            "LinkedIn URL",
            value=st.session_state.editable["linkedin"],
        )

    with edit_col5:
        st.session_state.editable["github"] = st.text_input(
            "GitHub URL",
            value=st.session_state.editable["github"],
        )

    st.markdown('<div class="section-title">🎓 Education</div>', unsafe_allow_html=True)
    st.session_state.editable["education"] = st.text_area(
        "Education",
        value=st.session_state.editable["education"],
        height=130,
    )

    edit_col6, edit_col7 = st.columns(2)

    with edit_col6:
        st.markdown('<div class="section-title">💼 Experience</div>', unsafe_allow_html=True)
        st.session_state.editable["experience"] = st.text_area(
            "Experience",
            value=st.session_state.editable["experience"],
            height=180,
        )

    with edit_col7:
        st.markdown('<div class="section-title">🚀 Projects</div>', unsafe_allow_html=True)
        st.session_state.editable["projects"] = st.text_area(
            "Projects",
            value=st.session_state.editable["projects"],
            height=180,
        )

    st.markdown('<div class="section-title">📜 Certifications</div>', unsafe_allow_html=True)
    st.session_state.editable["certifications"] = st.text_area(
        "Certifications",
        value=st.session_state.editable["certifications"],
        height=130,
    )

    st.divider()
    st.subheader("🧠 Detected Skills")
    if data["skills"]:
        for category, items in data["skills"].items():
            st.markdown(f"**{category}**")
            st.markdown(
                "".join(f'<span class="chip">{escape(skill)}</span>' for skill in items),
                unsafe_allow_html=True,
            )
    else:
        st.warning("Koi skill detect nahi hui.")

    with st.expander("📄 Raw Extracted Text"):
        st.text(data["text"])

# ----------------------------------------------------------------------------
# SCORE AND ATS
# ----------------------------------------------------------------------------
with tab3:
    st.subheader(f"Total CV Score: {total}/100 — {label}")

    for category, (value, maximum) in breakdown.items():
        st.write(f"**{category}** — {value}/{maximum}")
        st.progress(min(1.0, value / maximum))

    score_df = pd.DataFrame({
        "Category": list(breakdown.keys()),
        "Score": [value for value, _ in breakdown.values()],
        "Max": [maximum for _, maximum in breakdown.values()],
    })

    score_chart = go.Figure()
    score_chart.add_bar(
        x=score_df["Category"],
        y=score_df["Max"],
        name="Maximum",
        marker_color="#e5e7eb",
    )
    score_chart.add_bar(
        x=score_df["Category"],
        y=score_df["Score"],
        name="Your Score",
        marker_color="#7c3aed",
    )
    score_chart.update_layout(
        barmode="overlay",
        title="Score Breakdown",
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e5e7eb" if st.session_state.theme == "Dark" else "#0f172a",
    )
    st.plotly_chart(score_chart, use_container_width=True)

    st.divider()
    st.subheader("🤖 ATS-style Checks")

    checks = ats_checks(data)
    check_df = pd.DataFrame(checks)

    for _, row in check_df.iterrows():
        if row["Status"] == "Pass":
            badge = '<span class="chip ok">PASS</span>'
        else:
            badge = '<span class="chip miss">WARNING</span>'

        st.markdown(
            f'<div class="card"><b>{escape(row["Check"])}</b> {badge}'
            f'<div class="small">{escape(row["Detail"])}</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("✅ Improvement Tips")
    for tip in tips or ["Great CV! Keep it updated."]:
        st.write("• " + tip)

# ----------------------------------------------------------------------------
# JOBS
# ----------------------------------------------------------------------------
with tab4:
    st.subheader("💼 Best Matching Roles & Hiring Companies")

    for job in jobs[:8]:
        with st.expander(
            f"{job['Role']} — {job['Match %']}% match",
            expanded=job is jobs[0],
        ):
            st.progress(job["Match %"] / 100)
            st.markdown("**Companies:** " + ", ".join(job["Companies"]))

            st.markdown("**Matched skills:**")
            if job["Matched"]:
                st.markdown(
                    "".join(
                        f'<span class="chip ok">{escape(skill.title())}</span>'
                        for skill in job["Matched"]
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.write("—")

            st.markdown("**Skills to learn:**")
            if job["Missing"]:
                st.markdown(
                    "".join(
                        f'<span class="chip miss">{escape(skill.title())}</span>'
                        for skill in job["Missing"]
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.write("—")

# ----------------------------------------------------------------------------
# JD MATCHER
# ----------------------------------------------------------------------------
with tab5:
    st.subheader("🎯 Job Description Matcher")
    st.caption("Job description paste karo. App CV skills se match percentage aur missing skills nikalega.")

    jd_text = st.text_area(
        "Paste Job Description",
        height=280,
        placeholder="Paste the full job description here...",
    )

    if st.button("🔍 Match CV with Job Description", type="primary"):
        if not jd_text.strip():
            st.warning("Pehle job description paste karo.")
        else:
            jd_result = match_job_description(data["text"], jd_text)
            st.session_state.jd_result = jd_result

    jd_result = st.session_state.get("jd_result")

    if jd_result:
        if not jd_result["jd_skills"]:
            st.warning("Job description me koi known technical skill detect nahi hui.")
        else:
            score_col1, score_col2, score_col3 = st.columns(3)

            with score_col1:
                st.markdown(
                    f'<div class="kpi"><div class="label">JD Match</div>'
                    f'<div class="value">{jd_result["match_percent"]}%</div></div>',
                    unsafe_allow_html=True,
                )

            with score_col2:
                st.markdown(
                    f'<div class="kpi"><div class="label">Matched Skills</div>'
                    f'<div class="value">{len(jd_result["matched"])}</div></div>',
                    unsafe_allow_html=True,
                )

            with score_col3:
                st.markdown(
                    f'<div class="kpi"><div class="label">Missing Skills</div>'
                    f'<div class="value">{len(jd_result["missing"])}</div></div>',
                    unsafe_allow_html=True,
                )

            st.progress(jd_result["match_percent"] / 100)

            st.markdown('<div class="section-title">✅ Matched Skills</div>', unsafe_allow_html=True)
            if jd_result["matched"]:
                st.markdown(
                    "".join(
                        f'<span class="chip ok">{escape(skill.title())}</span>'
                        for skill in jd_result["matched"]
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.write("—")

            st.markdown('<div class="section-title">⚠️ Missing Skills — Priority Order</div>',
                        unsafe_allow_html=True)
            if jd_result["priority"]:
                for index, skill in enumerate(jd_result["priority"], start=1):
                    st.markdown(
                        f'<div class="card">{index}. <b>{escape(skill.title())}</b>'
                        f' <span class="chip miss">Learn / Add</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.success("Excellent! CV me job description ke important skills already hain.")

# ----------------------------------------------------------------------------
# PROJECTS AND REPORT
# ----------------------------------------------------------------------------
with tab6:
    st.subheader("💡 Suggested Project Topics")

    for category, idea in ideas:
        st.markdown(f"- **[{category}]** {idea}")

    st.divider()
    st.subheader("📥 Download Report")

    editable_data = dict(data)
    editable_data["name"] = st.session_state.editable["name"] or data["name"]
    editable_data["email"] = st.session_state.editable["email"] or data["email"]
    editable_data["phone"] = st.session_state.editable["phone"] or data["phone"]
    editable_data["linkedin"] = st.session_state.editable["linkedin"] or None
    editable_data["github"] = st.session_state.editable["github"] or None
    editable_data["education"] = [
        line.strip()
        for line in st.session_state.editable["education"].splitlines()
        if line.strip()
    ]
    editable_data["experience"] = [
        line.strip()
        for line in st.session_state.editable["experience"].splitlines()
        if line.strip()
    ]
    editable_data["projects"] = [
        line.strip()
        for line in st.session_state.editable["projects"].splitlines()
        if line.strip()
    ]
    editable_data["certifications"] = [
        line.strip()
        for line in st.session_state.editable["certifications"].splitlines()
        if line.strip()
    ]

    try:
        pdf_bytes = build_pdf(
            editable_data,
            total,
            breakdown,
            tips,
            jobs,
            ideas,
            st.session_state.get("jd_result"),
        )

        safe_name = re.sub(r"[^A-Za-z0-9]", "_", editable_data["name"])
        st.download_button(
            "⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=f"CV_Report_{safe_name}.pdf",
            mime="application/pdf",
            type="primary",
        )
    except Exception as error:
        st.error(f"PDF generate nahi hua: {error}")