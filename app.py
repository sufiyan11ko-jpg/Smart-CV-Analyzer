"""
Smart CV Analyzer Pro - FINAL CLEAN
"""
from __future__ import annotations
import io, re, os, json, sqlite3, hashlib, secrets, random, time, smtplib, ssl
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

def connect():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS resume_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, file_name TEXT NOT NULL, category TEXT, ats_score REAL NOT NULL, found_skills TEXT, missing_skills TEXT, extracted_text TEXT, analysis_date TEXT NOT NULL, full_json TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_history_user_date ON resume_history(user_id, analysis_date)')
        cols = {r["name"] for r in c.execute("PRAGMA table_info(resume_history)")}
        if "full_json" not in cols:
            c.execute('ALTER TABLE resume_history ADD COLUMN full_json TEXT')

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

def send_otp_email(to_email, otp, purpose="Verification"):
    try:
        try:
            EMAIL_ADDRESS = st.secrets.get("EMAIL_ADDRESS") or os.getenv("EMAIL_ADDRESS")
            EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD") or os.getenv("EMAIL_PASSWORD")
        except Exception:
            EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
            EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            raise ValueError("Missing")
        EMAIL_PASSWORD = str(EMAIL_PASSWORD).replace(" ", "").strip()
        EMAIL_ADDRESS = str(EMAIL_ADDRESS).strip()
        msg = MIMEText(f"Your OTP is: {otp} Valid 5 min")
        msg['Subject'] = f"OTP {otp} - {purpose}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context, timeout=20) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(e)
        return True

init_db()

SKILLS_DB = {
    "Programming": ["python","java","c++","c#","javascript","typescript","kotlin","swift","php","ruby","scala","matlab","c","r","go","dart","bash","rust"],
    "Web & App Development": ["html","css","react","angular","vue","node.js","nodejs","express","django","flask","fastapi","spring boot","bootstrap","tailwind","next.js","rest api","streamlit","wordpress","jquery","android","flutter","react native","ios"],
    "Data & AI": ["machine learning","deep learning","nlp","natural language processing","computer vision","pandas","numpy","scikit-learn","tensorflow","keras","pytorch","opencv","power bi","tableau","data analysis","data visualization","matplotlib","seaborn","excel","statistics","generative ai","llm","langchain","data science","artificial intelligence","pyspark","spark","data engineering"],
    "Database": ["sql","mysql","postgresql","mongodb","sqlite","oracle","firebase","redis","nosql","microsoft sql server","database design"],
    "Cloud & DevOps": ["aws","azure","gcp","docker","kubernetes","jenkins","ci/cd","linux","terraform","git","github","devops","github actions","ansible","cloud computing"],
    "Soft Skills": ["communication","leadership","teamwork","problem solving","time management","critical thinking","adaptability","creativity","collaboration","presentation","attention to detail","negotiation","customer service"]
}
AMBIGUOUS = {"c", "r", "go", "ca", "law", "sales", "sql"}
LABELS = {"node.js":"Node.js","nodejs":"Node.js","next.js":"Next.js","ci/cd":"CI/CD","ui/ux":"UI/UX","power bi":"Power BI","rest api":"REST API","scikit-learn":"Scikit-learn","c++":"C++","c#":"C#"}
def pretty(s):
    x=s.lower()
    return LABELS.get(x, x.upper() if len(x) <= 3 else x.title())
SECTION_ALIASES = {
    "education": ["education","academic qualification","academics","qualifications"],
    "experience": ["experience","work experience","professional experience","employment history","internship"],
    "projects": ["projects","academic projects","personal projects","project work"],
    "skills": ["skills","technical skills","key skills","core competencies"],
    "certifications": ["certifications","certificates","courses"],
}
ROLE_SKILLS = {
 "Data Analyst":["sql","excel","power bi","tableau","python","pandas","data analysis","data visualization","statistics"],
 "Data Scientist":["python","machine learning","pandas","numpy","scikit-learn","sql","statistics","deep learning"],
 "Python / Backend Developer":["python","django","flask","fastapi","sql","postgresql","rest api","git","docker"],
 "Frontend Developer":["html","css","javascript","react","typescript","bootstrap","tailwind","git","figma"],
}
COMPANIES = ["TCS","Infosys","Accenture","Wipro","Capgemini","Cognizant","Deloitte","IBM","Microsoft","Amazon","Google"]

def pattern_for(skill):
    aliases = {"node.js":r"node\.?js","nodejs":r"node\.?js","c++":r"c\+\+","c#":r"c\#"}
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

