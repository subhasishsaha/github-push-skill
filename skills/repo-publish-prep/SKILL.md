---
name: repo-publish-prep
description: Orchestrator protocol for multi-agent adversarial codebase preparation. The coordinator spawns and manages subagents (Agent 01 Explorer, Agent 02 Documenter, Agent 03 Adversarial Auditor, Agent 04 Remediation Engineer). Subagents write their own dynamic audit scripts in '.audit/.scratch/' and strictly adhere to behavioral isolation contracts stored in '.audit/.agents/'.
license: Apache-2.0
metadata:
  version: v4
  architecture: orchestrator-subagent-behavioral-isolation
  compatibility: universal-agent-agnostic
---

# Repository Publish & Hosting Preparation (`repo-publish-prep`)

An orchestrator-driven multi-agent verification protocol that guarantees **truth in code and documentation** before publishing or pushing to GitHub, GitLab, Bitbucket, or remote Git hosting.

The primary coordinator acts as the **Orchestrator**. It does not perform audits directly; it defines, spawns, and coordinates specialized **subagents** (`agent_01`, `agent_02`, `agent_03`, `agent_04`).

---

## 🛡️ Behavioral Isolation & File Boundary Contracts (`.audit/.agents/`)

To prevent subagents from overstepping their scope—such as **Agent 04 editing Agent 03's audit report** instead of fixing the application code—the Orchestrator enforces strict behavioral contracts stored in:
```text
.audit/.agents/
├── agent_01.md    # Explorer contract (write only .audit/recon/ & .audit/.scratch/)
├── agent_02.md    # Documenter contract (write only README.md)
├── agent_03.md    # Auditor contract (write only .audit/.scratch/ & .audit/verification/agent_03/report.md)
└── agent_04.md    # Remediation contract (write ONLY application code; NEVER touch report.md)
```

The Orchestrator injects the exact behavioral contract from `.audit/.agents/agent_XX.md` into each subagent's system prompt and task instructions.

---

## 🏗️ Orchestration Flowchart

```mermaid
flowchart TD
    Start["🚀 Orchestrator Starts"] --> InitAgents["Initialize .audit/.agents/ contracts"]
    InitAgents --> CheckReadme{"Does README.md exist?"}
    
    %% Phase 1
    CheckReadme -->|Yes| VerifyWithUser["Prompt User: Does README match intended application behavior?"]
    VerifyWithUser -->|User: Drifted / Wrong| HaltUser["🛑 Halt Execution Immediately & Ask User for Clarification"]
    VerifyWithUser -->|User: Verified OK| Phase2["Proceed to Phase 2"]
    
    CheckReadme -->|No| LaunchA1["Orchestrator injects .audit/.agents/agent_01.md\nSpawns Agent 01 (Explorer)"]
    LaunchA1 --> A1Work["Agent 01 inspects code, creates scratch scripts in .audit/.scratch/\nWrites .audit/recon/agent_01_report.md\n(STRICT: Never writes README.md)"]
    A1Work --> LaunchA2["Orchestrator injects .audit/.agents/agent_02.md\nSpawns Agent 02 (Verifier)"]
    LaunchA2 --> A2Verify{"Agent 02 verifies code on disk.\nDoes Agent 01 report match truth?"}
    A2Verify -->|Fails / Discrepancy| A1Retry["Reject report with diff.\nAgent 01 discards & re-runs"]
    A1Retry --> A1Work
    A2Verify -->|Passes| A2Draft["Agent 02 writes README.md"]
    A2Draft --> VerifyNewReadme["Prompt User: Verify newly generated README.md"]
    VerifyNewReadme --> Phase2

    %% Phase 2
    Phase2 --> LaunchA3["Orchestrator injects .audit/.agents/agent_03.md\nSpawns Agent 03 (Adversarial Auditor)"]
    LaunchA3 --> A3Work["Agent 03 creates on-demand audit scripts in .audit/.scratch/:\n- AST stubs & eagerness bias\n- Import errors & undeclared packages\n- Hardcoded developer paths & IPs\n- Markdown link & doc drift\nWrites findings to .audit/verification/agent_03/report.md\n(STRICT: Makes NO application code edits)"]
    A3Work --> CheckIssues{"Are there blockers / issues?"}
    CheckIssues -->|No Issues| Phase3["Proceed to Phase 3"]
    CheckIssues -->|Issues Found| LaunchA4["Orchestrator injects .audit/.agents/agent_04.md\nSpawns Agent 04 (Remediation Engineer)"]
    LaunchA4 --> A4Work["Agent 04 implements full, un-stubbed fixes in code\n(STRICT: NEVER touches .audit/verification/agent_03/report.md)"]
    A4Work --> A3Recheck["Orchestrator returns control to Agent 03\nRe-runs dynamic audit in .audit/.scratch/"]
    A3Recheck --> CheckIssues

    %% Phase 3
    Phase3 --> FinalReport["Orchestrator generates Final Certification at:\n.agents/final_report/report.md"]
    FinalReport --> PresentUser["Present Certification & Executive Summary to User"]
```

---

## 🛠️ Dynamic Scripting Workspace: `.audit/.scratch/`

