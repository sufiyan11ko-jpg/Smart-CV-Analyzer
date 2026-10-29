# 📄 Smart CV Analyzer Pro

> **Analyze. Improve. Get Hired.**
> An AI-powered Resume Analyzer that helps you beat the ATS, find skill gaps, and land your dream job.

![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OCR](https://img.shields.io/badge/OCR-Tesseract-5A9BD4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

### 🔗 Live Demo
👉 **[Try Live App Here](https://your-app-link.streamlit.app)** 
*(Deploy ke baad apna link yaha daal dena)*

---

## ✨ Key Features

- **📤 Upload Anything:** Supports **PDF, DOCX, TXT, JPG, JPEG, PNG** - Even image resumes via OCR
- **🤖 ATS Score (0-100%):** 7-point professional checklist - Email, Phone, Skills, Education, Experience, Length, Action Verbs
- **🧠 100+ Skills Detection:** Auto-categorizes skills into Programming, Web, Data & AI, Database, Cloud & DevOps, Mobile & Soft Skills
- **💼 Dream Job Matcher:** Matches your resume with 10 top roles like Data Scientist, Full Stack Developer, DevOps Engineer + suggests top hiring companies
- **🎯 JD vs Resume:** Paste any Job Description and get Match % + Missing Keywords instantly
- **📊 100-Point Detailed Report:** Breakdown of Contact Info, Skills, Education, Experience, Projects, Certifications
- **💡 Project Ideas:** Get personalized project suggestions based on your current skills to improve your resume
- **🔐 Full Auth System:** Secure Login / Signup / Forgot Password
- **📚 Smart History:** Saves every resume you analyze with date, category & score
- **📥 One-Click Report:** Download full analysis as TXT file

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Streamlit, Custom CSS, HTML |
| **Backend** | Python |
| **Resume Parsing** | PyPDF2, python-docx, Pillow + pytesseract (OCR) |
| **Database** | SQLite3 |
| **Data Processing** | Pandas, Regex, JSON |
| **Deployment** | Streamlit Cloud + GitHub |

---

## 📁 Project Structure
Smart-CV-Analyzer/
│
├── app.py                 # Main Application File
├── requirements.txt       # Python Libraries
├── packages.txt           # System Packages for Cloud (Tesseract OCR)
├── README.md              # Documentation
└── resume_analyzer.db     # Auto-created Databasejavascript
---

## 🚀 Run Locally in VS Code (2 Minutes)

**Step 1: Clone / Create Folder**
```bash
# Agar GitHub se clone karna hai
git clone https://github.com/your-username/smart-cv-analyzer.git
cd smart-cv-analyzerStep 2: Install Python Librariesbashpip install -r requirements.txtStep 3: Install Tesseract (Only for JPG/PNG Support)Windows: Download & Install from Tesseract Official Wiki - Select English during installLinux/Mac: sudo apt-get install tesseract-ocrStep 4: Run the Appbashpython -m streamlit run app.pyApp will open at http://localhost:8501☁️ Deploy to Streamlit Cloud (Free Hosting)Push these 3 files to your GitHub repo: app.py, requirements.txt, packages.txtGo to share.streamlit.io and login with GitHubClick Create app -> Select your repo smart-cv-analyzer -> Main file: app.py -> Click Deploy!Your live link will be ready in 2-3 minutes!IMPORTANT: packages.txt is mandatory for image (JPG/PNG) support on cloud. Without it, image upload will fail.javascripttesseract-ocr
tesseract-ocr-eng📊 How Scoring WorksCategoryMarksWhat it ChecksContact Info10Name, Email, Phone, LinkedIn/GitHubSkills25Number of technical + soft skillsEducation10Degree mentionedExperience20Experience years & detailsProjects15Number of projectsCertifications5CertificatesFormatting & Impact15Word count, metrics, action verbsTotal100Final CV ScoreGrade System:80-100 = Excellent 🌟65-79 = Good 👍45-64 = Average ⚠️<45 = Needs Work ❌📸 ScreenshotsLoginAnalyzerDetailed ScoreSecure AuthUpload PDF/JPGJob Roles & Projects👨‍💻 AuthorSufiyanGitHub: @your-usernameLinkedIn: Your LinkedInProject Link: Smart CV Analyzer ProIf you found this helpful, please give it a ⭐ on GitHub!🤝 ContributingFork the projectCreate your feature branch (git checkout -b feature/AmazingFeature)Commit your changes (git commit -m 'Add some AmazingFeature')Push to the branch (git push origin feature/AmazingFeature)Open a Pull Request📜 LicenseDistributed under the MIT License. See LICENSE for more information.Crafted for Careers | Analyze. Improve. Get Hired.javascript
**Bas itna kar:**
1.  `your-username` ki jagah apna GitHub username daal de (2 jagah hai)
2.  Deploy ke baad `your-app-link` ki jagah apna Streamlit link daal de

**Ho gaya toh push kar de - tera GitHub repo top 1% lagega.**