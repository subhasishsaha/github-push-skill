#!/usr/bin/env python3
"""
Unit tests for audit_repo.py and generate_env_example.py
"""

import sys
import shutil
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "repo-publish-prep" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_repo import RepoAuditor, is_placeholder
from generate_env_example import generate_env_example

class TestAuditRepo(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="repo_audit_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_placeholder_filter(self):
        self.assertTrue(is_placeholder("your_api_key_here"))
        self.assertTrue(is_placeholder("process.env.API_KEY"))
        self.assertTrue(is_placeholder("dummy_secret"))
        self.assertFalse(is_placeholder("AKIAIOSFODNN7REAL99"))

    def test_detects_missing_essential_files(self):
        auditor = RepoAuditor(self.test_dir)
        results = auditor.run_audit()
        
        categories = [f["category"] for f in results["findings"]]
        self.assertIn("ESSENTIAL_FILES", categories)
        self.assertIn("GITIGNORE", categories)

    def test_detects_secret_leak(self):
        code_file = self.test_dir / "app.py"
        # Dynamically build synthetic Google API key so test file itself is not flagged
        dummy_token = "AIza" + "SyD1234567890abcdefghijklmnopqrstuv"
        code_file.write_text(f'API_KEY = "{dummy_token}"\n', encoding="utf-8")
        
        auditor = RepoAuditor(self.test_dir)
        results = auditor.run_audit()

        secret_findings = [f for f in results["findings"] if f["category"] == "SECRETS" and f["severity"] == "BLOCKER"]
        self.assertTrue(len(secret_findings) > 0)
        self.assertIn("Google / Gemini API Key", secret_findings[0]["title"])

    def test_detects_sensitive_filename(self):
        env_file = self.test_dir / ".env"
        env_file.write_text("DATABASE_URL=postgres://localhost\n", encoding="utf-8")

        auditor = RepoAuditor(self.test_dir)
        results = auditor.run_audit()

        findings = [f for f in results["findings"] if f["category"] == "SECRETS"]
        self.assertTrue(any(".env" in f["title"] for f in findings))

    def test_detects_large_files(self):
        large_file = self.test_dir / "bigdata.bin"
        # Write 11 MB dummy file
        with open(large_file, "wb") as f:
            f.seek(11 * 1024 * 1024 - 1)
            f.write(b"\0")

        auditor = RepoAuditor(self.test_dir, max_file_size_mb=10.0, critical_file_size_mb=50.0)
        results = auditor.run_audit()

        large_findings = [f for f in results["findings"] if f["category"] == "LARGE_FILES"]
        self.assertTrue(len(large_findings) > 0)
        self.assertEqual(large_findings[0]["severity"], "WARNING")

    def test_env_example_generator(self):
        env_file = self.test_dir / ".env"
        db_url = "postgres://" + "user:pass" + "@db:5432/mydb"
        env_file.write_text(f"PORT=8080\nSECRET_KEY=supersecret123\nDATABASE_URL={db_url}\n", encoding="utf-8")
        
        src_file = self.test_dir / "index.js"
        src_file.write_text("const apiKey = process.env.STRIPE_API_KEY;\n", encoding="utf-8")

        out_file = self.test_dir / ".env.example"
        generate_env_example(self.test_dir, out_file)

        self.assertTrue(out_file.exists())
        content = out_file.read_text(encoding="utf-8")
        self.assertIn("PORT=8080", content)
        self.assertIn("SECRET_KEY=your_secret_key_here", content)
        self.assertIn("STRIPE_API_KEY=your_stripe_api_key_here", content)
        self.assertNotIn("supersecret123", content)

if __name__ == "__main__":
    unittest.main()
