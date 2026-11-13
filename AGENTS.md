# Agent Instructions: Adversarial Codebase Preparation Protocol

This repository implements the **`repo-publish-prep`** protocol — an adversarial, closed-loop multi-agent verification system for preparing, auditing, sanitizing, and packaging codebases for GitHub, GitLab, Bitbucket, and remote Git hosting.

## The 3-Phase Execution Protocol

Follow [skills/repo-publish-prep/SKILL.md](./skills/repo-publish-prep/SKILL.md) strictly:

### Phase 1: README Verification Gate
1. **If README.md exists:**
   - Read `README.md` and verify with the user if it matches intended application behavior.
   - If drifted, **stop execution immediately** and ask for clarification.
   - If verified, proceed to Phase 2.
2. **If README.md is missing:**
   - Launch `agent_01` (Codebase Archeologist) to inspect code and draft findings report (Agent 01 never writes the README).
   - Launch `agent_02` (Verifier) to independently check Agent 01's report against the code.
   - If verification fails, Agent 01 discards and re-runs.
   - Once verified, Agent 02 drafts `README.md` and submits it to user for confirmation.

### Phase 2: Implementation Integrity Loop (Agent 03 ⇄ Agent 04)
1. **Launch `agent_03` (Adversarial Auditor):**
   - Pure audit role (no code edits).
   - Runs forensic AST scanners (`scan_stubs.py`, `scan_dependencies.py`, `scan_path_leaks.py`, `scan_doc_drift.py`).
   - Writes report to `.audit/verification/agent_03/report.md`.
2. **Launch `agent_04` (Remediation Engineer):**
   - Implements full, production-grade fixes as specified in `report.md`.
   - Returns control to `agent_03`.
3. **Re-verification Loop:**
   - Agent 03 re-runs the audit. When all checks pass, Phase 2 is complete.

### Phase 3: Final Certification
1. Write the final certification report to `.agents/final_report/report.md`.
2. Present the executive summary to the user and stage clean Git commits.
