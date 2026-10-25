"""Lightweight unit tests for the rule-based CV Analyzer. Run: python -m unittest tests.py"""
import unittest
import app


class ResumeAnalyzerTests(unittest.TestCase):
    def test_email_detection(self):
        self.assertEqual(app.find_email("Contact: test.user@example.com"), "test.user@example.com")
        self.assertEqual(app.find_email("No email here"), "Not detected")

    def test_indian_phone_detection(self):
        self.assertNotEqual(app.find_phone("Phone: +91 98765 43210"), "Not detected")
        self.assertEqual(app.find_phone("Roll number: 123456"), "Not detected")

    def test_skill_detection(self):
        result = app.detect_skills("I used Python, SQL and GitHub for a project.")
        all_skills = {s for values in result.values() for s in values}
        self.assertIn("Python", all_skills)
        self.assertIn("SQL", all_skills)

    def test_score_total_and_grade(self):
        text = """Name Person
Email: person@example.com
Phone: 9876543210
PROFESSIONAL SUMMARY
A motivated student with a strong interest in software development and a desire to learn.
SKILLS
Python SQL Git
EDUCATION
BSc Computer Science 2027
PROJECTS
Student application
Description of the project with enough details to explain the features and technologies used.
"""
        profile = app.build_profile(text, "test.txt")
        score = app.score_resume(text, profile)
        self.assertGreaterEqual(score["score"], 0)
        self.assertLessEqual(score["score"], 100)
        self.assertEqual(sum(x["Awarded"] for x in score["breakdown"]), score["score"])
        self.assertIn(score["grade"], ["A", "B", "C", "D"])

    def test_job_matching(self):
        skills = {"Programming Languages": ["Python"], "Database Management": ["SQL"]}
        result = app.match_role(skills, "Python Developer")
        self.assertEqual(result["Match percentage"], 40)
        self.assertIn("Python", result["Matched skills"])

    def test_empty_job_description_skills(self):
        result = app.custom_job_match("Resume text", {}, "Friendly, collaborative teammate")
        self.assertIsNone(result["percentage"])

    def test_docx_extraction(self):
        from docx import Document
        from io import BytesIO
        doc = Document()
        doc.add_paragraph("Test Resume")
        buf = BytesIO()
        doc.save(buf)
        extracted = app.extract_docx(buf.getvalue())
        self.assertIn("Test Resume", extracted)

    def test_pdf_generation(self):
        text = "Test Person\nEmail: test@example.com\nPhone: 9876543210\nSKILLS\nPython\nEDUCATION\nBSc Computer Science 2027"
        profile = app.build_profile(text, "test.txt")
        score = app.score_resume(text, profile)
        roles = [app.match_role(profile["skills"], role) for role in app.JOB_ROLES]
        ats = app.ats_check(text, profile)
        feedback = app.get_feedback(text, profile, score, ats)
        pdf = app.make_pdf_report(profile, score, roles, ats, feedback)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)


if __name__ == "__main__":
    unittest.main()
