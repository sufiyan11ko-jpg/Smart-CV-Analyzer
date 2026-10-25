# Viva Questions and Answers — AI CV Analyzer & Career Matcher

## 1-minute project introduction

Good morning, sir/madam. My project is **AI CV Analyzer & Career Matcher**. It is a Python and Streamlit web application that accepts PDF and DOCX resumes, extracts readable text, detects contact details and configured skills, and identifies education, experience, projects and certifications where possible. It calculates a transparent resume-completeness score, gives a basic ATS-style checklist, matches detected skills with predefined roles, and generates a PDF report. PyMuPDF and python-docx are used for extraction, pandas for tables, Plotly for charts and ReportLab for PDF generation. The current version is rule-based and does not use a trained AI model or make hiring decisions.

## 2-minute project explanation

The user first sees a welcome screen and uploads a PDF or DOCX file. The app checks the extension and file size, then extracts text using PyMuPDF or python-docx. Regular expressions identify email, phone and some links. A configurable skills dictionary is searched in the extracted text, and heading rules attempt to identify education, experience, projects and certifications.

The scoring function gives points to eight sections, with a maximum total of 100. The role matcher compares detected skills against required skills for eight predefined roles. A user can also paste a job description, see matched and missing configured skills, and generate a 30- or 60-day learning roadmap. Plotly displays the results, and ReportLab creates a PDF report. Session state keeps the analysis available during normal Streamlit reruns. The application is educational: extraction can make mistakes, scanned PDF OCR is not included, and the score is not a validated hiring measure.

## Questions and simple answers

### 1. What is the title of your project?
AI CV Analyzer & Career Matcher.

### 2. What is the main objective?
To extract resume information, estimate completeness, show improvement suggestions and compare skills with job roles.

### 3. Which language is used?
Python is used for the application logic.

### 4. Why did you use Streamlit?
It lets us build an interactive web app directly in Python with less front-end code.

### 5. Is this a real trained AI model?
No. This version uses transparent rule-based text processing and a predefined skills dictionary.

### 6. What is PyMuPDF?
A Python library that can extract selectable text from PDF files.

### 7. What is python-docx?
A library for reading and writing Microsoft Word DOCX documents.

### 8. What is a regular expression?
A pattern used to find text such as emails, phone numbers and years.

### 9. Why use pandas?
It organizes extracted results into tables for the dashboard.

### 10. Why use Plotly?
It creates interactive charts with labels and tooltips.

### 11. Why use ReportLab?
It generates a downloadable PDF report from analysis results.

### 12. What is Streamlit session state?
It stores values between Streamlit reruns during a user's session.

### 13. Why is session state needed?
Without it, a rerun could lose the current resume analysis.

### 14. How is the CV score calculated?
The app awards points for eight sections using rules, then sums them to a maximum of 100.

### 15. What are the score weights?
Contact 10, summary 10, skills 20, education 15, experience 15, projects 15, certifications 5, readability 10.

### 16. Are the score grades industry standards?
No. They are configurable categories defined for this project.

### 17. How are skills detected?
The app searches extracted text for configured terms using case-insensitive matching and boundaries.

### 18. Can the skill dictionary be edited?
Yes. Edit SKILL_CATEGORIES near the top of app.py.

### 19. How does job matching work?
It calculates matched required skills divided by total required skills, multiplied by 100.

### 20. Does a 100% match guarantee a job?
No. It only means all configured skills were found in the resume text.

### 21. What is an ATS?
An Applicant Tracking System is software employers may use to manage applications.

### 22. Does this app copy a commercial ATS?
No. It provides a small rule-based compatibility checklist only.

### 23. Can it read scanned PDFs?
Not directly. Scanned PDFs need OCR, which is not included in this version.

### 24. What happens if the PDF has no text?
The app shows an error explaining that readable text was not extracted and OCR may be needed.

### 25. Which file formats are supported?
PDF and DOCX.

### 26. Why is there a file size limit?
It reduces accidental memory use and keeps the student app manageable.

### 27. Does the app permanently save resumes?
The application does not intentionally save uploaded resumes to disk; it processes them in memory.

### 28. Why should users verify extracted details?
Resume layouts vary, so rules may miss or misclassify text.

### 29. What is a custom job description matcher?
It compares configured skills in a pasted job description with skills detected in the resume.

