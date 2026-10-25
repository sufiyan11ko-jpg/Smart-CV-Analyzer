# AI CV Analyzer & Career Matcher — Project Report

**Course:** TYBSc Computer Science  
**Project type:** College mini-project  
**Technology:** Python, Streamlit, PyMuPDF, python-docx, pandas, Plotly, ReportLab  
**Tagline:** Analyze Your Resume. Discover Your Potential.

> Fill in student name, roll number, college, guide and submission date according to your college format. Test-case results must be filled after you execute the tests; no test results are claimed here.

## Abstract

AI CV Analyzer & Career Matcher is a web application that extracts readable text from PDF and DOCX resumes and uses transparent rule-based methods to identify contact details, configured skills, education, experience, projects and certifications. It estimates resume completeness using a weighted score, provides a basic ATS-style checklist, compares detected skills with predefined career roles, supports matching against a pasted job description, and creates a downloadable PDF report. The application is intended for learning and self-review. It does not use a trained AI model, connect to employers, or make hiring decisions.

## 1. Introduction

A resume contains important information about a candidate's education, skills and experience, but reviewing it manually can take time. This project demonstrates how Python text processing and a simple web interface can help organize resume information and give transparent feedback.

## 2. Problem statement

Students and entry-level applicants may not know whether their resume contains clear sections, how to present their skills, or which predefined job roles use similar skills. A simple local application can help them inspect extracted information and identify gaps, while keeping the rules visible and understandable.

## 3. Objectives

- Build a professional Streamlit interface.
- Accept PDF and DOCX files.
- Extract readable resume text.
- Identify contact details and resume sections where possible.
- Detect skills from an editable dictionary.
- Calculate a transparent completeness score out of 100.
- Provide ATS-style checklist feedback.
- Match skills to predefined roles and pasted job descriptions.
- Suggest learning topics for missing skills.
- Generate a PDF report from current analysis data.
- Keep processing simple, with no paid API or intentional permanent resume storage.

## 4. Existing system

Traditional manual review depends on the reviewer's time and consistency. Some online services use proprietary algorithms and may require accounts or subscriptions. Commercial applicant tracking systems vary and are not reproduced by this student project.

## 5. Proposed system

The user uploads a PDF or DOCX. The application validates the file, extracts text, processes it with regular expressions and heading rules, calculates the score, compares configured skills, displays a dashboard and optionally creates a PDF report.

## 6. Scope

Included:
- PDF/DOCX text extraction.
- Contact and section heuristics.
- Skills dictionary and predefined role database in Python source.
- Rule-based scoring and ATS-style checklist.
- Custom job-description skill matching.
- Interactive charts and PDF report generation.
- Local test suite.

Not included:
- OCR for scanned documents.
- Trained machine-learning model or generative AI.
- Live job listings or employer integrations.
- User accounts, databases, permanent resume storage or authentication.
- Exact compatibility scoring for commercial ATS products.

## 7. Requirements

### Hardware
- Computer capable of running a supported Python version.
- Internet connection for initial package installation.
- Sufficient memory to run Python, Streamlit and a browser.

### Software
- Windows 10/11 (other Python-supported systems may work).
- Python 3.11 or newer compatible with installed packages.
- Visual Studio Code.
- Required packages in `requirements.txt`.
- Modern web browser.

## 8. Technology descriptions

- **Python:** Main programming language; handles extraction, text processing and scoring.
- **Streamlit:** Creates the interactive web application using Python.
- **PyMuPDF (fitz):** Extracts selectable text from PDF pages.
- **python-docx:** Reads paragraphs and tables from DOCX files.
- **Regular expressions (`re`):** Detect email addresses, phone numbers, years and headings.
- **pandas:** Converts results into tables for display.
- **Plotly:** Generates interactive charts.
- **ReportLab:** Creates the downloadable PDF report.
- **HTML/CSS:** Provides custom visual styling inside Streamlit.

## 9. System architecture

1. **Presentation layer:** Streamlit upload screen, sidebar, tabs, cards and charts.
2. **Validation layer:** Checks extension and file size; catches extraction errors.
3. **Extraction layer:** PyMuPDF for PDF and python-docx for DOCX.
4. **Analysis layer:** Regex, heading matching, skills dictionary and section heuristics.
5. **Scoring and matching layer:** Weighted completeness score, ATS checklist and job skills overlap.
6. **Reporting layer:** ReportLab creates a PDF from the same in-memory analysis data.
7. **Session state:** Retains analysis results between Streamlit reruns during the current session.

## 10. Modules

### 10.1 File upload and extraction
The uploader accepts PDF and DOCX up to a configurable 8 MB. Files are processed as bytes in memory. Empty or unreadable documents produce a useful error. OCR is not implemented, so image-only PDFs require OCR before upload.

### 10.2 Candidate information
Email is detected with a regular expression. Phone detection targets common Indian mobile formats. Name detection examines early lines conservatively and offers a user correction field. Link and location detection are simple heuristics.

### 10.3 Skills extraction
The editable `SKILL_CATEGORIES` dictionary groups skill names. Each configured term is searched in extracted text using boundaries intended to reduce partial-word matches. Detected terms are deduplicated and grouped.

