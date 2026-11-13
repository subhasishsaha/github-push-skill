# Agent Instructions: Orchestrator-Driven Codebase Preparation Protocol

This repository implements the **`repo-publish-prep`** protocol — an orchestrator-driven multi-agent verification system for preparing, auditing, sanitizing, and packaging codebases for GitHub, GitLab, Bitbucket, and remote Git hosting.

## The Orchestrator Protocol & Behavioral Isolation

The primary agent must act as the **Orchestrator**, coordinating specialized subagents (`agent_01`, `agent_02`, `agent_03`, `agent_04`) rather than performing audits directly.

### Behavioral Isolation Contracts (`.audit/.agents/`)
To prevent subagents from overstepping their scope (e.g. Agent 04 editing Agent 03's audit report), the Orchestrator injects behavioral contracts from `.audit/.agents/`:
- **`agent_01.md`**: Permitted writes: `.audit/reports/agent_01_report.md` & `.audit/.scratch/`. Forbidden: `README.md`, application code.
- **`agent_02.md`**: Permitted writes: `README.md`. Forbidden: `.audit/reports/`, application code.
- **`agent_03.md`**: Permitted writes: `.audit/.scratch/` & `.audit/reports/agent_03_report.md`. Forbidden: ANY application code or `README.md`.
- **`agent_04.md`**: Permitted writes: Application code & configs. **CRITICAL RESTRICTION: MUST NEVER TOUCH `.audit/reports/` (INCLUDING `agent_03_report.md` AND `final_report.md`)!** All audit reports are strictly owned by Agent 03 and the Orchestrator.

Subagents dynamically create their own targeted audit and discovery scripts in `.audit/.scratch/` for each run.

### Phase 1: README Verification Gate
1. **If README.md exists:**
   - Read `README.md` and verify with the user if it matches intended application behavior.
   - If drifted, **stop execution immediately** and ask for clarification.
   - If verified, proceed to Phase 2.
2. **If README.md is missing:**
   - Orchestrator spawns `agent_01` (Codebase Archeologist) to inspect code and draft findings in `.audit/reports/agent_01_report.md` (Agent 01 never writes the README).
   - Orchestrator spawns `agent_02` (Verifier) to independently check Agent 01's report against the code.
   - If verification fails, Agent 01 discards and re-runs.
   - Once verified, Agent 02 drafts `README.md` and submits it to user for confirmation.

### Phase 2: Implementation Integrity Loop (Agent 03 ⇄ Agent 04)
1. **Launch `agent_03` (Adversarial Auditor):**
   - Pure audit role (no code edits).
   - Writes on-demand audit scripts in `.audit/.scratch/` to check:
     - Eagerness bias & stubs
     - Undeclared packages / import errors
     - Hardcoded developer paths (`C:\Users\...`, `/home/...`) & IPs
     - Document-to-code drift
     - Secret leaks
   - Writes report to `.audit/reports/agent_03_report.md`.
2. **Launch `agent_04` (Remediation Engineer):**
   - Implements full, production-grade fixes as specified in `agent_03_report.md`.
   - Leaves `.audit/reports/` completely untouched.
   - Returns control to `agent_03`.
3. **Re-verification Loop:**
   - Agent 03 re-runs its audit in `.audit/.scratch/`. When all checks pass, Phase 2 is complete.

### Phase 3: Final Certification
1. Write the final certification report to `.audit/reports/final_report.md`.
2. Present the executive summary to the user and stage clean Git commits.