Instead of brittle static scripts, subagents write purpose-built scripts directly in `.audit/.scratch/`:
- **`agent_01`** writes dynamic AST inspection or entrypoint discovery scripts in `.audit/.scratch/` to explore unknown repos.
- **`agent_03`** writes specialized Python, Node, or Shell scripts in `.audit/.scratch/` to test:
  1. Stubs, empty functions (`pass`, `...`), and `raise NotImplementedError`.
  2. Imports vs manifests (`package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`).
  3. Absolute paths (`C:\Users\...`, `/home/...`) and internal private IPs.
  4. Broken relative Markdown links and documented entrypoints.
- `.audit/` (including `.audit/.scratch/` and `.audit/.agents/`) is ignored in `.gitignore` so temporary audit scripts never dirty the repository.

---

## 🤖 The 4 Subagent Behavioral Boundaries

The Orchestrator must define and spawn each subagent with its explicit contract from `.audit/.agents/`:

### 1. `agent_01` — Codebase Archeologist / Explorer
- **Contract File:** `.audit/.agents/agent_01.md`
- **Permitted Writes:** `.audit/.scratch/*`, `.audit/recon/agent_01_report.md`.
- **FORBIDDEN:** Creating or editing `README.md`, editing application source code, editing `.audit/verification/`.

### 2. `agent_02` — Independent Verifier & Technical Writer
- **Contract File:** `.audit/.agents/agent_02.md`
- **Permitted Writes:** `README.md` at repository root.
- **FORBIDDEN:** Modifying `.audit/recon/agent_01_report.md`, editing application code, inventing ungrounded features.

### 3. `agent_03` — Adversarial Codebase Auditor
- **Contract File:** `.audit/.agents/agent_03.md`
- **Permitted Writes:** `.audit/.scratch/*`, `.audit/verification/agent_03/report.md`.
- **FORBIDDEN:** Modifying application source code files, editing `README.md`, editing package manifests. Sole maintainer of the audit report.

### 4. `agent_04` — Remediation Engineer
- **Contract File:** `.audit/.agents/agent_04.md`
- **Permitted Writes:** Application source code files, package manifests (`package.json`, `requirements.txt`), repository hygiene files (`.gitignore`, `.editorconfig`, `.env.example`, `CONTRIBUTING.md`, `SECURITY.md`).
- **CRITICAL RESTRICTION:** **MUST NEVER TOUCH, EDIT, OR MODIFY `.audit/verification/agent_03/report.md` OR ANY FILE IN `.audit/verification/`!**
  - The audit report belongs exclusively to Agent 03.
  - Agent 04 must NEVER edit the report to check off boxes or delete findings.
  - Agent 04 fixes the issues in actual source code. Agent 03 independently re-audits the code and updates the report itself.
  - Zero stubs: No `pass`, no ellipsis, no placeholder comments, no mock bypasses.

---

## 🔄 Orchestrator Execution Protocol

### Step 0: Behavioral Setup
Ensure `.audit/.agents/` exists and contains the 4 behavioral contracts (bootstrapped from `templates/agents/` if needed).

### Phase 1: README Verification Gate
1. Check if `README.md` exists.
2. If `README.md` exists:
   - Ask the user: *"Does this README accurately represent what the application is intended to do, or has it drifted?"*
   - If user signals drift: **Halt execution immediately.** Ask for clarification before proceeding.
   - If user confirms: Proceed to Phase 2.
3. If `README.md` is missing:
   - Orchestrator injects `.audit/.agents/agent_01.md` and spawns `agent_01`. Agent 01 writes `.audit/recon/agent_01_report.md`.
   - Orchestrator injects `.audit/.agents/agent_02.md` and spawns `agent_02`. Agent 02 verifies. If failed, loops back to Agent 01 (Max 3 iterations). Once passed, Agent 02 drafts `README.md`.
   - Present newly drafted `README.md` to user for explicit confirmation.

### Phase 2: Implementation Integrity Loop
1. Orchestrator ensures directory `.audit/.scratch/` exists.
2. Orchestrator injects `.audit/.agents/agent_03.md` and invokes `agent_03`.
3. `agent_03` writes its inspection scripts into `.audit/.scratch/`, runs them, and outputs `.audit/verification/agent_03/report.md`.
4. Orchestrator reads `.audit/verification/agent_03/report.md`.
5. If blockers or warnings exist:
   - Orchestrator injects `.audit/.agents/agent_04.md` and invokes `agent_04` with the action items.
   - `agent_04` implements real code fixes. Agent 04 strictly leaves `report.md` untouched.
   - Orchestrator hands control back to `agent_03` to re-execute its scratch audit.
   - Loop repeats until 0 blockers remain (Circuit breaker: Max 3 iterations, then escalate to user).

### Phase 3: Final Certification & Ledger
1. When Agent 03 confirms 0 blockers remain, Orchestrator compiles and writes:
   ```text
   .agents/final_report/report.md
   ```
   Adhering to [templates/audit/final_report.template.md](./templates/audit/final_report.template.md).
2. Orchestrator verifies `git status`.
3. Orchestrator presents the final certification summary to the user.
