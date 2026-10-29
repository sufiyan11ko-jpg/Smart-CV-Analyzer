"""
Smart CV Analyzer Pro - FINAL PERFECT VERSION
No Tesseract, Light Theme, Mobile Friendly, Login + History + Save
requirements.txt: streamlit, PyPDF2, python-docx, pandas
"""
import hashlib, io, json, re, sqlite3
from datetime import datetime
from xml.sax.saxutils import escape
import streamlit as st

st.set_page_config(page_title="Smart CV Analyzer Pro", page_icon="📄", layout="centered", initial_sidebar_state="collapsed")

# --- FIX FOR UPLOAD CRASH ---
def make_card(key_name):
    try:
        return st.container(key=key_name)
    except TypeError:
        return st.container(border=True)

# --- ALL LOGIC ---
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
    if low in LABEL_OVERRIDES: return LABEL_OVERRIDES[low]
    return skill.upper() if len(skill) <= 3 else skill.title()
SECTION_ALIASES = {
    "education": ["education","academic qualification","academics","qualifications"],
    "experience": ["experience","work experience","professional experience","employment history","internship","internships"],
    "projects": ["projects","academic projects","personal projects","key projects"],
    "skills": ["skills","technical skills","key skills","core competencies"],
    "certifications": ["certifications","certificates","courses"],
    "other": ["summary","objective","profile","achievements","awards"],
}
JOB_ROLES = {
    "Data Scientist": {"skills": ["python","machine learning","pandas","numpy","scikit-learn","sql","statistics","deep learning","data visualization"], "companies": ["Google","Amazon","Microsoft","Fractal Analytics","Mu Sigma","Tiger Analytics"]},
    "Data Analyst": {"skills": ["sql","excel","power bi","tableau","python","pandas","data analysis","data visualization"], "companies": ["Deloitte","EY","KPMG","Genpact","WNS","Swiggy"]},
    "AI / ML Engineer": {"skills": ["python","tensorflow","pytorch","deep learning","nlp","computer vision","machine learning","docker","llm"], "companies": ["NVIDIA","OpenAI","Samsung R&D","Qualcomm"]},
    "Python / Backend Developer": {"skills": ["python","django","flask","fastapi","sql","postgresql","rest api","git","docker"], "companies": ["Infosys","Zoho","Freshworks","Razorpay"]},
    "Frontend Developer": {"skills": ["html","css","javascript","react","typescript","bootstrap","tailwind","git","figma"], "companies": ["Flipkart","Myntra","Cred","Meesho"]},
    "Full Stack Developer": {"skills": ["html","css","javascript","react","node.js","mongodb","express","sql","git","rest api"], "companies": ["TCS","Infosys","Accenture","Cognizant"]},
    "Java Developer": {"skills": ["java","spring boot","mysql","sql","rest api","oop","git","junit"], "companies": ["TCS","Infosys","Wipro","IBM","Oracle"]},
    "DevOps / Cloud Engineer": {"skills": ["aws","azure","docker","kubernetes","linux","jenkins","ci/cd","terraform","git","bash"], "companies": ["Amazon AWS","Microsoft Azure","Red Hat"]},
    "Android / Mobile Developer": {"skills": ["android","kotlin","java","flutter","dart","firebase","react native"], "companies": ["Google","Samsung","PhonePe","Dream11"]},
    "Software Tester / QA": {"skills": ["selenium","junit","jira","sql","java","python","git"], "companies": ["Capgemini","Cognizant","Infosys"]},
}
PROJECT_IDEAS = {
    "Data & AI": ["Resume–Job Description Matcher using NLP","Customer Churn Prediction Dashboard","Sentiment Analysis using Transformers"],
    "Web": ["Full-Stack Job Portal","Real-time Chat App","E-commerce Platform with Payment Gateway"],
    "Programming": ["Smart Library Management System","Algorithm Visualizer","Code Plagiarism Detector"],
    "Database": ["Hospital Management System","Inventory Management with Analytics"],
    "Cloud & DevOps": ["CI/CD Pipeline for Dockerized App on AWS","Kubernetes Auto-scaling Demo"],
    "Mobile & Other": ["Flutter Expense Tracker","IoT Smart Home Monitoring","Face-recognition Attendance App"],
}
GENERIC_IDEAS = ["Portfolio Website with Blog","AI Chatbot for FAQs using RAG","Weather and Air-Quality Dashboard"]
ATS_ACTION_VERBS = ["developed","designed","built","created","implemented","improved","optimized","automated","led","managed","analyzed","deployed","tested"]
METRIC_RE = re.compile(r"\d+\s?%|\d+\+|\$\s?\d+|₹\s?\d+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.I)
DEGREE_RE = re.compile(r"\b(b\.?\s?tech|m\.?\s?tech|bca|mca|bba|mba|b\.?\s?sc|m\.?\s?sc|bachelor|master)\b", re.I)

def extract_email(t): m=EMAIL_RE.search(t); return m.group(0) if m else "Not found"
def extract_phone(t):
    for m in PHONE_RE.finditer(t):
        d=re.sub(r"\D","",m.group(0))
        if 10<=len(d)<=13 and not re.fullmatch(r"(19|20)\d{2}(19|20)\d{2}",d): return m.group(0).strip()
    return "Not found"
def extract_name(text,email):
    skip=("resume","curriculum","vitae","cv","profile","objective","summary","contact","address","email","phone","mobile","github","linkedin")
    for line in [l.strip() for l in text.splitlines() if l.strip()][:15]:
        if "@" in line or any(w in line.lower() for w in skip) or re.search(r"\d", line): continue
        words=re.sub(r"[^A-Za-z .'-]"," ",line).split()
        if 2<=len(words)<=4 and all(w[0].isalpha() for w in words): return " ".join(words)
    if email!="Not found": return re.sub(r"[\d._-]+"," ",email.split("@")[0]).title().strip()
    return "Not found"
def split_sections(text):
    lookup={a:k for k,al in SECTION_ALIASES.items() for a in al}
    sections={k:[] for k in SECTION_ALIASES}; cur=None
    for raw in text.splitlines():
        line=raw.strip()
        if not line: continue
        key=re.sub(r"[^a-z &]","",line.lower()).strip()
        if len(line)<45 and key in lookup: cur=lookup[key]; continue
        if cur: sections[cur].append(line)
    return sections
def find_pattern(text,pattern): return re.search(r"(?<![A-Za-z0-9+#.])"+re.escape(pattern)+r"(?![A-Za-z0-9+#])",text or "",re.I)
def extract_skills(text,skills_section):
    found={}
    for cat,skills in SKILLS_DB.items():
        for s in skills:
            hay=skills_section if s in AMBIGUOUS else text
            if hay and find_pattern(hay,s):
                lab=pretty(s); found.setdefault(cat,[]); 
                if lab not in found[cat]: found[cat].append(lab)
    return found
def extract_education(text,lines): lines=lines[:] if lines else [l.strip() for l in text.splitlines() if DEGREE_RE.search(l)]; return [l for l in lines if len(l)>3][:12]
def extract_experience(lines): return [l for l in lines if len(l)>3][:15]
def extract_projects(lines):
    out=[]
    for line in lines:
        c=line.strip()
        if len(c)<4: continue
        is_title=not c.startswith(("•","-","*","●","▪")) and len(c.split())<=14
        if is_title or not out: out.append(c.lstrip("•-*●▪ ").strip())
    return out[:10]
def extract_certifications(text,lines):
    lines=lines[:] if lines else []
    if not lines:
        for l in text.splitlines():
            if re.search(r"\b(certified|certification|certificate|course)\b",l,re.I): lines.append(l.strip())
    return [l.strip("•-*●▪ ") for l in lines if len(l.strip())>4][:12]
def extract_links(text): li,gh=LINKEDIN_RE.search(text),GITHUB_RE.search(text); return (li.group(0) if li else None, gh.group(0) if gh else None)
def estimate_experience_years(text,exp_lines):
    years=[float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",text,re.I)]; best=max(years) if years and max(years)<40 else 0.0; return round(best,1)
def calculate_score(d):
    bd={}; c=(3 if d["name"]!="Not found" else 0)+(3 if d["email"]!="Not found" else 0)+(2 if d["phone"]!="Not found" else 0)+(2 if d["linkedin"] or d["github"] else 0); bd["Contact Info"]=(c,10)
    tech=sum(len(i) for k,i in d["skills"].items() if k!="Soft Skills"); cats=len([k for k,i in d["skills"].items() if i and k!="Soft Skills"]); ss=min(18,tech*1.5)+min(5,cats*1.25)+(2 if d["skills"].get("Soft Skills") else 0); bd["Skills"]=(round(min(ss,25),1),25)
    bd["Education"]=(min(10,4+len(d["education"])*2) if d["education"] else 0,10); es=min(20,8+len(d["experience"])*1.2+d["experience_years"]*2) if d["experience"] else 0; bd["Experience"]=(round(es,1),20)
    bd["Projects"]=(min(15,len(d["projects"])*5) if d["projects"] else 0,15); bd["Certifications"]=(round(min(5,len(d["certifications"])*1.5),1) if d["certifications"] else 0,5)
    words=len(d["text"].split()); fmt=10 if 250<=words<=900 else 6 if (150<=words<250 or 900<words<=1300) else 3; metrics=METRIC_RE.search(d["text"]); fmt=min(15,fmt+(2 if metrics else 0)); av=sum(1 for v in ATS_ACTION_VERBS if find_pattern(d["text"],v)); fmt=min(15,fmt+(3 if av>=3 else 1 if av else 0)); bd["Formatting & Impact"]=(fmt,15)
    total=max(0,min(100,round(sum(v for v,_ in bd.values())))); return total,bd,[]
def grade(score):
    if score>=80: return "Excellent 🌟","#16a34a"
    if score>=65: return "Good 👍","#2563eb"
    if score>=45: return "Average ⚠️","#d97706"
    return "Needs Work ❌","#dc2626"
def match_jobs(all_skills):
    have={s.lower() for s in all_skills}; rows=[]
    for role,info in JOB_ROLES.items():
        req=info["skills"]; matched=[s for s in req if s in have]; rows.append({"Role":role,"Match %":round(100*len(matched)/len(req)),"Matched":matched,"Missing":[s for s in req if s not in matched],"Companies":info["companies"]})
    return sorted(rows,key=lambda r:r["Match %"],reverse=True)
def match_job_description(cv,jd):
    def extract_jd_skills(jd):
        found=[]
        for cat,skills in SKILLS_DB.items():
            if cat=="Soft Skills": continue
            for s in skills:
                if s in AMBIGUOUS: continue
                if find_pattern(jd,s):
                    c="node.js" if s=="nodejs" else s
                    if c not in found: found.append(c)
        return found
    jd_skills=extract_jd_skills(jd)
    if not jd_skills: return {"jd_skills":[],"matched":[],"missing":[],"match_percent":0,"priority":[]}
    def in_cv(s):
        if s=="node.js": return bool(find_pattern(cv,"node.js") or find_pattern(cv,"nodejs"))
        return bool(find_pattern(cv,s))
    matched=[s for s in jd_skills if in_cv(s)]; missing=[s for s in jd_skills if s not in matched]; pr=sorted(missing,key=lambda s:(0 if s in ("python","sql","machine learning","javascript","aws") else 1,s))
    return {"jd_skills":jd_skills,"matched":matched,"missing":missing,"match_percent":round(100*len(matched)/len(jd_skills)),"priority":pr}
def suggest_projects(skills_by_cat):
    ideas,seen=[],set()
    for cat,_ in sorted(skills_by_cat.items(),key=lambda i:len(i[1]),reverse=True):
        for idea in PROJECT_IDEAS.get(cat,[]):
            if idea not in seen: ideas.append((cat,idea)); seen.add(idea)
    for idea in GENERIC_IDEAS: ideas.append(("General",idea))
    return ideas[:12]

# --- NO TESSERACT - ONLY PDF/DOCX/TXT ---
def parse_pdf(data:bytes)->str:
    from PyPDF2 import PdfReader; reader=PdfReader(io.BytesIO(data)); return "\n".join((p.extract_text() or "") for p in reader.pages)
def parse_docx(data:bytes)->str:
    import docx; document=docx.Document(io.BytesIO(data)); parts=[p.text for p in document.paragraphs]; return "\n".join(parts)
def read_file(name:str,data:bytes)->str:
    lower=name.lower()
    if lower.endswith(".pdf"): return parse_pdf(data)
    if lower.endswith(".docx"): return parse_docx(data)
    if lower.endswith(".txt"): return data.decode("utf-8",errors="ignore")
    raise ValueError("Only PDF, DOCX, TXT supported")

def analyze(text,jd):
    low=text.lower(); words=len(text.split()); SPEC_SKILLS=["python","java","c++","javascript","react","node.js","sql","mysql","machine learning","deep learning","data analysis","excel","power bi","communication","leadership","teamwork","aws","docker","git","html","css","tensorflow","pytorch","nlp","pandas","numpy","streamlit","flask","django"]
    def find_skills(t):
        f=[]; 
        for s in SPEC_SKILLS:
            if re.search(r"(?<![a-z0-9+#.])"+re.escape(s)+r"(?![a-z0-9+#])",t.lower()): f.append(s)
        return f
    skills=find_skills(text); EDU_WORDS=["education","bachelor","master","b.tech","degree","university"]; EXP_WORDS=["experience","internship","employment"]; ACTION_VERBS=["developed","designed","built","created","implemented","improved","optimized","automated","led","managed","analyzed","deployed"]
    checks={"Email address":extract_email(text)!="Not found","Phone number":extract_phone(text)!="Not found","Skills keywords":len(skills)>0,"Education section":any(w in low for w in EDU_WORDS),"Experience section":any(w in low for w in EXP_WORDS),"Length (300+ words)":words>300,"Action verbs":any(re.search(r"\b"+v+r"\b",low) for v in ACTION_VERBS)}; ats=max(35,min(95,sum(checks.values())*14))
    try:
        sec=split_sections(text); email,phone=extract_email(text),extract_phone(text); li,gh=extract_links(text); exp=extract_experience(sec["experience"])
        data={"text":text,"name":extract_name(text,email),"email":email,"phone":phone,"linkedin":li,"github":gh,"skills":extract_skills(text,"\n".join(sec["skills"])),"education":extract_education(text,sec["education"]),"experience":exp,"experience_years":estimate_experience_years(text,exp),"projects":extract_projects(sec["projects"]),"certifications":extract_certifications(text,sec["certifications"])}
        all_skills=[]; 
        for items in data["skills"].values():
            for s in items:
                if s not in all_skills: all_skills.append(s)
        data["all_skills"]=all_skills; total,breakdown,tips=calculate_score(data)
        adv={"data":data,"total":total,"breakdown":breakdown,"tips":tips,"jobs":match_jobs(all_skills),"ideas":suggest_projects(data["skills"]),"jd":match_job_description(text,jd) if jd.strip() else None}
    except Exception: adv=None
    result={"checks":checks,"ats":ats,"skills":skills,"words":words,"match":None,"missing":[],"adv":adv}
    if jd.strip():
        STOPWORDS=set("the and for are with you your this that from have will job role work team candidate years year plus must should".split()); 
        def keywords(t): return {w for w in re.findall(r"[a-z0-9+#]{3,}",t.lower()) if w not in STOPWORDS and not w.isdigit()}
        job_words,cv_words=keywords(jd),keywords(text)
        if job_words: common=job_words & cv_words; result["match"]=int(min(92,len(common)/len(job_words)*100*2)); result["missing"]=sorted(job_words-cv_words)[:15]
    return result
def report_text(res:dict)->str:
    lines=["SMART CV ANALYZER PRO - REPORT","="*30,f"ATS Score: {res['ats']}%",f"Word Count: {res['words']}","Skills Detected: "+(", ".join(res["skills"]) or "None"),"","ATS Checklist:"]; lines+=[f"  [{'OK' if ok else 'X'}] {name}" for name,ok in res["checks"].items()]
    if res["match"] is not None: lines+=["",f"Job Match: {res['match']}%","Missing keywords: "+(", ".join(res["missing"]) or "None")]
    adv=res.get("adv")
    if adv: d=adv["data"]; lines+=["",f"Detailed CV Score: {adv['total']}/100",f"Name: {d['name']}",f"Email: {d['email']}",f"Phone: {d['phone']}","", "Best matching roles:"]; lines+=[f"  - {j['Role']} ({j['Match %']}%)" for j in adv["jobs"][:5]]
    return "\n".join(lines)
TIPS={"Email address":"Add a professional email address","Phone number":"Add phone number","Skills keywords":"Add Skills section","Education section":"Add Education","Experience section":"Add experience","Length (300+ words)":"Expand to 300+ words","Action verbs":"Use action verbs like built, developed"}

# --- LIGHT THEME FORCE ---
st.markdown("""<style>
:root { color-scheme: light only; }
[data-testid="stSidebar"]{display:none} #MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;height:0}
.stApp{background:#f8f9fb} .block-container{padding-top:0.8rem;max-width:780px}
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4{color:#1f2937}
.hero{background:linear-gradient(135deg,#6e56ff,#ff5a8a);border-radius:16px;padding:14px;text-align:center;margin-bottom:12px}
.hero h1{color:#fff!important;font-size:1.4rem;margin:0} 
.upload-title{font-size:1.3rem;font-weight:800;text-align:center;color:#1f2937;margin-bottom:8px}
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:18px;box-shadow:0 6px 20px rgba(17,24,39,.07)}
textarea,input{background:#fff!important;color:#111827!important}
[data-testid="stFileUploaderDropzone"]{background:#f3f4f6!important;border:1px dashed #9ca3af}
.stButton>button{width:100%;border-radius:14px;font-weight:800;padding:.7rem 1rem;border:none;background:linear-gradient(135deg,#6e56ff,#8b6bff)!important}
.stButton>button *{color:#fff!important}
.mbox{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:16px 8px;text-align:center;margin-bottom:10px}
.mbox .v{font-size:1.8rem;font-weight:800;color:#6e56ff} .mbox .l{font-size:.85rem;color:#6b7280;font-weight:600}
.panel{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:14px 16px;margin-bottom:12px}
.chip{display:inline-block;padding:4px 11px;margin:3px;border-radius:999px;background:#eef0ff;border:1px solid #c9c2ff;color:#3b2fb0!important;font-size:.82rem}
.chip.ok{background:#e8f8ee;border-color:#a7e3bd;color:#166534!important} .chip.miss{background:#fdecec;border-color:#f5b5b5;color:#991b1b!important}
.foot{text-align:center;color:#6b7280;font-size:.85rem;margin-top:28px}
</style>""",unsafe_allow_html=True)

# --- DB ---
DB_FILE="resume_analyzer.db"
def q(sql,args=(),one=False,commit=False):
    conn=sqlite3.connect(DB_FILE); cur=conn.execute(sql,args); out=cur.fetchone() if one else cur.fetchall()
    if commit: conn.commit()
    conn.close(); return out
def init_db():
    conn=sqlite3.connect(DB_FILE); conn.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password_hash TEXT, created_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS resume_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, file_name TEXT, category TEXT, ats_score REAL, found_skills TEXT, missing_skills TEXT, extracted_text TEXT, analysis_date TEXT, full_json TEXT)"""); conn.commit(); conn.close()
def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def save_history(user_id,file_name,text,res):
    adv=res.get("adv"); category=adv["jobs"][0]["Role"] if adv else "General"; missing=[pretty(s) for s in adv["jobs"][0]["Missing"]] if adv else []
    q("INSERT INTO resume_history(user_id,file_name,category,ats_score,found_skills,missing_skills,extracted_text,analysis_date,full_json) VALUES(?,?,?,?,?,?,?,?,?)",(user_id,file_name,category,res["ats"],json.dumps(res["skills"]),json.dumps(missing),text,datetime.now().strftime("%Y-%m-%d %H:%M"),json.dumps(res)),commit=True)
init_db()
for _k,_v in {"logged_in":False,"user_id":None,"user_name":"","user_email":""}.items(): st.session_state.setdefault(_k,_v)
def logout():
    for k in list(st.session_state.keys()): del st.session_state[k]

def render_results(res:dict,key:str="cur"):
    st.markdown("## 📊 Results")
    c1,c2,c3=st.columns(3)
    for col,label,value in [(c1,"ATS Score",f"{res['ats']}%"),(c2,"Skills Found",len(res["skills"])),(c3,"Word Count",res["words"])]:
        col.markdown(f'<div class="mbox"><div class="v">{value}</div><div class="l">{label}</div></div>',unsafe_allow_html=True)
    st.progress(res["ats"]/100)
    left,right=st.columns(2)
    with left:
        rows="".join(f"<div>{'✅' if ok else '❌'} {name}</div>" for name,ok in res["checks"].items()); st.markdown(f'<div class="panel"><h4>📋 ATS Checklist</h4>{rows}</div>',unsafe_allow_html=True)
        tags="".join(f"<code>{s}</code> " for s in res["skills"]) or "No skills"; st.markdown(f'<div class="panel"><h4>🧠 Skills Detected</h4>{tags}</div>',unsafe_allow_html=True)
    with right:
        failed=[n for n,ok in res["checks"].items() if not ok]; tips="".join(f"<div>💡 {TIPS[n]}</div>" for n in failed) or "🎉 Great resume!"; st.markdown(f'<div class="panel"><h4>🚀 Improvement Tips</h4>{tips}</div>',unsafe_allow_html=True)
    adv=res.get("adv")
    if adv:
        d=adv["data"]; grade_label,_=grade(adv["total"]); st.markdown("## 🔬 Detailed Professional Analysis"); t1,t2,t3,t4=st.tabs(["👤 Profile","🧮 Score /100","💼 Job Roles","💡 Projects"])
        with t1:
            info=f"<div><b>Name:</b> {escape(d['name'])}</div><div><b>Email:</b> {escape(d['email'])}</div><div><b>Phone:</b> {escape(d['phone'])}</div><div><b>Experience:</b> {d['experience_years']} yrs</div>"; st.markdown(f'<div class="panel"><h4>👤 Candidate</h4>{info}</div>',unsafe_allow_html=True)
            st.markdown(f"<div class='panel'><b>Education:</b><br>{'<br>'.join(escape(x) for x in d['education']) or 'Not found'}</div>",unsafe_allow_html=True)
        with t2:
            st.subheader(f"CV Score: {adv['total']}/100 — {grade_label}")
            for cat,(val,mx) in adv["breakdown"].items(): st.write(f"**{cat}** — {val}/{mx}"); st.progress(max(0.0,min(1.0,float(val)/mx)))
        with t3:
            for i,job in enumerate(adv["jobs"][:6]):
                with st.expander(f"{job['Role']} — {job['Match %']}% match",expanded=(i==0)):
                    st.progress(job["Match %"]/100); st.write("**Top Companies:** "+", ".join(job["Companies"]))
                    ok_html="".join(f'<span class="chip ok">{escape(pretty(s))}</span>' for s in job["Matched"]); miss_html="".join(f'<span class="chip miss">{escape(pretty(s))}</span>' for s in job["Missing"])
                    st.markdown(f"**Matched:** {ok_html}",unsafe_allow_html=True); st.markdown(f"**To Learn:** {miss_html}",unsafe_allow_html=True)
        with t4:
            for cat,idea in adv["ideas"]: st.markdown(f"- **[{cat}]** {idea}")
        if adv["jd"]:
            st.markdown("### 🎯 Job Description Match")
            st.progress(adv["jd"]["match_percent"]/100)
            st.write(f"Match: {adv['jd']['match_percent']}%")
    st.download_button("⬇️ Download Full Report (TXT)",report_text(res),file_name="cv_report.txt",mime="text/plain",key=f"dl_{key}")

# --- MAIN ---
st.markdown("""<div class="hero"><h1>📄 Smart CV Analyzer Pro</h1></div>""",unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    with make_card("auth_card"):
        st.markdown('<div class="upload-title">🔐 Login to Continue</div>',unsafe_allow_html=True)
        t1,t2,t3=st.tabs(["🔐 Login","📝 Sign Up","🔑 Forgot Password"])
        with t1:
            e=st.text_input("Email",key="le"); p=st.text_input("Password",type="password",key="lp")
            if st.button("Login",key="b_login",type="primary"):
                u=q("SELECT id,name,email FROM users WHERE email=? AND password_hash=?",(e.strip().lower(),hp(p)),one=True)
                if u: st.session_state.update(logged_in=True,user_id=u[0],user_name=u[1],user_email=u[2]); st.rerun()
                else: st.error("Invalid email or password.")
        with t2:
            n=st.text_input("Full Name",key="sn"); e2=st.text_input("Email",key="se"); p1=st.text_input("Password",type="password",key="sp1"); p2=st.text_input("Confirm Password",type="password",key="sp2")
            if st.button("Create Account",key="b_signup",type="primary"):
                e2=e2.strip().lower()
                if not (n.strip() and e2 and p1): st.error("Fill all fields.")
                elif q("SELECT id FROM users WHERE email=?",(e2,),one=True): st.error("Email already registered.")
                elif p1!=p2: st.error("Passwords do not match.")
                else: q("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(n.strip(),e2,hp(p1),datetime.now().strftime("%Y-%m-%d")),commit=True); st.success("✅ Account created! Now login.")
        with t3:
            e3=st.text_input("Registered Email",key="fe"); np1=st.text_input("New Password",type="password",key="fp1")
            if st.button("Reset Password",key="b_reset",type="primary"):
                if not q("SELECT id FROM users WHERE email=?",(e3.strip().lower(),),one=True): st.error("Email not found.")
                else: q("UPDATE users SET password_hash=? WHERE email=?",(hp(np1),e3.strip().lower()),commit=True); st.success("✅ Password updated.")
    st.markdown('<div class="foot">Made with ❤️ for Students | Light Theme</div>',unsafe_allow_html=True); st.stop()

_uid=st.session_state["user_id"]
nav_col,out_col=st.columns([4,1])
with nav_col: page=st.radio("Menu",["🔍 Analyzer","📚 History","👤 Profile"],horizontal=True,key="nav",label_visibility="collapsed")
with out_col:
    if st.button("🚪 Logout",key="b_logout"): logout(); st.rerun()

if page.startswith("🔍"):
    # --- UPLOAD IN CENTER - NO SLIDE NEEDED ---
    with make_card("upload_center"):
        st.markdown('<div class="upload-title">📤 UPLOAD YOUR CV</div>',unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#6b7280;">PDF, DOCX, TXT - Instant Professional Analysis</p>',unsafe_allow_html=True)
        mode=st.radio("Input method",["Upload File","Paste Text"],horizontal=True,label_visibility="collapsed",key="mode_radio")
        uploaded,pasted=None,""
        if mode=="Upload File":
            uploaded=st.file_uploader("Upload resume",type=["pdf","docx","txt"],label_visibility="collapsed",key="resume_uploader")
            if uploaded: st.success(f"✅ Uploaded: {uploaded.name}")
        else: pasted=st.text_area("Paste resume text",height=220,label_visibility="collapsed",placeholder="Paste your resume text here...",key="paste_area")
        st.markdown("**💼 Job Description (Optional)**")
        jd_text=st.text_area("Job description",height=90,label_visibility="collapsed",placeholder="Paste JD for better matching...",key="jd_area")
        go=st.button("🔍 Analyze Resume Now",type="primary",key="analyze_btn")
    
    if go:
        text,fname="", "Pasted Text"
        try:
            if mode=="Upload File":
                if uploaded is None: st.warning("Please upload a file first")
                else: fname=uploaded.name; text=read_file(uploaded.name,uploaded.getvalue())
            else: text=pasted
        except Exception as exc: st.error(f"❌ {exc}")
        if text.strip():
            result=analyze(text,jd_text); st.session_state["result"]=result
            try: save_history(_uid,fname,text,result); st.toast("✅ Saved to History")
            except: pass
    res=st.session_state.get("result")
    if res: render_results(res,"cur")

elif page.startswith("📚"):
    import pandas as pd
    st.markdown("## 📚 History - Saved Data")
    rows=q("SELECT id,analysis_date,file_name,category,ats_score,extracted_text,full_json FROM resume_history WHERE user_id=?",(_uid,)); df=pd.DataFrame(rows,columns=["ID","Date","File Name","Category","ATS Score","text","full"])
    c1,c2=st.columns(2); c1.metric("📁 Total Scans",len(df)); c2.metric("📊 Avg Score",f"{df['ATS Score'].mean():.1f}%" if len(df) else "0%")
    if df.empty: st.info("No resumes yet - Upload first")
    else:
        st.dataframe(df[["Date","File Name","Category","ATS Score"]],width="stretch",hide_index=True)
        for _,r in df.iterrows():
            rid=int(r["ID"])
            with st.expander(f"{r['File Name']} - {r['Category']} - {r['ATS Score']:.0f}%"):
                payload=None
                if r["full"]:
                    try: payload=json.loads(r["full"])
                    except: payload=None
                if payload: render_results(payload,f"h{rid}")
                if st.button("🗑️ Delete",key=f"x{rid}"): q("DELETE FROM resume_history WHERE id=? AND user_id=?",(rid,_uid),commit=True); st.rerun()
else:
    st.markdown("## 👤 Profile"); st.write(f"**Name:** {st.session_state.get('user_name')}"); st.write(f"**Email:** {st.session_state.get('user_email')}"); total=q("SELECT COUNT(*) FROM resume_history WHERE user_id=?",(_uid,),one=True)[0]; st.metric("Resumes Analyzed",total)

st.markdown('<div class="foot">Made with ❤️ | 100% Light Theme | No OCR Error | Mobile Ready</div>',unsafe_allow_html=True)