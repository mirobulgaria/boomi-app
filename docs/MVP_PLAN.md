# Boomi Builder — MVP Plan

## Product objective

Build a multi-user, AI-assisted Boomi integration lifecycle application without modifying the proven standalone boomi-cli.

The first real project will be SAP ↔ ZTE.

The first real project mode will primarily exercise:

ADOPT + CONTINUE

rather than NEW.

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
- secret redaction;
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

AI context may include:

- project metadata;
- artifacts where authorized;
- evidence;
- open questions;
- decisions;
- sanitized Actual State;
- dependency graph;
- Desired State;
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