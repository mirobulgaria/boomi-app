# Boomi Builder — MVP Plan

## Product objective

Build a multi-user, AI-assisted Boomi integration lifecycle application without modifying the proven standalone boomi-cli.

The first real project will be SAP ↔ ZTE.

The first real project mode will primarily exercise:

ADOPT + CONTINUE

rather than NEW.

---

## Current execution roadmap

This section is the authoritative sequencing for near-term work.
Before additional writable shape expansion, the existing deterministic creation pipeline must pass Boomi capability compliance remediation against current official Boomi documentation and authoritative serialization evidence.

Compliance remediation order:

1. Start
2. Map
3. Connector Action
4. Return Documents
5. Process Call
6. Stop
7. Branch
8. Try/Catch
9. Decision

Subsequent capability expansion:

1. Message
2. Data Process
3. Set Properties
4. Exception
5. Notify
6. SAP JCo
7. Web Services SOAP Client
8. Web Services Server
9. Database

The authoritative capability registry is:

`docs/BOOMI_CAPABILITY_COMPLIANCE.md`

The numbered Phase sections below remain capability specifications. Where their historical order conflicts with this roadmap, **this roadmap wins**.

### 1. Deterministic Boomi understanding (current)

- SensitiveValueRedactor
- analyze-process
- Connector Settings / Operation analyzers
- Unified Component Analysis Service
- Environment / Environment Extensions

Goal: close the generic vertical slice

Boomi definition → Discovery → Analyzers → Platform Facts

Component analysis status: working v1; representation coverage still expanding.

### 2. CHECKPOINT — engineering / productization

After the understanding slice above:

- Root `README.md` (points to detailed docs)
- CI: Windows + Python 3.13 + pytest
- Read-only FastAPI surface: connections / discovery / analysis

Do not add ruff/mypy as a CI gate until the project has an agreed configuration.

Do not design the final SQLite schema before Project + ADOPT + Evidence contracts stabilize.

### 3. Project domain and persistence

- Project domain model
- ADOPT
- Evidence / blocker model
- Persistence migration to SQLite

### 4. Multi-user product surface

- Application identity / authentication
- React + TypeScript shell
- Connections UI
- Discover / Analyze / Adopt UI

### 5. Controlled change lifecycle

- Desired State
- Diff
- Plan
- Preview
- Approval
- Apply
- Verify
- Audit / Sync

Write primitives may exist in the embedded engine. The application-level controlled write policy / authorization / approval layer is what must be built here. Capability in the engine ≠ permitted application write path.

### 6. AI assistant

AI may assist on safe structured context only:

Platform Facts + Project Context + Evidence
→ AI proposals / explanations / questions

**Never:** AI → Boomi

Place AI after Evidence / Project model is real, and before (or alongside) Plan as an assistant — not as an authority over Boomi writes.

---

## Analyzer expansion cut-off

After **Unified Analysis + Environment / Environment Extensions**, stop expanding the analyzer layer unless a concrete real adoption case shows a missing **generic Boomi capability**.

Rules:

- Different fields / names / business structures in a future project → **do not** write a new analyzer; use existing generic Platform Facts + project evidence.
- A new Boomi representation the platform does not yet understand → **then** extend a generic capability.

This cut-off protects against building an excellent analyzer library with no shippable product, and stays aligned with `ARCHITECTURE.md` (platform is project-agnostic; SAP ↔ ZTE is validation, not schema).

---

## Phase 0 — Baseline

Status: COMPLETE

Completed:

- standalone boomi-cli separated from project workspace;
- standalone CLI proven against v6-controlled-restore-proven;
- Boomi Builder directory created;
- embedded CLI copied byte-for-byte;
- engine baseline documented;
- baseline SHA-256 manifest created.

---

## Phase 1 — Application foundation

Goal:

Create a runnable local application with no Boomi writes.

Deliverables:

- Python backend skeleton;
- FastAPI application;
- React + TypeScript frontend skeleton;
- SQLite database bootstrap;
- health endpoint;
- application configuration;
- structured logging;
- initial test framework.

No AI.
No Boomi write.
No project import yet.

---

## Phase 2 — Users and Boomi Connections

Goal:

Support multiple application users and user-owned Boomi connections.

Deliverables:

- User model;
- application login foundation;
- BoomiConnection model;
- Add Boomi Connection UI;
- fields:
  - connection name
  - BOOMI_ACCOUNT_ID
  - BOOMI_USERNAME
  - BOOMI_API_TOKEN
- protected token storage;
- Test Connection;
- token never returned to frontend after storage;
- audit events for connection operations.

No AI access to secrets.

---

## Phase 3 — Embedded CLI read-only adapter

Goal:

Backend can invoke the embedded CLI safely.

Deliverables:

- BoomiEngineAdapter;
- explicit workspace handling;
- runtime credential injection;
- stdout/stderr capture;
- timeout handling;
- reusable sensitive-value redaction at presentation / logging / AI boundaries;
- structured result parsing;
- read-only operations:
  - get
  - search
  - inspect
  - export where required

Standalone CLI remains untouched.

---

## Phase 4 — Project foundation

Goal:

Create and manage projects.

Deliverables:

- Project;
- ProjectMember;
- ProjectEnvironment;
- permissions;
- project dashboard;
- project environment configuration;
- user selects an authorized BoomiConnection for operations.

---

## Phase 5 — Boomi discovery

Goal:

Discover an existing integration without modifying it.

Deliverables:

