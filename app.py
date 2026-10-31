"""
CV Analyser — secure Streamlit resume analysis app
Run: python -m pip install -r requirements.txt
     streamlit run app.py

First launch: create an account from Sign Up, then log in.
OTP: local demo OTP is shown on screen by default. Configure SMTP/Twilio
environment variables for actual email/SMS delivery. Do not use demo OTP in production.
"""
import os, re, io, json, hmac, hashlib, secrets, sqlite3, smtplib, urllib.parse, urllib.request, base64
from datetime import datetime, timedelta
from email.message import EmailMessage
from xml.sax.saxutils import escape

import streamlit as st

st.set_page_config(page_title="CV Analyser", page_icon="📄", layout="wide")

DB_FILE = os.getenv("CV_DB_FILE", "cv_analyser.db")
PBKDF2_ITERS = 310_000
OTP_TTL_MIN = 5
MAX_OCR_PAGES = 10

INDUSTRIES = {
    "IT & Software": ["python","java","c++","javascript","html","css","react","node.js","django","flask","sql","mysql","mongodb","git","github","docker","aws","linux","rest api","api","excel","streamlit"],
    "Data & AI": ["python","sql","machine learning","pandas","numpy","scikit-learn","tensorflow","pytorch","statistics","power bi","tableau","excel","data analysis","data visualization","nlp"],
    "Finance & Accounting": ["accounting","bookkeeping","financial analysis","budgeting","forecasting","auditing","taxation","gst","tally","quickbooks","sap","excel","payroll"],
    "Marketing & Sales": ["seo","sem","content marketing","social media","google analytics","email marketing","copywriting","branding","google ads","crm","lead generation","salesforce"],
    "Human Resources": ["recruitment","talent acquisition","onboarding","employee relations","payroll","performance management","hris","interviewing"],
    "Design & Creative": ["figma","photoshop","illustrator","ui/ux","wireframing","prototyping","typography","graphic design","canva","user research","video editing"],
    "Engineering": ["autocad","solidworks","ansys","matlab","plc","scada","revit","circuit design","embedded systems","robotics","iot","quality control"],
}
SOFT = ["communication","leadership","teamwork","problem solving","time management","critical thinking","adaptability","creativity","collaboration","presentation"]

