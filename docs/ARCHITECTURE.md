# Boomi Builder — Architecture v1

## 1. Purpose

Boomi Builder is a multi-user, AI-assisted application for managing the lifecycle of Boomi integrations.

It must support:

- NEW — build a new integration from requirements and contracts;
- ADOPT — discover and adopt an existing Boomi integration;
- CONTINUE — determine what already exists and continue an incomplete implementation;
- CHANGE — compare desired state with actual Boomi state and safely modify an existing integration;
- RECOVER — support controlled lifecycle and reconciliation operations.

The primary workflow is:

DISCOVER
→ EVIDENCE
→ DESIRED STATE
→ DIFF
→ PLAN
→ PREVIEW
→ APPROVE
→ APPLY
→ VERIFY
→ SYNC

AI must not write directly to Boomi.

All Boomi changes must pass through deterministic application policy and the embedded Boomi execution engine.

---

## 2. Existing proven execution engine

Embedded engine:

engine\boomi-cli\

Baseline:

v6-controlled-restore-proven

The embedded engine was imported byte-for-byte from the proven standalone CLI.

The standalone CLI remains independent and MUST NOT be modified automatically by Boomi Builder development.

Baseline provenance is recorded in:

engine\BASELINE.md
engine\BASELINE_SHA256SUMS.txt

---

## 3. High-level architecture

Browser UI
    |
    v
Frontend
React + TypeScript
    |
    v
Backend API
Python + FastAPI
    |
    +--> Authentication / Authorization
    |
    +--> Project Service
    |
    +--> Artifact Service
    |
    +--> Evidence Service
    |
    +--> AI Orchestrator
    |
    +--> Boomi Discovery Service
    |
    +--> Desired State Service
    |
    +--> Diff Engine
    |
    +--> Plan Engine
    |
    +--> Policy / Approval Engine
    |
    +--> Execution Service
    |
    +--> Audit Service
    |
    +--> Secret Store Adapter
    |
    +--> Boomi Engine Adapter
              |
              v
       embedded boomi-cli
              |
              v
          Boomi Platform

---

## 4. Fundamental state model

Boomi Builder maintains two independent states.

### Actual State

Authoritative state discovered from Boomi.

Examples:

- component identity;
- type;
- version;
- current/deleted state;
- folder;
- branch;
- definition;
- references;
- dependency relationships.

Actual State MUST NOT be inferred from project documentation.

### Desired State

What should exist according to approved requirements, contracts, evidence and decisions.

Desired State MUST NOT silently contain unresolved assumptions.

### Diff

Diff compares:

Desired State
vs
Actual State

Possible classifications include:

- MATCH;
- MISSING;
- EXTRA;
- DIFFERENT;
- INCOMPLETE;
- UNKNOWN;
- BLOCKED;
- DRIFTED.

---

## 5. Existing integration support

The application must not assume an empty Boomi account.

It must support read-only discovery of existing integrations.

Discovery includes, where supported:

- folders;
- branches;
- components;
- current versions;
- deleted state;
- component definitions;
- component references;
- dependency graph;
- Where Used relationships.

Existing components may be ADOPTED into a project.

Adoption does not perform a Boomi write.

An adopted component receives a stable project identity linked to its Boomi componentId.

---

## 6. Drift detection

Before any write plan is applied, Boomi Builder MUST refresh the affected Actual State.

Example:

Project known version: 7
Boomi current version: 8

Result:

DRIFT DETECTED

The write operation must be blocked until the drift is explicitly resolved.

Possible resolution workflows:

- inspect external change;
- accept current Boomi state;
- update Desired State;
- generate a new plan.

No silent overwrite is allowed.

---

## 7. Multi-user model

Boomi Builder is a multi-user application.

Application identity and Boomi identity are separate concepts.

### Application identity

Identifies the logged-in Boomi Builder user.

### Boomi identity

Identifies the credentials used when interacting with a Boomi account.

Each user may own multiple Boomi Connections.

Example:

User
  |
  +-- Electrohold TEST
  |
  +-- Electrohold PROD
  |
  +-- Customer XYZ

A project does not own a user's API token.

---

## 8. Boomi Connection

A Boomi Connection contains non-secret configuration such as:

- connection name;
- BOOMI_ACCOUNT_ID;
- BOOMI_USERNAME;
- status;
- last successful connection test;
- secret reference.

BOOMI_API_TOKEN is secret material.

The token MUST NOT be stored as plaintext in:

- application database;
- project JSON;
- project artifacts;
- logs;
- execution records;
- frontend localStorage;
- AI context;
- prompts;
- source control.

The application stores only a SecretReference.

The actual secret is obtained by the backend only when required for an authorized Boomi operation.

---

## 9. Secret boundary

AI has no access to secret values.

Frontend must not receive an already stored API token back from the backend.

The secret flow is:

User
  |
  v
Frontend secret input
  |
  v
Backend
  |
  v
Secret Store
  |
  v
runtime credential material
  |
  v
Boomi Engine Adapter

The AI Orchestrator is outside this path.

For an initial Windows-hosted implementation, a protected local secret mechanism may be used.

The Secret Store interface MUST remain replaceable so that a centralized deployment can later use an approved enterprise vault.

---

## 10. Authorization

A user must be authorized for:

- project access;
- project administration;
- Boomi connection usage;
- preview operations;
- write operations;
- lifecycle operations;
- production operations.

Production writes should support stricter approval policy than TEST writes.

AI-generated plans do not imply authorization.

---

## 11. AI boundary

AI responsibilities may include:

- document analysis;
- requirements extraction;
- evidence classification;
- identifying contradictions;
- identifying missing information;
- generating questions;
- architecture proposals;
- mapping proposals based on real contracts;
- Desired State proposals;
- change impact analysis;
- Build Plan proposals;
- explanations of Actual State and Diff.

AI MUST NOT:

- receive Boomi API tokens;
- receive passwords or other secrets;
- execute unrestricted shell commands;
- call Boomi directly;
- silently convert assumptions into confirmed facts;
- bypass application authorization;
- bypass write policy;
- bypass approval;
- bypass deterministic verification.

---

## 12. Evidence model

Important conclusions must be evidence-aware.

Minimum evidence statuses:

CONFIRMED
SUPPORTING_CONTEXT
TO_CONFIRM

Evidence may reference:

- XML;
- XSD;
- WSDL;
- documents;
- transcripts;
- screenshots;
- configuration exports;
- verified Boomi state;
- user decisions.

Unknown information remains explicit.

An unresolved required field can block Desired State approval or Build Plan execution.

---

## 13. Boomi execution boundary

Only the Boomi Engine Adapter may invoke the embedded engine.

Frontend does not invoke PowerShell.

AI does not invoke PowerShell.

The adapter is responsible for:

- process invocation;
- workspace selection;
- credential injection;
- timeout handling;
- stdout/stderr capture;
- exit-state interpretation;
- output sanitization;
- structured result conversion;
- audit correlation.

Secrets must not be passed as visible command-line arguments if a safer runtime mechanism is available.

---

## 14. Write workflow

Every write follows:

REFRESH ACTUAL STATE
→ DRIFT CHECK
→ POLICY CHECK
→ BACKUP / SNAPSHOT
→ PREVIEW
→ APPROVAL
→ APPLY
→ AUTHORITATIVE VERIFY
→ AUDIT
→ SYNC

No automatic retry is allowed after an ambiguous destructive or lifecycle response.

---

## 15. Audit

Every meaningful operation must be auditable.

An execution record should identify:

- application user;
- project;
- project environment;
- Boomi connection;
- Boomi username;
- operation;
- component identity;
- before version;
- after version;
- plan;
- timestamps;
- result;
- verification status.

Secrets are never recorded.

---

## 16. Project storage

Boomi Builder has its own project storage.

Initial application projects live under:

projects\

The existing external ZTE workspace is not silently converted into mutable application storage.

It will later be imported/adopted through an explicit workflow.

---

## 17. Initial technology direction

Frontend:
React + TypeScript

Backend:
Python + FastAPI

Database:
SQLite for the initial implementation

Boomi execution:
embedded PowerShell boomi-cli

AI:
backend-mediated OpenAI integration

Project artifacts:
filesystem with database metadata

Secret storage:
adapter-based protected secret store

These choices may be revisited through an explicit architecture decision.