### 30. What happens if no configured skills are in the job description?
The app says a percentage cannot be calculated rather than showing a misleading value.

### 31. What is a skill gap?
A list of required skills that were not detected in the resume.

### 32. What is the learning roadmap?
A general 30- or 60-day plan suggesting topics for missing skills.

### 33. How is the candidate name detected?
The app inspects early lines and ignores common resume headings, contact lines and lines with digits.

### 34. Why can name detection be wrong?
The first line may contain a title or formatting that the simple rules cannot understand.

### 35. What is the role of HTML escaping?
It reduces the risk of user-provided text being interpreted as HTML in rendered output.

### 36. Why do we use try/except?
To handle invalid files and extraction/report errors without crashing the whole app.

### 37. How do you run the app?
Run `python -m streamlit run app.py` in the project folder.

### 38. How do you install dependencies?
Run `python -m pip install -r requirements.txt`.

### 39. How do you run automated tests?
Run `python -m unittest tests.py`.

### 40. What does the test suite check?
Email, phone, skills, score arithmetic, role matching, DOCX extraction and PDF generation.

### 41. What are the project's limitations?
Heuristic extraction, no OCR, limited skill vocabulary, no live jobs and no validated hiring score.

### 42. What is the future scope?
OCR, improved NLP, more test cases, configurable role data and carefully designed privacy features.

### 43. Why is there no database?
The mini-project keeps configuration in Python dictionaries and avoids storing sensitive resumes.

### 44. What is the difference between PDF and DOCX extraction?
PDF text is extracted page by page with PyMuPDF; DOCX paragraphs and table cells are read with python-docx.

### 45. How are projects extracted?
The app looks for a recognized Projects heading and treats following lines as project text until the next recognized heading.

### 46. Can the application identify all certifications perfectly?
No. It extracts lines under a recognized section; users must verify the results.

### 47. What is a false positive in skill detection?
It is when a term is detected but does not actually represent the candidate's skill.

### 48. Why is the app useful for students?
It gives a structured checklist and helps students identify resume details to improve.

### 49. What is the tagline?
Analyze Your Resume. Discover Your Potential.

### 50. What should you say honestly if asked where AI is used?
This version is rule-based, not a trained AI model. The title uses AI in a broad project context, but the implemented logic is deterministic text analysis.

## How to explain the code

1. Start with the constants and editable `SKILL_CATEGORIES` and `JOB_ROLES` dictionaries.
2. Explain `extract_pdf()` and `extract_docx()` as format-specific text extractors.
3. Explain `find_email()`, `find_phone()` and `detect_skills()` as text-processing functions.
4. Explain `build_profile()` as the function that combines extracted information into one dictionary.
5. Explain `score_resume()` as the weighted rule-based score calculation.
6. Explain `match_role()` and `custom_job_match()` as skill-overlap functions.
7. Explain `make_pdf_report()` as the ReportLab PDF builder.
8. Explain the Streamlit tabs as the user interface and `st.session_state` as the way results persist across reruns.

## Likely teacher questions

**Q: Why do you call it an AI CV Analyzer if it does not use machine learning?**  
A: The implemented version is a rule-based prototype for the project topic. It is important to be honest: it does not train or call an AI model. A future version could add NLP or a validated model.

**Q: Is the score scientifically accurate?**  
A: No. It is a transparent completeness estimate created for this mini-project. It should not be used as a hiring decision.

**Q: What if extraction is wrong?**  
A: The user should verify the output. The app shows extracted text and allows the detected name to be corrected.

**Q: What is the most important limitation?**  
A: Resume layouts vary, so heading-based extraction can miss details. OCR for scanned PDFs is not included.

## Hinglish revision notes

- **Rule-based:** Fixed rules ke basis par result nikalta hai; trained AI model nahi hai.
- **Regex:** Text mein email, phone ya year jaise patterns dhoondhne ka tareeqa.
- **Session state:** Streamlit rerun hone par analysis ko session mein retain karta hai.
- **Score:** Resume completeness ka educational estimate hai, job milne ki guarantee nahi.
- **Job match:** Resume mein detected skills aur role ki required skills ka overlap.
- **OCR:** Image/scanned PDF se text nikalne ki technology; current project mein included nahi hai.
