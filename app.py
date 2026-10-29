"""
from __future__ import annotations
import io, re, os, json, sqlite3, hashlib, secrets, zipfile, random, time, smtplib, ssl
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "resume_analyzer.db"
ADMIN_EMAIL = os.getenv("SCVA_ADMIN_EMAIL", "sufiyan11ko@gmail.com").strip().lower()
MAX_FILE_MB = 10

st.set_page_config(page_title="Smart CV Analyzer Pro", page_icon="📄", layout="wide", initial_sidebar_state="expanded")

# ------------------------------ DATABASE ------------------------------
def connect():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS resume_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL, category TEXT, ats_score REAL NOT NULL,
            found_skills TEXT, missing_skills TEXT, extracted_text TEXT,
            analysis_date TEXT NOT NULL, full_json TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_history_user_date ON resume_history(user_id, analysis_date)")
        cols = {r["name"] for r in c.execute("PRAGMA table_info(resume_history)")}
        if "full_json" not in cols:
            c.execute("ALTER TABLE resume_history ADD COLUMN full_json TEXT")

def query(sql, args=(), one=False, commit=False):
    with connect() as c:
        cur = c.execute(sql, args)
        result = cur.fetchone() if one else cur.fetchall()
        if commit:
            c.commit()
        return result

def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 240_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, expected = stored.split("$", 2)
        if scheme == "pbkdf2_sha256":
            actual = password_hash(password, salt).split("$", 2)[2]
            return secrets.compare_digest(actual, expected)
        if len(stored) == 64 and re.fullmatch(r"[a-f0-9]{64}", stored):
            return secrets.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)
    except Exception:
        pass
    return False

def generate_otp():
    return str(random.randint(100000, 999999))

# ---------- FINAL FIXED EMAIL FUNCTION ----------
def send_otp_email(to_email, otp, purpose="Verification"):
    try:
        try:
            EMAIL_ADDRESS = st.secrets.get("EMAIL_ADDRESS") or os.getenv("EMAIL_ADDRESS")
            EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD") or os.getenv("EMAIL_PASSWORD")
        except Exception:
            EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
            EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            raise ValueError("Email secrets missing")

        EMAIL_PASSWORD = str(EMAIL_PASSWORD).replace(" ", "").strip()
        EMAIL_ADDRESS = str(EMAIL_ADDRESS).strip()

        msg = MIMEText(f"Your Smart CV Analyzer {purpose} OTP is: {otp}\n\nValid for 5 minutes.")
        msg['Subject'] = f"Your OTP {otp} - {purpose}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context, timeout=20) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email Fallback: {e}")
        return True # True taaki OTP screen pe dikha sakein, error na aaye

init_db()

# ------------------------------ SKILL DATABASE ------------------------------
SKILLS_DB = {
    "Programming": ["python","java","c++","c#","javascript","typescript","kotlin","swift","php","ruby","scala","matlab","c","r","go","dart","bash","rust","kotlin"],
    "Web & App Development": ["html","css","react","angular","vue","node.js","nodejs","express","django","flask","fastapi","spring boot","bootstrap","tailwind","next.js","rest api","streamlit","wordpress","jquery","android","flutter","react native","ios"],
    "Data & AI": ["machine learning","deep learning","nlp","natural language processing","computer vision","pandas","numpy","scikit-learn","tensorflow","keras","pytorch","opencv","power bi","tableau","data analysis","data visualization","matplotlib","seaborn","excel","statistics","generative ai","llm","langchain","data science","artificial intelligence","pyspark","spark","data engineering"],
    "Database": ["sql","mysql","postgresql","mongodb","sqlite","oracle","firebase","redis","nosql","microsoft sql server","database design"],
    "Cloud & DevOps": ["aws","azure","gcp","docker","kubernetes","jenkins","ci/cd","linux","terraform","git","github","devops","github actions","ansible","cloud computing"],
    "Mechanical & Automobile": ["autocad","solidworks","catia","ansys","thermodynamics","manufacturing","automobile engineering","cnc","hydraulics","mechanical design","3d printing","cad","cam"],
    "Electrical & Electronics": ["electrical engineering","circuit design","pcb design","plc","scada","embedded systems","vlsi","power systems","wiring","arduino","raspberry pi","microcontrollers","electronics"],
    "Civil & Architecture": ["autocad civil","revit","staad pro","structural analysis","construction management","surveying","estimation","architecture","3d modeling","bim","quantity surveying"],
    "Medical & Healthcare": ["mbbs","nursing","pharmacy","anatomy","physiology","patient care","surgery","diagnosis","medical coding","lab technician","pharmacology","clinical research","healthcare"],
    "Finance & Commerce": ["accounting","tally","gst","auditing","financial modeling","investment banking","stock market","ca","cfa","budgeting","taxation","banking","financial analysis","bookkeeping","quickbooks","accounts payable"],
    "Business & Management": ["business management","project management","agile","scrum","operations management","supply chain","business analysis","entrepreneurship","hr management","recruitment","business development","microsoft project"],
    "Marketing & Sales": ["digital marketing","seo","sem","social media marketing","content marketing","google analytics","sales","crm","branding","market research","advertising","email marketing","hubspot"],
    "Education & Teaching": ["teaching","curriculum design","classroom management","lesson planning","educational psychology","communication","subject matter expert","e-learning","tutoring"],
    "Hospitality & Tourism": ["hotel management","hospitality","cooking","culinary arts","food safety","front office","housekeeping","tourism management","event management","customer service","food and beverage"],
    "Legal & Law": ["law","legal research","contract drafting","advocacy","corporate law","criminal law","civil law","legal writing","compliance","litigation"],
    "Design & Creative": ["graphic design","photoshop","illustrator","figma","ui/ux","video editing","premiere pro","after effects","fashion design","interior design","animation","canva","adobe xd","typography"],
    "Agriculture & Environment": ["agriculture","agronomy","horticulture","soil science","organic farming","environmental science","forestry","irrigation","pest control","sustainability"],
    "Government & Defense": ["upsc","ssc","police","army","defense","public administration","government policies","law enforcement","disaster management"],
    "Soft Skills": ["communication","leadership","teamwork","problem solving","time management","critical thinking","adaptability","creativity","collaboration","presentation","attention to detail","negotiation","customer service"]
}
AMBIGUOUS = {"c", "r", "go", "ca", "law", "sales", "sql"}
LABELS = {"node.js":"Node.js","nodejs":"Node.js","next.js":"Next.js","ci/cd":"CI/CD","ui/ux":"UI/UX","power bi":"Power BI","rest api":"REST API","scikit-learn":"Scikit-learn","c++":"C++","c#":"C#","ios":"iOS","nosql":"NoSQL","mysql":"MySQL","postgresql":"PostgreSQL","mongodb":"MongoDB","javascript":"JavaScript","typescript":"TypeScript","tensorflow":"TensorFlow","pytorch":"PyTorch","opencv":"OpenCV","fastapi":"FastAPI","github":"GitHub","wordpress":"WordPress","jquery":"jQuery","langchain":"LangChain","sqlite":"SQLite","spring boot":"Spring Boot","react native":"React Native","aws":"AWS","gcp":"GCP","html":"HTML","css":"CSS","nlp":"NLP","llm":"LLM","seo":"SEO","gst":"GST","plc":"PLC","scada":"SCADA","mbbs":"MBBS","ca":"CA","cfa":"CFA"}
def pretty(s):
    x=s.lower()
    return LABELS.get(x, x.upper() if len(x) <= 3 else x.title())
SECTION_ALIASES = {
    "education": ["education","academic qualification","academic qualifications","academics","qualifications","academic background","educational qualification"],
    "experience": ["experience","work experience","professional experience","employment history","internship","internships","work history","internship experience","training","employment"],
    "projects": ["projects","academic projects","personal projects","project work","key projects","major projects","project experience"],
    "skills": ["skills","technical skills","key skills","core competencies","skills & tools","technical proficiency","it skills","areas of expertise"],
    "certifications": ["certifications","certificates","courses","training & certifications","certifications & courses","licenses"],
}
ROLE_SKILLS = {
 "Data Analyst":["sql","excel","power bi","tableau","python","pandas","data analysis","data visualization","statistics"],
 "Data Scientist":["python","machine learning","pandas","numpy","scikit-learn","sql","statistics","deep learning","data visualization"],
 "AI / ML Engineer":["python","tensorflow","pytorch","deep learning","nlp","computer vision","machine learning","docker"],
 "Python / Backend Developer":["python","django","flask","fastapi","sql","postgresql","rest api","git","docker"],
 "Frontend Developer":["html","css","javascript","react","typescript","bootstrap","tailwind","git","figma"],
 "Full Stack Developer":["html","css","javascript","react","node.js","mongodb","express","sql","git","rest api"],
 "Java Developer":["java","spring boot","mysql","sql","rest api","git"],
 "DevOps / Cloud Engineer":["aws","azure","docker","kubernetes","linux","jenkins","ci/cd","terraform","git"],
 "Mobile Developer":["android","kotlin","java","flutter","dart","firebase","react native"],
 "Software Tester / QA":["selenium","jira","sql","java","python","git","testing"],
 "Mechanical Engineer":["autocad","solidworks","catia","ansys","mechanical design","manufacturing"],
 "Electrical Engineer":["electrical engineering","circuit design","plc","scada","embedded systems","power systems"],
 "Civil Engineer":["autocad civil","revit","staad pro","structural analysis","construction management","surveying"],
 "Accountant / Finance":["accounting","tally","gst","auditing","financial modeling","taxation","financial analysis"],
 "Digital Marketing":["digital marketing","seo","sem","social media marketing","content marketing","google analytics"],
 "UI/UX Designer":["figma","ui/ux","user research","prototyping","wireframing","graphic design"],
 "HR / Recruitment":["hr management","recruitment","communication","interviewing","business management"],
}
COMPANIES = ["TCS","Infosys","Accenture","Wipro","Capgemini","Cognizant","Deloitte","IBM","Microsoft","Amazon","Google","HCLTech","Tech Mahindra","Zoho","Freshworks"]
PROJECT_IDEAS = {
 "Data & AI":["Resume–Job Description Matcher using NLP","Customer Churn Prediction Dashboard","Product Review Sentiment Analysis","Sales Forecasting Dashboard"],
 "Web & App Development":["Full-Stack Job Portal with Role-Based Login","Portfolio Website with Analytics","Personal Finance Tracker","Online Examination System"],
 "Programming":["Algorithm Visualizer","Code Plagiarism Detector","Task Automation Toolkit"],
 "Database":["Inventory Management with SQL Analytics","Hospital Management Database"],
 "Cloud & DevOps":["Dockerized Web App with CI/CD","Cloud Monitoring Dashboard"],
 "Mechanical & Automobile":["CAD Model and Stress Analysis","Vehicle Maintenance Prediction"],
 "Electrical & Electronics":["IoT Energy Monitoring System","Smart Home Automation"],
 "Civil & Architecture":["Building Cost Estimation Tool","3D Building Model with BIM"],
 "Finance & Commerce":["Personal Budget and GST Tracker","Financial KPI Dashboard"],
 "Marketing & Sales":["SEO Audit Dashboard","Campaign Performance Analytics"],
 "Design & Creative":["Mobile App UI Kit in Figma","Brand Identity and Design System"],
 "Medical & Healthcare":["Clinic Appointment Management","Healthcare Inventory Tracker"],
}
def pattern_for(skill):
    aliases = {"node.js":r"node\.?js","nodejs":r"node\.?js","c++":r"c\+\+","c#":r"c\#","ci/cd":r"ci\s*/\s*cd","ui/ux":r"ui\s*/\s*ux"}
    p=aliases.get(skill.lower(), re.escape(skill))
    return re.compile(r"(?<![A-Za-z0-9+#.])"+p+r"(?![A-Za-z0-9+#])", re.I)
def found_skills(text, skill_section=""):
    found={}
    for cat, skills in SKILLS_DB.items():
        for s in skills:
            hay=skill_section if s in AMBIGUOUS else text
            if hay and pattern_for(s).search(hay):
                found.setdefault(cat,[])
                lab=pretty(s)
                if lab not in found[cat]: found[cat].append(lab)
    return found
def split_sections(text):
    lookup={a:k for k, aliases in SECTION_ALIASES.items() for a in aliases}
    sections={k:[] for k in SECTION_ALIASES}
    cur=None
    for raw in text.splitlines():
        line=raw.strip()
        if not line: continue
        key=re.sub(r"[^a-z &/]", "", line.lower()).strip()
        if len(line)<55 and key in lookup:
            cur=lookup[key]; continue
        if cur: sections[cur].append(line)
    return sections

IMAGE_EXTS=(".png",".jpg",".jpeg",".jfif",".webp",".bmp",".tif",".tiff",".gif",".heic",".heif")
def extract_text(filename, raw):
    low=filename.lower()
    if len(raw)>MAX_FILE_MB*1024*1024:
        raise ValueError(f"File is larger than {MAX_FILE_MB} MB.")
    if raw.startswith(b"%PDF") or low.endswith(".pdf"):
        import pdfplumber
        pages=[]
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages[:40]:
                pages.append(page.extract_text() or "")
        text="\n".join(pages)
        if len(text.strip())<40:
            try: text=ocr_bytes(raw, "pdf")
            except Exception: pass
        return text
    if low.endswith(".docx") or raw[:2]==b"PK":
        import docx
        d=docx.Document(io.BytesIO(raw))
        parts=[p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows: parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts)
    if low.endswith(IMAGE_EXTS):
        from PIL import Image
        img=Image.open(io.BytesIO(raw))
        return ocr_image(img)
    return raw.decode("utf-8", errors="ignore")

def ocr_bytes(raw, kind="pdf"):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        texts=[]
        for page in pdf.pages[:10]:
            texts.append(ocr_image(page.to_image(resolution=180).original))
        return "\n".join(texts)

def ocr_image(img):
    import pytesseract
    from PIL import ImageOps
    img=ImageOps.exif_transpose(img)
    if img.mode not in ("RGB","L"): img=img.convert("RGB")
    img=ImageOps.autocontrast(img.convert("L"))
    if max(img.size)<1800:
        scale=1800/max(img.size); img=img.resize((int(img.width*scale),int(img.height*scale)))
    return pytesseract.image_to_string(img, lang="eng", config="--psm 6")

EMAIL_RE=re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE=re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}")
LINKEDIN_RE=re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%]+",re.I)
GITHUB_RE=re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+",re.I)
ACTION_VERBS=["developed","designed","built","created","implemented","improved","optimized","automated","led","managed","analyzed","deployed","tested","reduced","increased","achieved","collaborated","integrated","maintained","researched"]
METRIC_RE=re.compile(r"\d+\s?%|\d+\+|\$\s?\d+|₹\s?\d+")
DEGREE_RE=re.compile(r"\b(b\.?\s?tech|m\.?\s?tech|bca|mca|bba|mba|b\.?\s?sc|m\.?\s?sc|b\.?\s?com|m\.?\s?com|bachelor|master|doctorate|12th|10th|hsc|ssc|diploma|ph\.?\s?d|degree)\b",re.I)
def get_name(text,email):
    skip=("resume","curriculum","vitae","profile","objective","summary","contact","address","email","phone","mobile","github","linkedin")
    for line in [x.strip() for x in text.splitlines() if x.strip()][:12]:
        if "@" in line or any(x in line.lower() for x in skip) or re.search(r"\d",line): continue
        words=re.sub(r"[^A-Za-z .'-]"," ",line).split()
        if 2<=len(words)<=4: return " ".join(w.capitalize() for w in words)
    if email!="Not found":
        return re.sub(r"[\d._-]+"," ",email.split("@")[0]).title().strip() or "Not found"
    return "Not found"
def extract_phone(text):
    for m in PHONE_RE.finditer(text):
        digits=re.sub(r"\D","",m.group())
        if 10<=len(digits)<=13: return m.group().strip()
    return "Not found"
def analyze_text(text):
    sec=split_sections(text)
    email_m=EMAIL_RE.search(text); email=email_m.group() if email_m else "Not found"
    li=LINKEDIN_RE.search(text); gh=GITHUB_RE.search(text)
    skills=found_skills(text,"\n".join(sec["skills"]))
    education=sec["education"] or [x.strip() for x in text.splitlines() if DEGREE_RE.search(x)]
    cert=sec["certifications"] or [x.strip() for x in text.splitlines() if re.search(r"\b(certified|certification|certificate|course|specialization|bootcamp)\b",x,re.I)]
    exp=sec["experience"]
    projects=sec["projects"]
    allskills=list(dict.fromkeys(s for items in skills.values() for s in items))
    words=len(text.split())
    contact=(3 if get_name(text,email)!="Not found" else 0)+(3 if email!="Not found" else 0)+(2 if extract_phone(text)!="Not found" else 0)+(2 if li or gh else 0)
    tech=sum(len(v) for k,v in skills.items() if k!="Soft Skills")
    cats=sum(bool(v) for k,v in skills.items() if k!="Soft Skills")
    skillscore=min(18,tech*1.5)+min(5,cats*1.25)+(2 if skills.get("Soft Skills") else 0)
    fmt=10 if 250<=words<=900 else 6 if 150<=words<=1300 else 3
    fmt=min(15,fmt+(2 if METRIC_RE.search(text) else 0)+(3 if sum(bool(re.search(r"\b"+v+r"\b",text,re.I)) for v in ACTION_VERBS)>=3 else 0))
    breakdown={"Contact Info":(contact,10),"Skills":(round(min(skillscore,25),1),25),"Education":(min(10,4+len(education)*2) if education else 0,10),"Experience":(min(20,8+len(exp)*1.2) if exp else 0,20),"Projects":(min(15,len(projects)*5) if projects else 0,15),"Certifications":(min(5,len(cert)*1.5) if cert else 0,5),"Formatting & Impact":(fmt,15)}
    score=round(sum(v for v,_ in breakdown.values()))
    tips=[]
    if not li and not gh: tips.append("Add a LinkedIn or GitHub profile link.")
    if tech<8: tips.append("Add relevant technical or role-specific skills that you genuinely have.")
    if not education: tips.append("Add your education, institution and graduation year.")
    if not exp: tips.append("Include internships, training, freelance, volunteering or work experience if applicable.")
    if len(projects)<2: tips.append("Add 2–3 projects with your role, tools used and results.")
    if not cert: tips.append("Add relevant courses or certifications if you have them.")
    if not METRIC_RE.search(text): tips.append("Quantify impact where truthful (e.g. time saved, users served, accuracy achieved).")
    if words<250: tips.append("Your CV is short; add useful project and experience details.")
    if words>900: tips.append("Keep the CV concise, usually 1–2 pages for an early-career applicant.")
    roles=[]; have={x.lower() for x in allskills}
    for role, req in ROLE_SKILLS.items():
        matched=[s for s in req if pretty(s).lower() in have or s in have]
        roles.append({"Role":role,"Match %":round(100*len(matched)/len(req)),"Matched":matched,"Missing":[s for s in req if s not in matched],"Companies":COMPANIES[:7]})
    roles.sort(key=lambda x:x["Match %"],reverse=True)
    return {"text":text,"name":get_name(text,email),"email":email,"phone":extract_phone(text),"linkedin":li.group() if li else "","github":gh.group() if gh else "","skills":skills,"all_skills":allskills,"education":education[:15],"experience":exp[:20],"projects":projects[:15],"certifications":cert[:15],"word_count":words,"score":score,"breakdown":breakdown,"tips":tips,"jobs":roles}

def jd_match(cv_text,jd_text):
    jd_skills=[]
    for cat,skills in SKILLS_DB.items():
        if cat=="Soft Skills": continue
        for s in skills:
            if s in AMBIGUOUS: continue
            if pattern_for(s).search(jd_text) and s not in jd_skills: jd_skills.append(s)
    matched=[s for s in jd_skills if pattern_for(s).search(cv_text)]
    missing=[s for s in jd_skills if s not in matched]
    priority=sorted(missing,key=lambda s:(0 if s in {"python","sql","excel","machine learning","javascript","aws"} else 1,s))
    return {"jd_skills":jd_skills,"matched":matched,"missing":missing,"priority":priority,"match_percent":round(100*len(matched)/len(jd_skills)) if jd_skills else 0}
def grade(score):
    if score>=80:return "Excellent 🌟"
    if score>=65:return "Good 👍"
    if score>=45:return "Average ⚠️"
    return "Needs Work ❌"
def project_ideas(skills):
    cats=sorted(skills,key=lambda c:len(skills[c]),reverse=True)
    out=[]
    for cat in cats:
        for idea in PROJECT_IDEAS.get(cat,[]):
            if (cat,idea) not in out: out.append((cat,idea))
    for idea in ["Portfolio Website with Blog","AI FAQ Chatbot","Weather and Air Quality Dashboard"]:
        out.append(("General",idea))
    return out[:12]
def pdf_report(d):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.6*cm,rightMargin=1.6*cm,topMargin=1.5*cm,bottomMargin=1.5*cm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Smallx",parent=styles["BodyText"],fontSize=8,leading=10))
    def p(x,style="BodyText"):
        return Paragraph(escape(str(x)).replace("\n","<br/>"),styles[style])
    story=[p("Smart CV Analyzer Pro Report","Title"),p("Generated: "+datetime.now().strftime("%d %b %Y, %H:%M")),Spacer(1,10)]
    story += [p(f"Candidate: {d['name']}"),p(f"Email: {d['email']} | Phone: {d['phone']}"),p(f"CV Score: {d['score']}/100 — {grade(d['score'])}"),p(f"Word count: {d['word_count']}"),Spacer(1,8)]
    rows=[[p("Section","Smallx"),p("Score","Smallx"),p("Maximum","Smallx")]]
    rows += [[p(k,"Smallx"),p(v,"Smallx"),p(m,"Smallx")] for k,(v,m) in d["breakdown"].items()]
    t=Table(rows,colWidths=[10*cm,3*cm,3*cm],repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#4f46e5")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [t,Spacer(1,12)]
    for title,key in [("Skills","all_skills"),("Education","education"),("Experience","experience"),("Projects","projects"),("Certifications","certifications")]:
        story.append(p(title,"Heading2"))
        values=d[key] or ["Not detected"]
        story.append(p(", ".join(values) if key in ("Skills",) else "\n".join("• "+str(x) for x in values)))
    story.append(p("Top job matches","Heading2"))
    for j in d["jobs"][:6]: story.append(p(f"{j['Role']}: {j['Match %']}% — matched: {', '.join(j['Matched']) or 'none'}"))
    story.append(p("Improvement tips","Heading2"))
    for tip in d["tips"] or ["Keep your CV updated."]: story.append(p("• "+tip))
    doc.build(story); return buf.getvalue()

# ------------------------------ UI ------------------------------
css_fix = "<style>.stApp{background:#0b1020;color:#e5e7eb}.block-container{max-width:1450px;padding-top:1.2rem}.hero{padding:28px 32px;border-radius:20px;background:linear-gradient(120deg,#4338ca,#7c3aed,#db2777);margin-bottom:18px}.hero h1,.hero p{color:white!important;margin:0}.hero p{margin-top:8px}div[data-testid='stMetric']{background:#111827;border:1px solid #2b3245;padding:14px;border-radius:14px}.card{background:#111827;border:1px solid #2b3245;border-radius:14px;padding:16px;margin:8px 0}.muted{color:#9ca3af}.stButton button,.stDownloadButton button{border-radius:10px;font-weight:700}</style>"
st.markdown(css_fix, unsafe_allow_html=True)
for k,v in {"logged_in":False,"user_id":None,"user_name":"","user_email":"","page":"Analyzer"}.items(): st.session_state.setdefault(k,v)

def hero(title,sub):
    st.markdown(f'<div class="hero"><h1>{escape(title)}</h1><p>{escape(sub)}</p></div>',unsafe_allow_html=True)
def chips(items):
    return " · ".join(str(x) for x in items) if items else "None detected"
def logout():
    for k in list(st.session_state.keys()):
        if k not in ("page",): del st.session_state[k]
    st.session_state.update(logged_in=False,user_id=None,user_name="",user_email="")
    st.rerun()

def auth_screen():
    hero("📄 Smart CV Analyzer Pro","Analyze your CV, discover job matches, and keep track of your progress.")
    _,mid,_=st.columns([1,1.5,1])
    with mid:
        login,signup,reset=st.tabs(["🔐 Login","📝 Create account","🔑 Reset with OTP"])
        with login:
            e=st.text_input("Email",key="login_email").strip().lower()
            p=st.text_input("Password",type="password",key="login_pass")
            if st.button("Login",type="primary",use_container_width=True):
                u=query("SELECT * FROM users WHERE email=?",(e,),one=True)
                if u and verify_password(p,u["password_hash"]):
                    st.session_state.update(logged_in=True,user_id=u["id"],user_name=u["name"],user_email=u["email"])
                    st.rerun()
                else: st.error("Email or password is incorrect.")
        with signup:
            st.info("Email pe OTP jayega - Agar email na aaye to OTP yahi dikhega")
            n=st.text_input("Full name",key="signup_name")
            e2=st.text_input("Email",key="signup_email").strip().lower()
            p1=st.text_input("Password (min 8 chars)",type="password",key="signup_pass")
            if st.button("Send OTP"):
                if not n or not e2 or len(p1)<8:
                    st.error("Sahi bharo")
                else:
                    otp = generate_otp()
                    send_otp_email(e2, otp, "Signup")
                    st.session_state["signup_otp"] = otp
                    st.session_state["signup_data"] = (n, e2, p1)
                    st.session_state["otp_time"] = time.time()
                    st.success(f"OTP sent to {e2}")
                    st.info(f"👉 Tera OTP hai: **{otp}** - Isko neeche daal de")
            otp_input = st.text_input("Enter OTP", key="signup_otp_input")
            if st.button("Verify & Create Account",type="primary",use_container_width=True):
                if otp_input and otp_input == st.session_state.get("signup_otp"):
                    n2,e2,p2 = st.session_state["signup_data"]
                    try:
                        query("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(n2.strip(),e2,password_hash(p2),datetime.now().strftime("%Y-%m-%d %H:%M:%S")),commit=True)
                        st.success("Account created! Login karo")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("Email already registered")
                else:
                    st.error(f"Invalid OTP. Sahi OTP: {st.session_state.get('signup_otp','')}")
        with reset:
            st.info("Ab naam ki zarurat nahi, sirf OTP se reset hoga!")
            er=st.text_input("Registered email",key="reset_email").strip().lower()
            if st.button("Send Reset OTP"):
                u=query("SELECT id FROM users WHERE email=?",(er,),one=True)
                if not u:
                    st.error("Email registered nahi hai")
                else:
                    otp = generate_otp()
                    send_otp_email(er, otp, "Password Reset")
                    st.session_state["reset_otp"] = otp
                    st.session_state["reset_email"] = er
                    st.session_state["reset_otp_time"] = time.time()
                    st.success(f"OTP sent to {er}")
                    st.info(f"👉 Reset OTP: **{otp}**")
            otp_r = st.text_input("Enter OTP",key="reset_otp_input")
            np=st.text_input("New password",type="password",key="reset_pass_new")
            if st.button("Verify OTP & Reset",use_container_width=True):
                if otp_r and otp_r == st.session_state.get("reset_otp"):
                    if len(np) < 8:
                        st.error("Password 8 char ka hona chahiye")
                    else:
                        query("UPDATE users SET password_hash=? WHERE email=?",(password_hash(np), st.session_state["reset_email"]),commit=True)
                        st.success("Password reset ho gaya!")
                else:
                    st.error(f"Invalid OTP. Sahi OTP: {st.session_state.get('reset_otp','')}")

if not st.session_state.logged_in:
    auth_screen()
    st.stop()

uid=st.session_state.user_id
with st.sidebar:
    st.markdown("## 📄 Smart CV Analyzer")
    st.success(f"Welcome, {st.session_state.user_name}")
    page=st.radio("Navigation",["🔍 Analyzer","📚 History","👤 Profile"]+(["🛡️ Admin Panel"] if st.session_state.user_email.lower()==ADMIN_EMAIL else []),key="nav")
    st.divider()
    st.caption(f"Signed in as {st.session_state.user_email}")
    if st.button("🚪 Logout",use_container_width=True): logout()

if page.startswith("🔍"):
    hero("Smart CV Analyzer Pro","Upload a CV or paste its text to get an ATS-style score, skills, job matches and actionable feedback.")
    left,right=st.columns([1,2.1])
    with left:
        mode=st.radio("Input method",["Upload file","Paste text"])
        if mode=="Upload file":
            uploaded=st.file_uploader("CV file (PDF, DOCX, TXT, JPG, PNG)",type=["pdf","docx","txt","jpg","jpeg","png","webp","bmp","tif","tiff"])
            raw=uploaded.getvalue() if uploaded else None
            filename=uploaded.name if uploaded else "resume.txt"
        else:
            pasted=st.text_area("Paste CV text",height=280,placeholder="Paste the complete resume text here...")
            raw=pasted.encode("utf-8") if pasted.strip() else None
            filename="Pasted_CV.txt"
        run=st.button("🚀 Analyze CV",type="primary",use_container_width=True,disabled=not raw)
    if run and raw:
        try:
            with st.spinner("Extracting and analyzing your CV..."):
                text=extract_text(filename,raw)
                if len(text.strip())<30: st.error("Very little text was extracted.")
                else:
                    result=analyze_text(text)
                    result["filename"]=filename
                    result["ideas"]=project_ideas(result["skills"])
                    payload=json.dumps(result,ensure_ascii=False)
                    top=result["jobs"][0] if result["jobs"] else {"Role":"General"}
                    query("INSERT INTO resume_history(user_id,file_name,category,ats_score,found_skills,missing_skills,extracted_text,analysis_date,full_json) VALUES(?,?,?,?,?,?,?,?,?)",
                      (uid,filename,top["Role"],result["score"],json.dumps(result["all_skills"],ensure_ascii=False),json.dumps(top["Missing"],ensure_ascii=False),text,datetime.now().strftime("%Y-%m-%d %H:%M"),payload),commit=True)
                    st.session_state["current_result"]=result
                    st.session_state.pop("jd_result",None)
                    st.success("Analysis complete and saved to your history.")
        except Exception as e: st.error(f"Could not analyze this file: {e}")
    d=st.session_state.get("current_result")
    if d:
        st.divider()
        tabs=st.tabs(["📊 Dashboard","🧾 Extracted details","🤖 ATS checks","💼 Job matches","🎯 JD matcher","💡 Projects & report"])
        with tabs[0]:
            a,b,c,e=st.columns(4)
            a.metric("CV Score",f"{d['score']}/100",grade(d["score"]))
            b.metric("Skills detected",len(d["all_skills"]))
            c.metric("Projects detected",len(d["projects"]))
            e.metric("Word count",d["word_count"])
            g=go.Figure(go.Indicator(mode="gauge+number",value=d["score"],title={"text":grade(d["score"])},gauge={"axis":{"range":[0,100]},"steps":[{"range":[0,45],"color":"#fee2e2"},{"range":[45,65],"color":"#fef3c7"},{"range":[65,80],"color":"#dbeafe"},{"range":[80,100],"color":"#dcfce7"}]}))
            g.update_layout(height=280,margin=dict(t=50,b=10),paper_bgcolor="rgba(0,0,0,0)",font_color="#e5e7eb")
            st.plotly_chart(g,use_container_width=True)
            x,y=st.columns(2)
            with x:
                st.subheader("Score breakdown")
                st.plotly_chart(px.bar(pd.DataFrame([{"Section":k,"Score":v,"Maximum":m} for k,(v,m) in d["breakdown"].items()]),x="Section",y=["Score","Maximum"],barmode="group"),use_container_width=True)
            with y:
                if d["skills"]:
                    sdf=pd.DataFrame([{"Category":k,"Skills":len(v)} for k,v in d["skills"].items()])
                    st.plotly_chart(px.pie(sdf,names="Category",values="Skills",hole=.45,title="Skill distribution"),use_container_width=True)
            st.subheader("Top role matches")
            showjobs=pd.DataFrame([{"Role":j["Role"],"Match %":j["Match %"]} for j in d["jobs"][:8]])
            st.plotly_chart(px.bar(showjobs.sort_values("Match %"),x="Match %",y="Role",orientation="h",range_x=[0,100]),use_container_width=True)
        with tabs[1]:
            st.subheader("Extracted candidate details")
            for title,key in [("Education","education"),("Experience","experience"),("Projects","projects"),("Certifications","certifications")]:
                st.markdown("**"+title+"**")
                st.write("\n".join(d.get(key,[])) or "Not detected")
            st.markdown("**Detected skills by category**")
            for cat,items in d["skills"].items(): st.write(f"**{cat}:** {', '.join(items)}")
            with st.expander("View extracted raw text"): st.text(d["text"])
        with tabs[2]:
            st.subheader("ATS-style checklist")
            words=d["word_count"]; checks=[("Email and phone",d["email"]!="Not found" and d["phone"]!="Not found","Keep contact information easy to find."),("LinkedIn / GitHub",bool(d["linkedin"] or d["github"]),"Add a professional profile link if relevant."),("Skills",bool(d["skills"]),"Use a clearly labelled skills section."),("Education",bool(d["education"]),"Include qualification, institution and year."),("Projects",len(d["projects"])>=2,"Include 2–3 relevant projects."),("Measurable impact",bool(METRIC_RE.search(d["text"])),"Add truthful numbers/results where possible."),("CV length",250<=words<=900,f"Current word count: {words}")]
            for title,ok,detail in checks:
                st.markdown(f'<div class="card"><b>{"✅ PASS" if ok else "⚠️ IMPROVE"} — {escape(title)}</b><br><span class="muted">{escape(detail)}</span></div>',unsafe_allow_html=True)
            st.subheader("Improvement plan")
            for tip in d["tips"]: st.write("• "+tip)
        with tabs[3]:
            st.subheader("Role match estimates")
            for j in d["jobs"][:12]:
                with st.expander(f"{j['Role']} — {j['Match %']}% match"):
                    st.progress(j["Match %"]/100)
                    st.write("**Matched skills:**",", ".join(j["Matched"]) or "None")
                    st.write("**Skills to learn:**",", ".join(j["Missing"]) or "None")
                    st.write("**Example employers:**",", ".join(j["Companies"]))
        with tabs[4]:
            st.subheader("Job Description Matcher")
            jd=st.text_area("Paste the job description",height=220,key="jd_area")
            if st.button("Match job description",type="primary"):
                if not jd.strip(): st.warning("Paste a job description first.")
                else: st.session_state["jd_result"]=jd_match(d["text"],jd)
            jr=st.session_state.get("jd_result")
            if jr:
                a,b,c=st.columns(3); a.metric("Keyword match",f"{jr['match_percent']}%"); b.metric("Matched",len(jr["matched"])); c.metric("Missing",len(jr["missing"]))
                st.write("**Matched:**",", ".join(jr["matched"]) or "None")
                st.write("**Missing:**",", ".join(jr["priority"]) or "None")
        with tabs[5]:
            st.subheader("Project ideas based on detected skills")
            for cat,idea in d["ideas"]: st.write(f"**{cat}:** {idea}")
            st.divider()
            try:
                pdf=pdf_report(d)
                safe=re.sub(r"[^A-Za-z0-9]+","_",d.get("name","Candidate")).strip("_") or "Candidate"
                st.download_button("⬇️ Download PDF report",pdf,file_name=f"CV_Report_{safe}.pdf",mime="application/pdf",type="primary")
            except Exception as e: st.error(f"PDF generation failed: {e}")

elif page.startswith("📚"):
    hero("📚 Analysis History","Review, search, download or delete your previous CV scans.")
    rows=query("SELECT id,analysis_date,file_name,category,ats_score,found_skills,missing_skills,extracted_text,full_json FROM resume_history WHERE user_id=? ORDER BY id DESC",(uid,))
    df=pd.DataFrame([dict(r) for r in rows])
    if df.empty: st.info("No scans yet. Analyze a CV to start building your history.")
    else:
        a,b,c=st.columns(3); a.metric("Total scans",len(df)); b.metric("Average score",f"{df['ats_score'].mean():.1f}/100"); c.metric("Best score",f"{df['ats_score'].max():.0f}/100")
        st.dataframe(df[["analysis_date","file_name","category","ats_score"]].rename(columns={"analysis_date":"Date","file_name":"File","category":"Best role","ats_score":"Score"}),use_container_width=True,hide_index=True)
        for _,r in df.iterrows():
            with st.expander(f"{r['file_name']} · {r['ats_score']}/100 · {r['analysis_date']}"):
                st.write("**Best matching role:**",r["category"])
                st.write("**Found skills:**",chips(json.loads(r["found_skills"] or "[]")))
                with st.expander("Extracted text"): st.text(r["extracted_text"] or "")
                if st.button("🗑️ Delete this scan",key=f"delhist{int(r['id'])}"):
                    query("DELETE FROM resume_history WHERE id=? AND user_id=?",(int(r["id"]),uid),commit=True); st.rerun()

elif page.startswith("👤"):
    hero("👤 My Profile","Manage account details and password.")
    u=query("SELECT * FROM users WHERE id=?",(uid,),one=True)
    a,b=st.columns(2); a.metric("Name",u["name"]); b.metric("Email",u["email"])
    c,d=st.columns(2); c.metric("Member since",u["created_at"]); d.metric("Total scans",query("SELECT COUNT(*) AS n FROM resume_history WHERE user_id=?",(uid,),one=True)["n"])
    st.subheader("Change password")
    old=st.text_input("Current password",type="password")
    new=st.text_input("New password (minimum 8 characters)",type="password")
    confirm=st.text_input("Confirm new password",type="password")
    if st.button("Update password",type="primary"):
        if not verify_password(old,u["password_hash"]): st.error("Current password is incorrect.")
        elif len(new)<8: st.error("New password must be at least 8 characters.")
        elif new!=confirm: st.error("Passwords do not match.")
        else: query("UPDATE users SET password_hash=? WHERE id=?",(password_hash(new),uid),commit=True); st.success("Password updated.")

else:
    hero("🛡️ Admin Panel","Administrative overview.")
    if st.session_state.user_email.lower()!=ADMIN_EMAIL:
        st.error("Access denied."); st.stop()
    users=query("SELECT id,name,email,created_at FROM users ORDER BY id DESC")
    udf=pd.DataFrame([dict(r) for r in users])
    st.dataframe(udf,use_container_width=True,hide_index=True)

st.markdown("---")
st.markdown("<p style='text-align:center;color:#9ca3af'>Built with ❤️ by Sufiyan · Smart CV Analyzer Pro</p>",unsafe_allow_html=True)