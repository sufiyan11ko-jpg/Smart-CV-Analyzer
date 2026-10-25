# AI CV Analyzer & Career Matcher

**Tagline:** Analyze Your Resume. Discover Your Potential.

A TYBSc Computer Science mini-project built with Python and Streamlit. It extracts text from PDF/DOCX resumes, identifies information using transparent rules, estimates CV completeness, checks basic ATS-style indicators, matches skills to predefined roles, and generates a PDF report.

> **Honesty note:** This is a rule-based educational application, not a trained AI model, a commercial ATS clone, or an employer hiring decision. Its score is not scientifically validated.

## Features

- PDF and DOCX upload (maximum 8 MB by default).
- In-memory text extraction with helpful errors for unreadable/scanned PDFs.
- Conservative name detection, email/Indian phone matching, links and simple location detection.
- Editable categorized skills dictionary.
- Education, experience, project and certification extraction.
- Transparent CV score out of 100 with reasons and suggestions.
- Basic ATS-style checklist.
- Eight editable predefined career roles.
- Custom job description skill matching.
- Skill-gap analysis and 30-/60-day learning roadmap.
- Interactive Plotly charts and downloadable ReportLab PDF report.
- Optional unit tests.
- No paid APIs, API keys or permanent resume storage by the app.

## Project files

```text
AI_CV_Analyzer_College_Mini_Project/
├── app.py
├── requirements.txt
├── README.md
├── PROJECT_REPORT.md
├── VIVA_QUESTIONS.md
├── .gitignore
├── sample_resume.txt
└── tests.py
```

## 1. Install Python

1. Download Python 3.11 or newer from https://www.python.org/downloads/.
2. On Windows, tick **Add Python to PATH** during installation if that option is shown.
3. Open Command Prompt and verify:

```bash
python --version
```

If `python` is not recognized, retry the installer and enable PATH, or try `py --version`.

## 2. Install VS Code

Download https://code.visualstudio.com/ and install it. Open VS Code.

## 3. Open the project folder

1. Extract the project ZIP, if you received it as a ZIP.
2. In VS Code, choose **File → Open Folder**.
3. Select `AI_CV_Analyzer_College_Mini_Project`.
4. Select **Terminal → New Terminal**.
5. Confirm the terminal is in the correct folder:

Windows PowerShell:
```powershell
dir
```

macOS/Linux:
```bash
ls
```

You should see `app.py` and `requirements.txt`. If not, use `cd` to move into the extracted project folder.

## 4. Create and activate a virtual environment (recommended)

Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, open a Command Prompt terminal and run:
```bat
.venv\Scripts\activate.bat
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 5. Install dependencies

Run the requested command:

```bash
python -m pip install -r requirements.txt
```

Wait for installation to finish.

## 6. Run the application

```bash
python -m streamlit run app.py
```

Streamlit prints a local URL, commonly http://localhost:8501. Open it in your browser. Keep the terminal open while using the app.

## 7. Use the website

1. Start on the welcome screen. No score or candidate details are shown before a successful upload.
2. Upload a text-based PDF or DOCX under 8 MB.
3. Click **Analyze my CV**.
4. Review the dashboard tabs. Correct the detected candidate name if needed.
5. In **Career Matching**, choose a predefined role.
6. In **Custom Job Match**, paste a job description and click the match button.
7. In **Skill Gap & Roadmap**, choose a role and a 30- or 60-day plan.
8. In **PDF Report**, click **Prepare / refresh PDF report**, then **Download PDF Report**.

## 8. Test with the sample resume

`sample_resume.txt` is a fictional test fixture, not a directly supported upload format. To test the app, copy its text into Word and save it as `sample_resume.docx`, or paste it into a document and export as a text-based PDF. Do not use fictional data as a real candidate's resume.

## 9. Run automated tests

From the project directory with dependencies installed:

```bash
python -m unittest tests.py
```

The tests cover email and phone detection, skill matching, score arithmetic, job matching, DOCX extraction and PDF generation. Run them locally before submission. These tests do not replace manual testing with different real PDF layouts.

## Troubleshooting

### `python` is not recognized
Reinstall Python with PATH enabled, restart VS Code, or try `py --version` and `py -m pip ...`.

### `pip` or dependency installation fails
Try:
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
Check your internet connection and use a supported Python version.

### `ModuleNotFoundError`
Activate `.venv` and install requirements again in the same terminal. Confirm the selected VS Code interpreter is `.venv`.

### Wrong folder / `app.py` not found
Run `dir` (Windows) and use `cd path\to\AI_CV_Analyzer_College_Mini_Project`.

### Port already in use
Run:
```bash
python -m streamlit run app.py --server.port 8502
```
Then open the URL printed by Streamlit.

### Invalid or password-protected PDF
Try opening it in a PDF reader and exporting an unlocked, text-based PDF. This app does not bypass PDF passwords.

### Scanned PDF shows no readable text
The PDF may contain page images rather than selectable text. OCR is not included. Use an OCR-enabled tool to create a text-searchable PDF, or upload a DOCX/text-based PDF.

### DOCX extraction error
Open the file in Word/LibreOffice and save it as a new `.docx` file. Legacy `.doc` files are not supported directly.

### PDF report fails
Update dependencies with `python -m pip install -r requirements.txt`, restart the app, and try again. Report errors may be caused by unusually long or malformed extracted content; review the source file.

## Privacy and limitations

- The app processes upload bytes in memory and does not intentionally save resumes to disk. Streamlit hosting infrastructure may still process requests; public deployment should be treated as a privacy-sensitive choice.
- Do not upload resumes without permission. Avoid public demonstrations using real personal data.
- Text extraction can miss multi-column layouts, images, tables and unusual formatting.
- Scanned PDF OCR is not implemented.
- Name, education, experience and project parsing are heuristics; verify results.
- The skills dictionary and job-role requirements are editable but limited.
- A match percentage is not a probability of getting hired.
- The ATS review is a basic checklist, not a commercial ATS scoring system.

## Optional deployment: GitHub + Streamlit Community Cloud

See the deployment section in `PROJECT_REPORT.md` and follow the official documentation:
- https://docs.github.com/
- https://docs.streamlit.io/deploy/streamlit-community-cloud

Before publishing, remove real resumes and personal data from the repository, keep secrets out of Git, and understand that a public app can be used by anyone with access to its URL.

## Footer

TYBSc Computer Science Mini Project | Python & Streamlit