### 10.4 Section extraction
Education, experience, projects and certifications are extracted from recognizable headings. Resume formatting varies, so these are heuristic results and should be checked by the user. The app does not infer missing facts.

## 11. Scoring algorithm

Weights total 100:

| Section | Maximum |
|---|---:|
| Contact Information | 10 |
| Professional Summary | 10 |
| Skills | 20 |
| Education | 15 |
| Experience | 15 |
| Projects | 15 |
| Certifications | 5 |
| Readability and Structure | 10 |
| **Total** | **100** |

Each section awards points according to explicit rules in `score_resume()`. The final score is the sum of section points and capped at 100. Grade bands are A (85–100), B (70–84), C (50–69) and D (0–49). A modest baseline is used when no employment is detected so freshers are not automatically given zero experience-section points; the explanation states that no professional experience was detected. The score estimates completeness only and is not validated against hiring outcomes.

## 12. Job matching algorithm

Each predefined role has a required skills list. The app compares it with detected resume skills:

`Match percentage = (number of matched required skills / total required skills) × 100`

If a role has no configured requirements, the implementation returns 0 safely. Custom job descriptions are scanned for configured skills; a percentage is shown only if at least one configured skill was detected in the job description. Missing skills become learning suggestions, not claims about existing qualifications.

## 13. ATS-style checklist

The checklist evaluates contact information, recognizable headings, skills, education, experience/project evidence, extracted text length and possible unusual characters. For a selected role, it can also check role-skill overlap. This is a simple student implementation, not a replica of any commercial ATS.

## 14. Database and storage

The current version has no database. The skills dictionary and role requirements are Python dictionaries in `app.py`. Uploaded bytes and extracted text are held in memory during the session. The application does not intentionally write resumes to disk. Streamlit hosting and browser infrastructure still have their own data-processing characteristics, so public deployment requires privacy consideration.

## 15. Security and privacy

- Enforce an upload-size limit and file-type allowlist.
- Do not log full resume contents.
- Escape user-derived text in PDF paragraphs and custom HTML tags.
- Avoid permanent resume storage.
- Do not upload personal resumes to public repositories.
- Review hosting and privacy terms before public deployment.
- Treat uploaded content as untrusted and verify all extraction results.

## 16. Testing plan

The included `tests.py` tests email detection, Indian phone detection, skills detection, score arithmetic, job matching, empty custom job descriptions, DOCX extraction and PDF generation.

Run:

```bash
python -m unittest tests.py
```

### Test-case results template — fill after running

| Test | Expected result | Actual result | Status |
|---|---|---|---|
| Email detection | Correct email or Not detected | To be completed after execution | Pending |
| Indian phone detection | Common mobile format detected | To be completed after execution | Pending |
| Skill detection | Only configured terms in text returned | To be completed after execution | Pending |
| Score arithmetic | Sum equals displayed score, 0–100 | To be completed after execution | Pending |
| Role matching | Formula produces expected percentage | To be completed after execution | Pending |
| DOCX extraction | Paragraph/table text returned | To be completed after execution | Pending |
| PDF extraction | Selectable PDF text returned | To be completed manually | Pending |
| Scanned PDF | OCR-needed message if no text | To be completed manually | Pending |
| PDF report | Output begins with PDF signature and opens | To be completed after execution | Pending |
| Replacement resume | New successful analysis replaces old result | To be completed manually | Pending |

## 17. Limitations

- Resume formats differ; section extraction may miss information.
- Multi-column layouts, images, tables and text order can affect extraction.
- OCR is not included.
- Skill matching only recognizes terms in the configured dictionary.
- Name and location detection can be uncertain.
- The score is not scientifically validated.
- No live jobs, employer data, authentication or database is included.
- A role match does not guarantee a job.
- The ATS checklist does not represent a commercial product.

## 18. Future scope

- Optional OCR with a free OCR engine.
- Improved NLP-based entity and section extraction.
- Editable role requirements through a separate configuration file.
- User-reviewed corrections and export options.
- Unit/integration tests with a larger safe test corpus.
- Optional secure account storage only if justified and consented to.
- Deployment with privacy notice, file limits and abuse protections.

## 19. Conclusion

AI CV Analyzer & Career Matcher demonstrates document extraction, rule-based text analysis, scoring, skill overlap, interactive visualization and PDF reporting in one Streamlit application. Its transparent rules make it suitable for a TYBSc Computer Science mini-project and easier to explain during a viva. The results are educational guidance and must be verified by the user.

## 20. Official documentation

- Python: https://docs.python.org/3/
- Streamlit: https://docs.streamlit.io/
- PyMuPDF: https://pymupdf.readthedocs.io/
- python-docx: https://python-docx.readthedocs.io/
- pandas: https://pandas.pydata.org/docs/
- Plotly Python: https://plotly.com/python/
- ReportLab: https://docs.reportlab.com/
- GitHub Docs: https://docs.github.com/
- Streamlit Community Cloud: https://docs.streamlit.io/deploy/streamlit-community-cloud