- Sync from Boomi;
- folder/component inventory;
- normalized BoomiComponent records;
- current/deleted state;
- version tracking;
- branch tracking;
- component definition hashes;
- dependency/reference discovery;
- dependency graph;
- refresh operation.

First target:

SAP ↔ ZTE existing TEST implementation.

Current implementation status:

- read-only component metadata retrieval: implemented;
- component definition download: implemented;
- recursive dependency discovery: implemented v1;
- XML Profile analysis: implemented v1;
- Transform Map analysis: implemented v1;
- Process analysis: implemented v1;
- Connector Settings / Operation analysis: pending;
- Environment / Environment Extensions analysis: pending.

---

## Phase 6 — Adopt / Continue

Goal:

Allow existing Boomi components to become managed project components.

Deliverables:

- discovered component view;
- Inspect;
- Adopt;
- Ignore;
- ManagedComponent;
- project component inventory;
- stable componentId association;
- initial drift detection.

---

## Phase 7 — Artifacts and evidence

Goal:

Import integration documentation and maintain evidence.

Deliverables:

- artifact upload;
- SHA-256;
- artifact classification;
- Evidence registry;
- Open Questions;
- Decisions;
- CONFIRMED / SUPPORTING_CONTEXT / TO_CONFIRM;
- blocker representation.

First project:

existing SAP ↔ ZTE documentation.

---

## Phase 8 — AI Chat

Goal:

Add project-aware ChatGPT assistance.

AI context may include, when available:

- project metadata;
- artifacts where authorized;
- evidence;
- open questions;
- decisions;
- sanitized Actual State;
- dependency graph;
- approved or proposed Desired State;
- Diff;
- plans.

AI context MUST NOT include:

- BOOMI_API_TOKEN;
- passwords;
- secret values;
- unrestricted local filesystem;
- unrestricted shell access.

Initial chat use cases:

- explain existing integration;
- identify missing information;
- compare evidence;
- identify blockers;
- propose Desired State;
- propose change plan.

---

## Phase 9 — Desired State and Diff

Goal:

Represent what should exist and compare it with Boomi.

Deliverables:

- DesiredComponent;
- evidence gating;
- normalized comparison;
- ComponentDiff;
- MATCH / MISSING / DIFFERENT / BLOCKED / DRIFTED;
- UI diff viewer.

---

## Phase 10 — Plan and Preview

Goal:

Generate deterministic plans before any write.

Deliverables:

- BuildPlan;
- BuildPlanStep;
- dependency ordering;
- preconditions;
- refresh-before-preview;
- drift detection;
- embedded CLI preview;
- aggregated preview result;
- human approval.

---

## Phase 11 — Controlled Apply

Goal:

Allow approved plans to modify Boomi.

Requirements:

- user authorization;
- user's own BoomiConnection;
- write policy;
- backups/snapshots;
- explicit approval;
- deterministic embedded CLI;
- authoritative verification;
- audit;
- no unsafe automatic retry.

Initial write scope should be deliberately limited.

---

## Phase 12 — Change and Recovery

Goal:

Safely manage existing integrations over time.

Deliverables:

- change impact analysis;
- controlled update;
- controlled delete;
- controlled restore;
- reconciliation;
- partial failure handling;
- recovery workflows.

---

## Boomi capability compliance checkpoint

Before broadening Controlled Apply, each writable capability must have:

- an explicit capability status;
- reviewed current official Boomi documentation;
- sufficient authoritative serialization evidence;
- a deterministic desired-state contract;
- Validate support;
- Build support;
- Verify support;
- positive regression coverage;
- meaningful negative regression coverage;
- controlled live evidence where required.

Known remediation includes:

### Branch

The Builder must enforce `numBranches` as an integer in the documented range 2 through 25.

Values outside that range and non-integer values must be rejected before Build.

### Try/Catch

The Builder must enforce Retry Count in the documented range 0 through 5.

The Builder must not infer unproven failure-trigger serialization from a single observed `catcherrors` instance.

### Decision

The current proven `process + static` Decision contract remains `PARTIALLY SUPPORTED`.

Exactly two operands are part of the supported Decision semantics currently being implemented, but additional parameter-value serialization variants require authoritative evidence before Builder support is expanded.

### Expansion rule

`Message`, `Data Process`, `Set Properties`, `Exception`, `Notify` and connector-specific creation support must follow the same documentation-plus-serialization capability lifecycle.

The MVP must prefer:

`BUILD BLOCKED`

over generation of plausible but insufficiently evidenced Boomi XML.

The objective is deterministic creation of Boomi components that Boomi accepts and interprets correctly.

---
## MVP safety principles

1. Read before write.
2. Refresh before apply.
3. Never silently overwrite drift.
4. AI proposes; deterministic engine applies.
5. Unknown evidence remains unknown.
6. Secrets never enter AI context.
7. Every write is attributable to an application user and Boomi identity.
8. Every write has authoritative post-operation verification.
9. Ambiguous destructive results are never automatically retried.
10. Standalone boomi-cli remains independent.
11. Project-specific names, fields and business structures never define generic platform logic.
12. Official Boomi documentation defines capability semantics and constraints; authoritative Boomi component definitions prove serialization.
13. Unsupported or insufficiently evidenced writable variants are blocked before Build or Boomi API write.
14. A single observed component never establishes the complete generic Boomi capability.
15. A passing regression test proves the declared tested contract; it does not expand that contract to untested Boomi variants.
16. Build refusal is a valid and required safety outcome when the requested capability cannot be represented deterministically.