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

## 2. Project-agnostic platform principle

Boomi Builder is a generic Boomi integration engineering platform.

It MUST NOT be designed specifically for the SAP ↔ ZTE integration or for any other individual integration project.

The SAP ↔ ZTE project is the first real-world validation and acceptance project for the platform. Its components, contracts, structures and business rules provide test evidence, but they do not define the generic application model.

A new integration project must be adoptable and analyzable without changing Boomi Builder source code merely because it has different:

- systems or applications;
- component names;
- component IDs;
- folders or branches;
- XML element names;
- profile structures;
- field names;
- mappings;
- process structures;
- connectors;
- endpoints;
- environments;
- business identifiers;
- business constants.

Generic application code MUST NOT depend on project-specific identifiers or semantics.

Examples of values that MUST NOT be hard-coded into generic analyzers, discovery services or application orchestration include:

- ZTE;
- SAP;
- `ZDVMBG_MR_REQUEST`;
- `ABLBELNR`;
- `ISTABLART`;
- `WA09`;
- `WA10`;
- project-specific Boomi component IDs;
- project-specific endpoint values;
- project-specific business constants.

Such values may legitimately exist as:

- discovered data;
- project metadata;
- evidence;
- approved Desired State;
- user decisions;
- project-specific validation criteria.

They MUST NOT exist as assumptions embedded in generic platform logic.

### 2.1 Platform Facts, Project Context and Evidence / Business Interpretation

Boomi Builder MUST keep three concerns separate.

#### Platform Facts

Platform Facts are facts authoritatively discovered from Boomi.

Examples include:

- component identity;
- component type;
- component version;
- folder;
- branch;
- current/deleted state;
- component definition;
- profile structure;
- element names;
- cardinalities;
- map source and target profiles;
- mapping definitions;
- process shapes;
- component references;
- dependency relationships;
- connector configuration structure;
- environment configuration where authoritatively available.

Platform Facts describe what exists in Boomi.

They do not by themselves establish what the business integration is intended to do.

#### Project Context

Project Context describes how discovered Boomi artifacts participate in a particular integration project.

Examples include:

- project;
- scenario;
- direction;
- source system;
- target system;
- project environment;
- adopted component role;
- project-specific requirement;
- project-specific contract.

The same generic Boomi component analysis model may therefore be used by multiple unrelated projects.

#### Evidence / Business Interpretation

Evidence / Business Interpretation describes conclusions about what discovered information means for a specific integration.

These conclusions MUST follow the Evidence Model and may be:

- CONFIRMED;
- SUPPORTING_CONTEXT;
- TO_CONFIRM.

A Platform Fact MUST NOT automatically become a business conclusion.

For example, discovering that a Map has the same component ID in `fromProfile` and `toProfile` proves that the current Boomi Map references the same profile on both sides.

It does not prove that this is the correct source-to-target contract for the integration.

### 2.2 Generic component analysis

Component analyzers MUST extract the structure actually present in a Boomi component.

They MUST NOT require known project field names, component names, business identifiers or expected project hierarchies.

For example, an XML Profile analyzer operates on generic `XMLElement` and `XMLAttribute` structures.

It does not require knowledge of:

- SAP IDoc segment names;
- ZTE payload fields;
- meter-reading identifiers;
- project-specific field semantics.

Likewise, a Map analyzer must analyze the mappings that actually exist in the Map rather than search for predefined project fields.

A Process analyzer must analyze the shapes and relationships actually present in the Process rather than assume a predefined orchestration pattern.

A Connector analyzer must analyze the connector representation actually present rather than assume a specific endpoint, authentication model or external system.

Specialized analyzers may exist for different Boomi component types or representation variants, but those analyzers MUST remain project-independent.

### 2.3 Data and structure agnosticism

Profile structures, field names, mappings and process layouts are project data.

They are not part of the generic Boomi Builder application schema.

For example, one project may contain:

Customer
→ Orders
→ Order
→ Items

while another project may contain:

IDOC
→ Segment
→ Device
→ Register

Both must be handled by the same generic profile-analysis capability when represented by the same supported Boomi profile format.

The application MUST discover and preserve the actual names and hierarchy rather than normalize them into a project-specific predefined model.

The same principle applies to:

- XML profiles;
- JSON profiles;
- flat-file profiles;
- maps;
- processes;
- connectors;
- operations;
- environments;
- other supported Boomi artifacts.

### 2.4 Unsupported structures

Boomi Builder is not required to understand every possible Boomi component representation from the first release.

When a component type, structure or representation is not supported, the application MUST:

- preserve the available evidence where safe and practical;
- identify the component and its known metadata;
- explicitly classify the analysis as unsupported or unresolved;
- avoid inventing missing semantics;
- avoid inferring behavior solely from names or superficial similarity.

Support for a previously unknown Boomi representation may require a new generic platform capability.

Adding a new integration project with different business data MUST NOT, by itself, require new application code.

### 2.5 Generic and project acceptance testing

Generic unit tests SHOULD use synthetic, project-neutral:

- component names;
- profile names;
- element names;
- field names;
- mappings;
- process structures;
- identifiers.

This helps prove that generic platform code does not depend on a particular project.

Real project components may additionally be used as acceptance and regression evidence to prove that the generic implementation works against real Boomi structures.

The SAP ↔ ZTE project is the first such real-world acceptance project.

Project-specific acceptance tests MUST NOT cause project-specific business logic to leak into the generic platform implementation.

### 2.6 Architectural acceptance criterion

A new integration project with different:

- profile structures;
- field names;
- maps;
- processes;
- connectors;
- endpoints;
- systems;
- business semantics;

must be able to follow the generic workflow:

CREATE PROJECT
→ CONNECT
→ DISCOVER
→ ANALYZE
→ ADOPT

without requiring changes to Boomi Builder source code solely because the business integration is different.

Source-code changes are justified when Boomi Builder encounters a previously unsupported Boomi platform capability, component type or representation.

They are not justified merely because a new project uses different business data.

---

## 3. Existing proven execution engine

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

## 4. High-level architecture

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
    +--> Component Analysis Services
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

Component Analysis Services are responsible for deterministic, project-independent interpretation of supported Boomi component representations.

Project-specific business interpretation is outside this generic analysis boundary.

---

## 5. Fundamental state model

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

Actual State records discovered values as data.

Project-specific component names, profile names, field names and structures are not application schema and MUST NOT be hard-coded into the generic domain model.

### Desired State

What should exist according to approved requirements, contracts, evidence and decisions.

Desired State MUST NOT silently contain unresolved assumptions.

Project-specific requirements and business semantics belong in Desired State and project evidence, not in generic Boomi component analyzers.

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

## 6. Existing integration support

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

An adopted component receives a stable project identity linked to its Boomi `componentId`.

Discovery MUST remain project-independent.

The discovery layer reports what Boomi contains and how supported components reference one another.

It MUST NOT assign project-specific business meaning to those relationships without Project Context and evidence.

---

## 7. Drift detection

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

## 8. Multi-user model

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

## 9. Boomi Connection

A Boomi Connection contains non-secret configuration such as:

- connection name;
- `BOOMI_ACCOUNT_ID`;
- `BOOMI_USERNAME`;
- status;
- last successful connection test;
- secret reference.

`BOOMI_API_TOKEN` is secret material.

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

The application stores only a `SecretReference`.

The actual secret is obtained by the backend only when required for an authorized Boomi operation.

---

## 10. Secret boundary

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

## 11. Authorization

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

## 12. AI boundary

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

AI interpretation MUST remain distinguishable from deterministic Boomi discovery and component analysis.

A generic analyzer reports observable component structure.

AI or project logic may interpret that structure only within the Evidence Model.

---

## 13. Evidence model

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

Evidence interpretation is project-specific.

Generic discovery and component-analysis services produce observations and Platform Facts.

They MUST NOT silently assign project-specific business meaning to those observations.

A discovered value may therefore be authoritative as Actual State while its business meaning remains TO_CONFIRM.

---

## 14. Boomi execution boundary

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

Read-only discovery and analysis SHOULD be separated where practical.

A component may be downloaded through the authorized Boomi execution boundary and then analyzed locally without repeatedly accessing Boomi or resolving credentials.

---

## 15. Write workflow

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

Generic write capabilities MUST operate on approved Desired State and deterministic plans.

They MUST NOT contain project-specific business assumptions embedded in execution code.

---

## 16. Audit

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

Where analysis contributes to a plan, the relevant discovered component version and evidence references should be identifiable so that the basis of the plan can be reconstructed.

---

## 17. Project storage

Boomi Builder has its own project storage.

Initial application projects live under:

projects\

The existing external ZTE workspace is not silently converted into mutable application storage.

It will later be imported/adopted through an explicit workflow.

Project storage contains Project Context and project-specific state.

Generic Boomi platform logic MUST NOT depend on a particular project's directory name, component IDs, profile names or field names.

Runtime data, secrets and downloaded discovery artifacts must remain separated from source-controlled application code and project definitions according to their security and lifecycle requirements.

---

## 18. Initial technology direction

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
