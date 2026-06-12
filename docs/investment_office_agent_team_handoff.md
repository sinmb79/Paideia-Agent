# Investment Office Agent Team Handoff

Updated: 2026-06-12

## Purpose

This handoff summarizes the local 22B Investment Office build-out and the follow-up requirements for the Paideia Agent development team. The key correction is that specialist credentials must be earned through Paideia growth cycles, not attached as static labels.

## Current Local Implementation

- Workspace repo: `%PAIDEIA_REPO%`
- Local storage root: `%AI22B_STORAGE_ROOT%`
- Investment office root: `%AI22B_STORAGE_ROOT%\investment-office\teams\22b-investment-office`
- Telegram bridge root: `%AI22B_STORAGE_ROOT%\telegram-bridge`
- Active Telegram bot: `<private-telegram-bot>`
- Active chat backend: `codex_oauth`
- Active model: `gpt-5.5`

The office has one CIO/team lead and eight specialist agents:

- Chief Investment Officer and Telegram team lead
- US market strategist
- Macro and rates analyst
- Geopolitics and policy analyst
- Commodities and FX analyst
- US equity research analyst
- Portfolio and risk manager
- Trading and execution planner
- Compliance and records officer

## Important Correction

The first education dossier pass only attached synthetic credentials to team members. That is insufficient for the Paideia model.

The corrected rule is:

```text
Graduation requires live runtime,
learning_decision = promoted,
and capstone score >= 88.

Fallback or quarantined learning cannot graduate.
```

Team membership now has an additional product rule:

```text
Every team member must be raised by the built-in Paideia development program.
Every team member must have a separate active employment_record.
Every team member must expose resume or hiring_dossier evidence.
Role labels alone cannot create team membership.
```

This rule is now recorded in:

- `investment-office\teams\22b-investment-office\development\DEVELOPMENT_REPORT.md`
- `investment-office\teams\22b-investment-office\development\development_program.capstone_002_remediation.json`
- `investment-office\teams\22b-investment-office\agent_roster.json`
- `investment-office\teams\22b-investment-office\22b_investment_office.team.json`

## Verified Growth Result

The remediation capstone was executed with `learn_from_chat=True`, `llm_mode=live`, `PAIDEIA_CHAT_BACKEND=codex_oauth`, and `gpt-5.5`.

Result:

- Members: 9
- Graduated: 9
- Failed: 0
- Remediation required: 0
- All members used `live_openai_responses`
- All members recorded `learning_decision=promoted`
- All roster and team entries now reference their growth program records

## Telegram Integration

The local bridge now supports:

- Normal message: chat with the CIO/team lead.
- `/team <objective>`: dispatch the objective to specialist agents, then ask the CIO/team lead to synthesize.
- `/status`: show active agent, backend, model, and team file.

The local bridge script was updated at:

- `%AI22B_STORAGE_ROOT%\telegram-bridge\paideia_telegram_bridge.py`
- `%AI22B_STORAGE_ROOT%\telegram-bridge\start_paideia_telegram_bridge.ps1`

The repo module was also updated at:

- `src/ai22b/talent_foundry/telegram_bridge.py`
- `tests/test_talent_foundry_telegram_bridge.py`

The PowerShell start script must avoid hard-coded non-ASCII bundle paths. It should read the leader employment record from the ASCII-path roster JSON instead. This prevents Windows PowerShell 5 encoding corruption of Korean path segments.

## Productization Requirements

### 1. First-class Investment Office Team Model

Add a first-class domain model for hired agent teams with:

- Team lead role
- Specialist roster
- Employment record paths
- Per-member onboarding session paths
- Per-member training run paths
- Per-member resume or hiring dossier evidence
- Growth program paths
- Education and capstone status
- Active graduation rule
- No-autonomous-trading policy

The team should not rely on ad hoc JSON mutation.

The supported creation path should be:

1. Build or choose the team objective.
2. For each specialist role, run Paideia's built-in onboarding/development program separately.
3. Produce that member's own `employment_record.json`, training run, learning ledger, memory substrate, and hiring dossier/resume.
4. Assemble the team only from members whose `development_evidence.passed` is true.
5. Block `/team` dispatch when any member is only a role label or lacks development evidence.

### 2. Growth-before-credential Pipeline

Credentials must be derived from training outcomes:

1. Assign role-specific curriculum or capstone.
2. Run the agent through a live or approved training cycle.
3. Record `chat_learning_update` or equivalent learning event.
4. Score the output against a role rubric.
5. Promote only when the strict graduation rule passes.
6. Write education and roster summaries from the verified result.

The development team should prevent manual credential attachment without a linked growth record.

### 3. Strict Graduation Gate

Implement a reusable graduation gate:

```text
runtime_status must be live/completed
learning_decision must be promoted
score must be >= threshold
fallback_used must be false
quarantined learning cannot graduate
```

The gate should emit clear failure reasons such as:

- `fallback_runtime_used`
- `learning_not_promoted`
- `score_below_threshold`
- `missing_growth_artifact`

### 4. Team Dispatch Command

The `/team` command should be promoted from local bridge logic into a supported Paideia feature.

Expected behavior:

1. Parse objective.
2. Dispatch specialist prompts by role.
3. Store every specialist report.
4. Ask the team lead to synthesize.
5. Return CIO-facing answer to Telegram.
6. Store the full directive artifact.

The command must remain approval-gated for investment actions.

### 5. Investment Safety Policy

The investment team must be positioned as research and portfolio support only.

Forbidden actions:

- Autonomous trading
- Order transmission
- Brokerage credential requests
- Guaranteed return claims
- Presenting unverified live market data as confirmed

Every recommendation should separate:

- Verified facts
- Assumptions
- Missing data
- Risk and invalidation
- Proposal
- Boss approval requirement

### 6. Runtime Reliability

During capstone 001, some calls fell back from `openai-codex` to deterministic local mode due connection errors. The remediation pass succeeded, but the product should implement:

- Retry/backoff for Codex OAuth calls
- Clear runtime-mode reporting
- Failure-safe graduation gate
- Optional queueing for long team cycles
- Telegram progress messages for long-running team dispatches

### 7. Tests Needed

Add tests for:

- `/team` dispatch calls specialist members before lead synthesis
- Team file loads from env and CLI args
- Non-ASCII employment paths survive PowerShell startup through roster lookup
- Graduation gate rejects fallback responses
- Graduation gate rejects quarantined learning
- Roster and team JSON are updated only from verified growth artifacts
- Investment safety policy is included in team prompts

## Current Verification

Latest local verification:

- Telegram bridge running with CIO team lead.
- Telegram ready notification sent successfully.
- `/team` plumbing smoke passed.
- CIO live chat smoke passed.
- `tests/test_talent_foundry_telegram_bridge.py` passed.
- Development report shows 9/9 graduated under the strict capstone rule.

## Next Development Milestone

Build a formal `InvestmentOffice` or generic `HiredAgentTeamOffice` module that owns:

- Team creation
- Role academy/capstone execution
- Graduation gate
- Telegram team dispatch
- Roster and education report generation
- Safety policy enforcement

The current local implementation proves the workflow, but it should be moved out of ad hoc scripts into maintainable package APIs and CLI commands.
