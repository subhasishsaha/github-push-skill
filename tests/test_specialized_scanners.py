#!/usr/bin/env python3
"""
Unit tests for specialized scanners:
- scan_stubs.py
- scan_dependencies.py
- scan_path_leaks.py
- scan_doc_drift.py
"""

import sys
import shutil
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "repo-publish-prep" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from scan_stubs import scan_stubs
from scan_dependencies import scan_dependency_mismatches
from scan_path_leaks import scan_path_leaks
from scan_doc_drift import scan_doc_drift

class TestSpecializedScanners(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="spec_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_stub_scanner_detects_empty_and_not_implemented(self):
        py_file = self.test_dir / "service.py"
        py_file.write_text(
            "def hollow_func():\n"
            "    pass\n\n"
            "def not_impl():\n"
            "    raise NotImplementedError('To be done')\n\n"
            "def swallow_error():\n"
            "    try:\n"
            "        do_work()\n"
            "    except Exception:\n"
            "        pass\n",
            encoding="utf-8"
        )

        findings = scan_stubs(self.test_dir)
        types = [f["type"] for f in findings]
        self.assertIn("EMPTY_FUNCTION_PASS", types)
        self.assertIn("NOT_IMPLEMENTED_ERROR", types)
        self.assertIn("SILENT_EXCEPTION_SWALLOW", types)

    def test_dependency_scanner_flags_undeclared_packages(self):
        # Python file importing a third party package not in requirements
        py_file = self.test_dir / "app.py"
        py_file.write_text("import sys\nimport os\nimport requests\nimport numpy as np\n", encoding="utf-8")

        req_file = self.test_dir / "requirements.txt"
        req_file.write_text("requests>=2.28.0\n", encoding="utf-8")

        results = scan_dependency_mismatches(self.test_dir)
        missing_pkgs = [f["package"] for f in results["findings"]]
        
        # 'numpy' is imported but not in requirements.txt
        self.assertIn("numpy", missing_pkgs)
        # 'requests' is declared, so it should NOT be flagged as missing
        self.assertNotIn("requests", missing_pkgs)
        # 'sys' and 'os' are stdlib, so they should NOT be flagged
        self.assertNotIn("sys", missing_pkgs)
        self.assertNotIn("os", missing_pkgs)

    def test_path_leaks_detects_local_user_paths(self):
        code_file = self.test_dir / "config.py"
        # Dynamically build synthetic user paths so the test file itself is not flagged
        win_path = "C:" + "\\\\Users\\\\" + "Subhasish" + "\\\\data"
        posix_path = "/" + "home" + "/developer/app/logs"
        ip_addr = "192." + "168." + "1.55"
        code_file.write_text(
            f'DATA_DIR = "{win_path}"\n'
            f'LOG_DIR = "{posix_path}"\n'
            f'DEV_SERVER = "{ip_addr}"\n',
            encoding="utf-8"
        )

        findings = scan_path_leaks(self.test_dir)
        self.assertTrue(len(findings) >= 3)
        descriptions = " ".join(f["description"] for f in findings)
        self.assertIn("Windows user directory path", descriptions)
        self.assertIn("POSIX user home directory path", descriptions)
        self.assertIn("private IP address", descriptions)

    def test_doc_drift_detects_dead_relative_links(self):
        readme = self.test_dir / "README.md"
        readme.write_text(
            "# Test Project\n\n"
            "See our [Documentation](./docs/guide.md) and [Real File](./real.txt).\n"
            "Also visit [External Link](https://example.com).\n",
            encoding="utf-8"
        )

        # Create real.txt, but do not create docs/guide.md
        (self.test_dir / "real.txt").write_text("Hello", encoding="utf-8")

        findings = scan_doc_drift(self.test_dir)
        dead_targets = [f["target"] for f in findings]

        self.assertIn("./docs/guide.md", dead_targets)
        self.assertNotIn("./real.txt", dead_targets)
        self.assertNotIn("https://example.com", dead_targets)

if __name__ == "__main__":
    unittest.main()