def connect():
    c = sqlite3.connect(DB_FILE, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          email TEXT UNIQUE, mobile TEXT UNIQUE, password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL, failed_attempts INTEGER DEFAULT 0,
          locked_until TEXT
        );
        CREATE TABLE IF NOT EXISTS otps(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          purpose TEXT NOT NULL, salt TEXT NOT NULL, code_hash TEXT NOT NULL,
          expires_at TEXT NOT NULL, attempts INTEGER DEFAULT 0,
          used INTEGER DEFAULT 0, created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS resume_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          file_name TEXT NOT NULL, score INTEGER NOT NULL, industry TEXT,
          job_match INTEGER, analysis_json TEXT NOT NULL, extracted_text TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_history_user ON resume_history(user_id);
        """)
init_db()

def now():
    return datetime.now()

def stamp(dt=None):
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")

def hash_password(pw):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, PBKDF2_ITERS)
    return f"{PBKDF2_ITERS}${salt.hex()}${digest.hex()}"

def verify_password(pw, stored):
    try:
        rounds, salt, digest = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(got, digest)
    except Exception:
        return False

def valid_password(p):
    return len(p) >= 8 and bool(re.search(r"[A-Za-z]", p)) and bool(re.search(r"\d", p))

def normalize_mobile(v):
    d = re.sub(r"\D", "", v or "")
    return d[-10:] if len(d) in (10, 11, 12, 13, 14, 15) else None

def identify(v):
    v = (v or "").strip()
    if "@" in v:
        return ("email", v.lower()) if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) else (None, None)
    m = normalize_mobile(v)
    return ("mobile", m) if m else (None, None)

def get_user(kind, value):
    if not kind: return None
    with connect() as c:
        return c.execute(f"SELECT * FROM users WHERE {kind}=?", (value,)).fetchone()

def cfg(k, default=""):
    return os.getenv(k, st.secrets.get(k, default) if hasattr(st, "secrets") else default)

def send_otp(user, code):
    message = f"Your CV Analyser verification code is {code}. It expires in {OTP_TTL_MIN} minutes. Do not share it."
    if user["email"] and cfg("SMTP_HOST") and cfg("SMTP_USER") and cfg("SMTP_PASSWORD"):
        msg = EmailMessage()
        msg["Subject"] = "CV Analyser OTP"
        msg["From"] = cfg("SMTP_FROM", cfg("SMTP_USER"))
        msg["To"] = user["email"]
        msg.set_content(message)
        port = int(cfg("SMTP_PORT", "587"))
        if port == 465:
            with smtplib.SMTP_SSL(cfg("SMTP_HOST"), port, timeout=15) as s:
                s.login(cfg("SMTP_USER"), cfg("SMTP_PASSWORD")); s.send_message(msg)
        else:
            with smtplib.SMTP(cfg("SMTP_HOST"), port, timeout=15) as s:
                s.starttls(); s.login(cfg("SMTP_USER"), cfg("SMTP_PASSWORD")); s.send_message(msg)
        return "email", None
    if user["mobile"] and cfg("TWILIO_SID") and cfg("TWILIO_TOKEN") and cfg("TWILIO_FROM"):
        sid, token = cfg("TWILIO_SID"), cfg("TWILIO_TOKEN")
        data = urllib.parse.urlencode({"To": cfg("DEFAULT_COUNTRY_CODE", "+91")+user["mobile"],
              "From": cfg("TWILIO_FROM"), "Body": message}).encode()
        req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data)
        req.add_header("Authorization", "Basic "+base64.b64encode(f"{sid}:{token}".encode()).decode())
        urllib.request.urlopen(req, timeout=15).read()
        return "sms", None
    if cfg("OTP_DEMO_MODE", "1").lower() not in ("1","true","yes"):
        raise RuntimeError("OTP delivery is not configured. Set SMTP or Twilio settings.")
    return "demo", code

def issue_otp(user, purpose):
    with connect() as c:
        recent = c.execute("SELECT created_at FROM otps WHERE user_id=? AND created_at>=? ORDER BY id DESC",
                           (user["id"], stamp(now()-timedelta(hours=1)))).fetchall()
        if len(recent) >= 5: raise ValueError("OTP limit reached. Try again after one hour.")
        if recent and (now()-datetime.strptime(recent[0]["created_at"], "%Y-%m-%d %H:%M:%S")).total_seconds() < 30:
            raise ValueError("Please wait 30 seconds before requesting another OTP.")
        c.execute("UPDATE otps SET used=1 WHERE user_id=? AND purpose=? AND used=0", (user["id"],purpose))
        code, salt = f"{secrets.randbelow(1000000):06d}", secrets.token_hex(16)
        digest = hashlib.sha256((salt+code).encode()).hexdigest()
        c.execute("INSERT INTO otps(user_id,purpose,salt,code_hash,expires_at,created_at) VALUES(?,?,?,?,?,?)",
                  (user["id"],purpose,salt,digest,stamp(now()+timedelta(minutes=OTP_TTL_MIN)),stamp()))
    mode, demo = send_otp(user, code)
    return mode, demo

def verify_otp(uid, purpose, code):
    with connect() as c:
        row = c.execute("SELECT * FROM otps WHERE user_id=? AND purpose=? AND used=0 ORDER BY id DESC LIMIT 1",
                        (uid,purpose)).fetchone()
        if not row: return False, "No active OTP. Request a new one."
        if row["expires_at"] < stamp(): 
            c.execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],)); return False, "OTP expired."
        if row["attempts"] >= 5:
            c.execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],)); return False, "Too many attempts. Request a new OTP."
        good = hmac.compare_digest(hashlib.sha256((row["salt"]+(code or "").strip()).encode()).hexdigest(), row["code_hash"])
        if good: c.execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],)); return True, ""
        c.execute("UPDATE otps SET attempts=attempts+1 WHERE id=?", (row["id"],))
        return False, f"Incorrect OTP. {4-row['attempts']} attempts left."

def extract_file(upload):
    name, data = upload.name, upload.getvalue()
    lower = name.lower()
    if data.startswith(b"%PDF"):
        import pdfplumber
        texts=[]
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages):
                txt = page.extract_text() or ""
                if len(txt.strip()) < 25 and i < MAX_OCR_PAGES:
                    try:
                        txt = ocr_image(page.to_image(resolution=200).original)
                    except Exception:
                        pass
                texts.append(txt)
        return "\n".join(texts), name
    if lower.endswith(".docx"):
        from docx import Document
        doc=Document(io.BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs] + [" | ".join(x.text for x in r.cells) for t in doc.tables for r in t.rows]), name
    if lower.endswith((".png",".jpg",".jpeg",".webp")):
        from PIL import Image
        return ocr_image(Image.open(io.BytesIO(data))), name
    if lower.endswith(".txt"):
        return data.decode("utf-8", errors="ignore"), name
    raise ValueError("Unsupported file. Upload PDF, DOCX, TXT, JPG, PNG or WEBP.")

def ocr_image(img):
    import pytesseract
    from PIL import ImageOps
    img = ImageOps.autocontrast(img.convert("L"))
    if max(img.size) < 1800:
        scale=1800/max(img.size); img=img.resize((int(img.width*scale),int(img.height*scale)))
    return pytesseract.image_to_string(img, config="--psm 3")

def detect_skills(text):
    low=text.lower()
    found=[]
    for skills in INDUSTRIES.values():
        for s in skills:
            if re.search(r"(?<![\w+#])"+re.escape(s)+r"(?![\w+#])", low) and s not in found:
                found.append(s)
    return found

def analyse(text, filename, jd=""):
    lines=[x.strip(" •\\t-") for x in text.splitlines() if x.strip()]
    email=re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",text)
    phone=re.search(r"(?:\+?\d[\d\s().-]{8,}\d)",text)
    name="Not found"
    for line in lines[:12]:
        if "@" not in line and not re.search(r"\d",line) and 2 <= len(line.split()) <= 4 and len(line)<45:
            name=line; break
    skills=detect_skills(text)
    soft=[s for s in SOFT if re.search(r"\b"+re.escape(s)+r"\b",text,re.I)]
    industry=max(INDUSTRIES, key=lambda k: sum(s in skills for s in INDUSTRIES[k])) if skills else "General"
    sections={}
    aliases={"Education":["education","qualification"],"Experience":["experience","employment","internship"],"Projects":["projects","project"],"Certifications":["certification","certificate","courses"]}
    current=""
    for line in lines:
        key=line.lower().strip(": ")
        match=next((k for k,vals in aliases.items() if key in vals),None)
        if match: current=match; sections.setdefault(current,[]); continue
        if current: sections.setdefault(current,[]).append(line)
    edu=sections.get("Education",[])[:12]
    exp=sections.get("Experience",[])[:15]
    projects=sections.get("Projects",[])[:10]
    certs=sections.get("Certifications",[])[:10]
    words=len(text.split())
    score=min(100, (10 if name!="Not found" else 0)+(8 if email else 0)+(5 if phone else 0)+min(25,len(skills)*2)+
              min(10,len(edu)*3)+min(15,len(exp)*3)+min(12,len(projects)*4)+min(5,len(certs)*2)+
              (10 if 180<=words<=1000 else 4))
    jdskills=[s for s in detect_skills(jd)] if jd.strip() else []
    matched=[s for s in jdskills if s in skills]
    match=round(100*len(matched)/len(jdskills)) if jdskills else 0
    tips=[]
    if name=="Not found" or not email or not phone: tips.append("Add clear contact details at the top of your CV.")
    if len(skills)<8: tips.append("Add relevant technical and soft skills with honest proficiency levels.")
    if not edu: tips.append("Add an Education section with course, institute and graduation year.")
    if not exp: tips.append("Add internships, volunteering, freelance or practical experience if applicable.")
    if len(projects)<2: tips.append("Add 2–3 projects with tools used and measurable outcomes.")
    if not certs: tips.append("Include relevant certifications or completed courses.")
    roles=[]
    for ind, ss in INDUSTRIES.items():
        if not ss: continue
        hit=[s for s in ss if s in skills]
        if hit: roles.append({"role":ind+" Professional","match":round(100*len(hit)/min(10,len(ss))),"matched":hit,"missing":[s for s in ss[:10] if s not in skills]})
    roles.sort(key=lambda x:x["match"],reverse=True)
    return {"file_name":filename,"created":stamp(),"contact":{"name":name,"email":email.group(0) if email else "Not found","phone":phone.group(0).strip() if phone else "Not found"},
            "skills":skills,"soft_skills":soft,"industry":industry,"education":edu,"experience":exp,"projects":projects,"certifications":certs,
            "score":score,"job_match":match,"jd_skills":jdskills,"jd_matched":matched,"roles":roles[:6],"tips":tips,"words":words}

def make_pdf(a):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    b=io.BytesIO(); styles=getSampleStyleSheet(); story=[]
    story += [Paragraph("CV Analyser — Resume Report",styles["Title"]),Spacer(1,10)]
    story += [Paragraph(f"<b>File:</b> {escape(a['file_name'])} &nbsp; <b>Date:</b> {a['created']}",styles["BodyText"]),Spacer(1,8)]
    story += [Paragraph(f"<b>CV Score:</b> {a['score']}/100 &nbsp; <b>Industry:</b> {escape(a['industry'])} &nbsp; <b>Job match:</b> {a['job_match']}%",styles["Heading2"])]
    for heading, vals in [("Contact",list(a["contact"].items())),("Skills",[("Detected",", ".join(a["skills"]) or "None"),("Soft skills",", ".join(a["soft_skills"]) or "None")]),("Education",[(str(i+1),v) for i,v in enumerate(a["education"])]),("Experience",[(str(i+1),v) for i,v in enumerate(a["experience"])]),("Projects",[(str(i+1),v) for i,v in enumerate(a["projects"])]),("Certifications",[(str(i+1),v) for i,v in enumerate(a["certifications"])]),("Suggestions",[(str(i+1),v) for i,v in enumerate(a["tips"])])]:
        story.append(Paragraph(heading,styles["Heading2"]))
        rows=[[Paragraph(escape(str(k)),styles["BodyText"]),Paragraph(escape(str(v)),styles["BodyText"])] for k,v in vals] or [["—","Not found"]]
        t=Table(rows,colWidths=[4*cm,13*cm]); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(0,-1),colors.whitesmoke)])); story.append(t)
    SimpleDocTemplate(b,pagesize=A4).build(story)
    return b.getvalue()

def save_result(uid,a,text):
    with connect() as c:
        c.execute("INSERT INTO resume_history(user_id,file_name,score,industry,job_match,analysis_json,extracted_text,created_at) VALUES(?,?,?,?,?,?,?,?)",
                  (uid,a["file_name"],a["score"],a["industry"],a["job_match"],json.dumps(a),text,stamp()))

def style():
    st.markdown("""<style>
    .stApp{background:#f5f7fb;color:#182033}
    [data-testid="stSidebar"]{background:#fff}
    .hero{padding:24px;border-radius:18px;background:linear-gradient(120deg,#4f46e5,#0ea5a4);color:white;margin-bottom:18px}
    .hero h1,.hero p{color:white!important}
    div[data-testid="stMetric"]{background:white;padding:14px;border:1px solid #e5e7eb;border-radius:14px}
    </style>""",unsafe_allow_html=True)
style()

for k,v in {"logged_in":False,"uid":None,"user_name":"","auth":None,"result":None}.items():
    st.session_state.setdefault(k,v)

def login_ui():
    st.markdown('<div class="hero"><h1>📄 CV Analyser</h1><p>Secure resume analysis · Skills · Job matching · PDF reports</p></div>',unsafe_allow_html=True)
    tabs=st.tabs(["🔐 Login","📝 Sign Up","🔑 Forgot Password"])
    with tabs[0]:
        with st.form("login"):
            ident=st.text_input("Email or mobile")
            pw=st.text_input("Password",type="password")
            go=st.form_submit_button("Continue")
        if go:
            kind,val=identify(ident); u=get_user(kind,val)
            if not u: st.error("Invalid credentials.")
            elif u["locked_until"] and u["locked_until"]>stamp(): st.error("Account temporarily locked. Try later.")
            elif not verify_password(pw,u["password_hash"]):
                with connect() as c:
                    fails=u["failed_attempts"]+1
                    c.execute("UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                              (0 if fails>=5 else fails,stamp(now()+timedelta(minutes=10)) if fails>=5 else None,u["id"]))
                st.error("Invalid credentials.")
            else:
                try:
                    mode,demo=issue_otp(u,"login")
                    st.session_state.auth={"uid":u["id"],"purpose":"login","mode":mode,"demo":demo}
                    st.rerun()
                except Exception as e: st.error(str(e))
    with tabs[1]:
        with st.form("signup"):
            name=st.text_input("Full name")
            email=st.text_input("Email (optional if mobile supplied)")
            mobile=st.text_input("Mobile (optional if email supplied)")
            p1=st.text_input("Password (8+ characters, letters and numbers)",type="password")
            p2=st.text_input("Confirm password",type="password")
            go=st.form_submit_button("Create account")
        if go:
            em=email.strip().lower() or None; mob=normalize_mobile(mobile) if mobile.strip() else None
            if not name.strip(): st.error("Enter your name.")
            elif not em and not mob: st.error("Enter email or mobile.")
            elif em and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",em): st.error("Invalid email.")
            elif mobile.strip() and not mob: st.error("Invalid mobile number.")
            elif not valid_password(p1): st.error("Password must be 8+ characters with letters and numbers.")
            elif p1!=p2: st.error("Passwords do not match.")
            else:
                try:
                    with connect() as c: c.execute("INSERT INTO users(name,email,mobile,password_hash,created_at) VALUES(?,?,?,?,?)",(name.strip(),em,mob,hash_password(p1),stamp()))
                    st.success("Account created. Open Login and sign in.")
                except sqlite3.IntegrityError: st.error("Email or mobile already registered.")
    with tabs[2]:
        with st.form("forgot"):
            ident=st.text_input("Registered email or mobile")
            go=st.form_submit_button("Send reset OTP")
        if go:
            kind,val=identify(ident); u=get_user(kind,val)
            if not u: st.error("Account not found.")
            else:
                try:
                    mode,demo=issue_otp(u,"reset")
                    st.session_state.auth={"uid":u["id"],"purpose":"reset","mode":mode,"demo":demo}
                    st.rerun()
                except Exception as e: st.error(str(e))

def otp_ui():
    a=st.session_state.auth
    st.subheader("🔐 OTP Verification")
    if a["mode"]=="demo": st.warning(f"Development OTP: **{a['demo']}**")
    else: st.info("OTP sent to your registered contact.")
    with st.form("otp_verify"):
        code=st.text_input("6-digit OTP",max_chars=6)
        go=st.form_submit_button("Verify OTP")
    if go:
        ok,msg=verify_otp(a["uid"],a["purpose"],code)
        if not ok: st.error(msg)
        elif a["purpose"]=="login":
            with connect() as c:
                u=c.execute("SELECT * FROM users WHERE id=?",(a["uid"],)).fetchone()
                c.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE id=?",(a["uid"],))
            st.session_state.update(logged_in=True,uid=u["id"],user_name=u["name"],auth=None)
            st.rerun()
        else:
            st.session_state.auth={"uid":a["uid"],"purpose":"new_password"}
            st.rerun()
    if st.button("Back"): st.session_state.auth=None; st.rerun()

def reset_password_ui():
    with st.form("new_pw"):
        p1=st.text_input("New password",type="password")
        p2=st.text_input("Confirm password",type="password")
        go=st.form_submit_button("Update password")
    if go:
        if not valid_password(p1): st.error("Use 8+ characters with letters and numbers.")
        elif p1!=p2: st.error("Passwords do not match.")
        else:
            with connect() as c: c.execute("UPDATE users SET password_hash=?,failed_attempts=0,locked_until=NULL WHERE id=?",(hash_password(p1),st.session_state.auth["uid"]))
            st.session_state.auth=None; st.success("Password updated. Log in now.")

def dashboard(a):
    c1,c2,c3,c4=st.columns(4)
    c1.metric("CV Score",f"{a['score']}/100"); c2.metric("Job Match",f"{a['job_match']}%")
    c3.metric("Skills Found",len(a["skills"])); c4.metric("Word Count",a["words"])
    st.progress(a["score"]/100)
    st.subheader("Candidate")
    st.write(a["contact"])
    st.subheader("Detected Skills")
    st.write(", ".join(a["skills"]) or "No known skills detected.")
    st.subheader("Education / Experience / Projects")
    for key in ("education","experience","projects","certifications"):
        with st.expander(key.title()):
            st.write(a[key] or "Not found")
    st.subheader("Role / Industry Suggestions")
    for r in a["roles"]:
        with st.expander(f"{r['role']} — {r['match']}%"):
            st.write("Matched:",", ".join(r["matched"]))
            st.write("Skills to learn:",", ".join(r["missing"]))
    if a["jd_skills"]:
        st.subheader("Job Description Match")
        st.write(f"{a['job_match']}%")
        st.write("Matched:",", ".join(a["jd_matched"]))
        st.write("Missing:",", ".join([s for s in a["jd_skills"] if s not in a["jd_matched"]]))
    st.subheader("Improvement Suggestions")
    for tip in a["tips"]: st.write("•",tip)
    try:
        pdf=make_pdf(a)
        st.download_button("⬇️ Download PDF Report",pdf,file_name="CV_Analyser_Report.pdf",mime="application/pdf")
    except Exception as e: st.warning(f"PDF report unavailable: {e}")
    st.download_button("⬇️ Download TXT Report",json.dumps(a,indent=2),file_name="CV_Analyser_Report.txt")

def app_ui():
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.user_name}")
        page=st.radio("Navigation",["Analyze Resume","Dashboard","History","Profile"])
        if st.button("Logout"):
            st.session_state.update(logged_in=False,uid=None,user_name="",result=None)
            st.rerun()
    if page=="Analyze Resume":
        st.title("🔍 Analyze Resume")
        method=st.radio("Input type",["Upload File","Paste Text"],horizontal=True)
        uploaded=None; pasted=""
        if method=="Upload File":
            uploaded=st.file_uploader("Choose resume",type=["pdf","docx","txt","jpg","jpeg","png","webp"])
        else: pasted=st.text_area("Paste resume text",height=240)
        jd=st.text_area("Job description (optional)",height=120)
        if st.button("Analyze Resume",type="primary"):
            try:
                if method=="Upload File":
                    if not uploaded: st.error("Upload a file first."); st.stop()
                    with st.spinner("Extracting text. OCR may take a moment..."): text,filename=extract_file(uploaded)
                else: text,filename=pasted,"Pasted_Resume.txt"
                if len(text.strip())<30: st.error("Not enough readable text. Try a clearer scan or paste text.")
                else:
                    with st.spinner("Analysing resume..."):
                        a=analyse(text,filename,jd); save_result(st.session_state.uid,a,text)
                        st.session_state.result={"analysis":a,"text":text}
            except Exception as e: st.error(f"Could not analyse file: {e}")
        if st.session_state.result:
            a=st.session_state.result["analysis"]; dashboard(a)
            with st.expander("View extracted text"): st.text(st.session_state.result["text"][:12000])
    elif page=="Dashboard":
        st.title("📊 Dashboard")
        with connect() as c: rows=c.execute("SELECT score,job_match,created_at FROM resume_history WHERE user_id=? ORDER BY id",(st.session_state.uid,)).fetchall()
        if rows:
            st.metric("Total analyses",len(rows)); st.metric("Average CV score",round(sum(x["score"] for x in rows)/len(rows)))
            st.metric("Best score",max(x["score"] for x in rows))
            st.line_chart({"CV Score":[x["score"] for x in rows]})
        else: st.info("No analyses yet. Start from Analyze Resume.")
    elif page=="History":
        st.title("📚 Resume History")
        with connect() as c: rows=c.execute("SELECT * FROM resume_history WHERE user_id=? ORDER BY id DESC",(st.session_state.uid,)).fetchall()
        if not rows: st.info("No saved resume history.")
        for row in rows:
            with st.expander(f"{row['file_name']} · Score {row['score']}/100 · {row['created_at']}"):
                a=json.loads(row["analysis_json"]); dashboard(a)
                with st.expander("Extracted text"): st.text(row["extracted_text"][:10000])
                if st.button("Delete this record",key=f"del_{row['id']}"):
                    with connect() as c: c.execute("DELETE FROM resume_history WHERE id=? AND user_id=?",(row["id"],st.session_state.uid))
                    st.rerun()
        if rows and st.button("Clear all history"):
            with connect() as c: c.execute("DELETE FROM resume_history WHERE user_id=?",(st.session_state.uid,))
            st.rerun()
    else:
        st.title("👤 Profile")
        with connect() as c: u=c.execute("SELECT * FROM users WHERE id=?",(st.session_state.uid,)).fetchone()
        st.write({"Name":u["name"],"Email":u["email"] or "—","Mobile":u["mobile"] or "—","Member since":u["created_at"]})
        with st.form("change_pw"):
            old=st.text_input("Current password",type="password")
            new=st.text_input("New password",type="password")
            confirm=st.text_input("Confirm new password",type="password")
            go=st.form_submit_button("Change password")
        if go:
            if not verify_password(old,u["password_hash"]): st.error("Current password incorrect.")
            elif not valid_password(new): st.error("New password must be 8+ characters with letters and numbers.")
            elif new!=confirm: st.error("Passwords do not match.")
            else:
                with connect() as c: c.execute("UPDATE users SET password_hash=? WHERE id=?",(hash_password(new),u["id"]))
                st.success("Password changed.")

st.markdown('<div class="hero"><h1>📄 CV Analyser</h1><p>Resume scoring · OCR · Skills analysis · Job matching · PDF reports</p></div>',unsafe_allow_html=True)
if st.session_state.auth:
    if st.session_state.auth["purpose"]=="new_password": reset_password_ui()
    else: otp_ui()
elif not st.session_state.logged_in:
    login_ui()
else:
    app_ui()