def extract_text(filename, raw):
    low=filename.lower()
    if len(raw)>10*1024*1024:
        raise ValueError("File larger than 10 MB")
    if raw.startswith(b"%PDF") or low.endswith(".pdf"):
        import pdfplumber
        pages=[]
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages[:40]:
                pages.append(page.extract_text() or "")
        return "\n".join(pages)
    if low.endswith(".docx") or raw[:2]==b"PK":
        import docx
        d=docx.Document(io.BytesIO(raw))
        parts=[p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows: parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts)
    return raw.decode("utf-8", errors="ignore")

EMAIL_RE=re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE=re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}")
LINKEDIN_RE=re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%]+",re.I)
DEGREE_RE=re.compile(r"\b(b\.?\s?tech|m\.?\s?tech|bca|mca|bba|mba|bachelor|master|degree)\b",re.I)

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
    li=LINKEDIN_RE.search(text)
    skills=found_skills(text,"\n".join(sec["skills"]))
    education=sec["education"] or [x.strip() for x in text.splitlines() if DEGREE_RE.search(x)]
    exp=sec["experience"]
    projects=sec["projects"]
    allskills=list(dict.fromkeys(s for items in skills.values() for s in items))
    words=len(text.split())
    contact=(3 if get_name(text,email)!="Not found" else 0)+(3 if email!="Not found" else 0)+(2 if extract_phone(text)!="Not found" else 0)+(2 if li else 0)
    tech=sum(len(v) for k,v in skills.items() if k!="Soft Skills")
    skillscore=min(18,tech*1.5)+5
    breakdown={"Contact Info":(contact,10),"Skills":(round(min(skillscore,25),1),25),"Education":(min(10,4+len(education)*2) if education else 0,10),"Experience":(min(20,8+len(exp)*1.2) if exp else 0,20),"Projects":(min(15,len(projects)*5) if projects else 0,15),"Certifications":(0,5),"Formatting":(10,15)}
    score=round(sum(v for v,_ in breakdown.values()))
    roles=[]; have={x.lower() for x in allskills}
    for role, req in ROLE_SKILLS.items():
        matched=[s for s in req if pretty(s).lower() in have or s in have]
        roles.append({"Role":role,"Match %":round(100*len(matched)/len(req)),"Matched":matched,"Missing":[s for s in req if s not in matched],"Companies":COMPANIES[:7]})
    roles.sort(key=lambda x:x["Match %"],reverse=True)
    return {"text":text,"name":get_name(text,email),"email":email,"phone":extract_phone(text),"linkedin":li.group() if li else "","github":"","skills":skills,"all_skills":allskills,"education":education[:15],"experience":exp[:20],"projects":projects[:15],"certifications":[],"word_count":words,"score":score,"breakdown":breakdown,"tips":[],"jobs":roles}

def grade(score):
    if score>=80:return "Excellent"
    if score>=65:return "Good"
    if score>=45:return "Average"
    return "Needs Work"

def hero(title,sub):
    st.markdown(f'<div class="hero"><h1>{escape(title)}</h1><p>{escape(sub)}</p></div>', unsafe_allow_html=True)

def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state.update(logged_in=False,user_id=None,user_name="",user_email="")
    st.rerun()

css_code = "<style>.stApp{background:#0b1020;color:#e5e7eb}.block-container{max-width:1450px;padding-top:1.2rem}.hero{padding:28px 32px;border-radius:20px;background:linear-gradient(120deg,#4338ca,#7c3aed,#db2777);margin-bottom:18px}.hero h1,.hero p{color:white!important;margin:0}.hero p{margin-top:8px}div[data-testid='stMetric']{background:#111827;border:1px solid #2b3245;padding:14px;border-radius:14px}</style>"
st.markdown(css_code, unsafe_allow_html=True)

for k,v in {"logged_in":False,"user_id":None,"user_name":"","user_email":""}.items():
    st.session_state.setdefault(k,v)

def auth_screen():
    hero("Smart CV Analyzer Pro","Analyze your CV, discover job matches, and keep track of your progress.")
    _,mid,_=st.columns([1,1.5,1])
    with mid:
        login,signup,reset=st.tabs(["Login","Create account","Reset OTP"])
        with login:
            e=st.text_input("Email",key="login_email").strip().lower()
            p=st.text_input("Password",type="password",key="login_pass")
            if st.button("Login",type="primary",use_container_width=True):
                u=query("SELECT * FROM users WHERE email=?",(e,),one=True)
                if u and verify_password(p,u["password_hash"]):
                    st.session_state.update(logged_in=True,user_id=u["id"],user_name=u["name"],user_email=u["email"])
                    st.rerun()
                else: st.error("Email or password incorrect.")
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
                    st.success(f"OTP sent to {e2}")
                    st.info(f"Tera OTP hai: {otp}")
            otp_input = st.text_input("Enter OTP", key="signup_otp_input")
            if st.button("Verify & Create Account",type="primary",use_container_width=True):
                if otp_input and otp_input == st.session_state.get("signup_otp"):
                    n2,e2,p2 = st.session_state["signup_data"]
                    try:
                        query("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(n2.strip(),e2,password_hash(p2),datetime.now().strftime("%Y-%m-%d %H:%M:%S")),commit=True)
                        st.success("Account ban gaya! Login karo.")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("Email already registered")
                else:
                    st.error("Invalid OTP")
        with reset:
            st.info("OTP se reset hoga")
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
                    st.success(f"OTP sent to {er}")
                    st.info(f"Reset OTP: {otp}")
            otp_r = st.text_input("Enter OTP",key="reset_otp_input")
            np=st.text_input("New password",type="password",key="reset_pass_new")
            if st.button("Verify OTP & Reset",use_container_width=True):
                if otp_r and otp_r == st.session_state.get("reset_otp"):
                    if len(np) < 8:
                        st.error("8 char chahiye")
                    else:
                        query("UPDATE users SET password_hash=? WHERE email=?",(password_hash(np), st.session_state["reset_email"]),commit=True)
                        st.success("Password reset ho gaya!")
                else:
                    st.error("Invalid OTP")

if not st.session_state.logged_in:
    auth_screen()
    st.stop()

uid=st.session_state.user_id
with st.sidebar:
    st.markdown("## Smart CV Analyzer")
    st.success(f"Welcome, {st.session_state.user_name}")
    page=st.radio("Navigation",["Analyzer","History","Profile"]+(["Admin Panel"] if st.session_state.user_email.lower()==ADMIN_EMAIL else []),key="nav")
    st.divider()
    st.caption(f"Signed in as {st.session_state.user_email}")
    if st.button("Logout",use_container_width=True): logout()

if page.startswith("Analyzer"):
    hero("Smart CV Analyzer Pro","Upload CV to get ATS score")
    mode=st.radio("Input",["Upload file","Paste text"])
    if mode=="Upload file":
        uploaded=st.file_uploader("CV file",type=["pdf","docx","txt","jpg","jpeg","png","webp"])
        raw=uploaded.getvalue() if uploaded else None
        filename=uploaded.name if uploaded else "resume.txt"
    else:
        pasted=st.text_area("Paste CV text",height=280)
        raw=pasted.encode("utf-8") if pasted.strip() else None
        filename="Pasted_CV.txt"
    run=st.button("Analyze CV",type="primary",use_container_width=True,disabled=not raw)
    if run and raw:
        try:
            with st.spinner("Analyzing..."):
                text=extract_text(filename,raw)
                result=analyze_text(text)
                result["filename"]=filename
                payload=json.dumps(result,ensure_ascii=False)
                top=result["jobs"][0] if result["jobs"] else {"Role":"General"}
                query("INSERT INTO resume_history(user_id,file_name,category,ats_score,found_skills,missing_skills,extracted_text,analysis_date,full_json) VALUES(?,?,?,?,?,?,?,?,?)",(uid,filename,top["Role"],result["score"],json.dumps(result["all_skills"],ensure_ascii=False),json.dumps(top["Missing"],ensure_ascii=False),text,datetime.now().strftime("%Y-%m-%d %H:%M"),payload),commit=True)
                st.session_state["current_result"]=result
                st.success("Analysis complete")
        except Exception as e: st.error(f"Error: {e}")
    d=st.session_state.get("current_result")
    if d:
        st.divider()
        a,b,c=st.columns(3)
        a.metric("CV Score",f"{d['score']}/100",grade(d["score"]))
        b.metric("Skills",len(d["all_skills"]))
        c.metric("Words",d["word_count"])
        st.write("Skills: " + ", ".join(d["all_skills"]))

elif page.startswith("History"):
    hero("History","Your previous scans")
    rows=query("SELECT id,analysis_date,file_name,category,ats_score FROM resume_history WHERE user_id=? ORDER BY id DESC",(uid,))
    df=pd.DataFrame([dict(r) for r in rows])
    if df.empty: st.info("No scans yet")
    else: st.dataframe(df,use_container_width=True,hide_index=True)

elif page.startswith("Profile"):
    hero("My Profile","Manage account")
    u=query("SELECT * FROM users WHERE id=?",(uid,),one=True)
    st.write(f"Name: {u['name']}, Email: {u['email']}")

else:
    hero("Admin Panel","Admin overview")
    if st.session_state.user_email.lower()!=ADMIN_EMAIL:
        st.error("Access denied"); st.stop()
    users=query("SELECT id,name,email,created_at FROM users ORDER BY id DESC")
    udf=pd.DataFrame([dict(r) for r in users])
    st.dataframe(udf,use_container_width=True,hide_index=True)

st.markdown("---")
st.markdown("<p style='text-align:center;color:#9ca3af'>Built by Sufiyan</p>", unsafe_allow_html=True)