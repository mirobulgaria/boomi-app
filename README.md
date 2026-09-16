# Boomi Builder

Boomi Builder is a project-agnostic, multi-user, AI-assisted application for managing the lifecycle of Boomi integrations.

The platform is being built around a deterministic and controlled lifecycle:

CONNECT → DISCOVER → ANALYZE → ADOPT → DESIRED STATE → DIFF → PLAN → PREVIEW → APPROVAL → APPLY → VERIFY → AUDIT / SYNC

The first real-world validation project is **SAP ↔ ZTE (AMI/AMR)**. That project validates the platform, but its component names, IDs, profiles, fields, mappings and business rules do not define the generic Boomi Builder application model.

## Current status

Boomi Builder is under active development.

The deterministic read-only foundation for understanding existing Boomi integrations is implemented. The planned analyzer expansion phase has reached its current MVP cut-off.

Development is now moving into productization:

1. repository documentation;
2. continuous integration;
3. read-only FastAPI application surface;
4. Project domain;
5. ADOPT;
6. Evidence and blocker management;
7. persistence;
8. multi-user product surface;
9. controlled change lifecycle;
10. AI assistance over safe structured context.

Authoritative project documentation:

- [Architecture](docs/ARCHITECTURE.md)
- [MVP plan](docs/MVP_PLAN.md)
- [Domain model](docs/DOMAIN_MODEL.md)
- [Development guide](docs/DEVELOPMENT.md)

## Implemented capabilities

### Application foundation

The backend currently includes:

- Python application package;
- FastAPI application foundation;
- health endpoint;
- application path and configuration handling;
- PowerShell process runner;
- automated test suite.

The React + TypeScript product UI is planned but is not yet implemented.

### Boomi connection foundation

Implemented connection capabilities include:

- `BoomiConnection` domain model;
- connection repository;
- connection enrollment;
- connection lifecycle service;
- runtime credential resolution;
- Windows DPAPI-backed secret storage;
- in-memory secret store for tests;
- separation of connection metadata from secret material.

Secret values are not intended to cross presentation, logging or AI boundaries.

### Embedded Boomi engine

Boomi Builder contains an embedded Boomi CLI under:

`engine/boomi-cli/`

Its imported provenance baseline is:

`v6-controlled-restore-proven`

The embedded engine was originally imported byte-for-byte from the proven standalone CLI. From that point forward, the standalone CLI and the Boomi Builder embedded engine are independent codebases.

Changes made under `boomi-builder/engine/` do not automatically modify the standalone CLI.

Baseline provenance is documented in:

- [Embedded engine baseline](engine/BASELINE.md)
- `engine/BASELINE_SHA256SUMS.txt`

### Application read-only safety

The embedded engine supports an explicit `app-readonly` runtime mode.

Only explicitly approved read operations are permitted through this mode.

Current approved operations are:

- `get`
- `get-definition`
- `list-environments`
- `get-environment-extensions`

Other CLI operations remain blocked by the application read-only safety boundary.

Application-level write authorization, approval and controlled execution are not implemented yet.

### Boomi discovery

Implemented read-only discovery capabilities include:

- component metadata retrieval;
- component definition retrieval;
- recursive dependency discovery;
- local discovery artifact storage;
- component dependency/reference discovery.

Discovery is generic and must not depend on project-specific component names or business identifiers.

### Deterministic component analysis

Generic deterministic analyzers currently exist for:

- XML Profiles;
- Transform Maps;
- Processes;
- Connector Settings;
- Connector Operations;
- Environment Extensions.

A unified Component Analysis Service dispatches supported Boomi component representations to the appropriate component analyzer.

Analyzer logic is based on Boomi representation structure, not project-specific business fields.

### XML Profile analysis

The XML Profile analyzer can derive structural facts including:

- logical element hierarchy;
- XML attributes;
- root paths;
- occurrence constraints;
- repeating elements;
- element keys;
- maximum lengths where represented.

It does not depend on SAP, ZTE or other project-specific field names.

### Transform Map analysis

The Transform Map analyzer can derive structural facts including:

- source profile reference;
- target profile reference;
- mappings;
- resolved profile paths;
- identity mappings;
- map sections;
- execution-order metadata.

It does not infer business mappings from similar field names.

### Process analysis

The Process analyzer can derive structural facts including:

- process settings;
- shapes;
- shape types;
- configuration trees;
- transitions;
- execution graph;
- component references.

Sensitive-value handling is kept separate from structural process analysis.

### Connector analysis

The Connector component analyzer supports structural interpretation of observed Connector Settings and Connector Operation representations.

It preserves generic configuration structure and component references without introducing project-specific connector semantics.

### Environment inventory

Boomi Builder supports typed read-only Environment inventory through the application adapter.

Environment inventory provides structured facts including:

- Environment ID;
- name;
- classification.

The inventory is retrieved through the embedded CLI using a machine-readable application contract.

### Environment Extensions

Boomi Builder supports read-only Environment Extensions transport and deterministic safe analysis.

Raw Environment Extensions XML may contain sensitive configuration values. Raw XML is therefore treated as trusted internal transport data and is not intended for normal presentation, logging or AI context.

The safe analyzer recognizes the currently observed structural categories:

- connections;
- operations;
- cross references;
- process properties.

The analyzer preserves safe structural metadata while excluding raw extension values from its analysis result.

Unknown future extension structures may be counted structurally without interpreting unknown attribute values as safe application data.

### Sensitive-value protection

A generic `SensitiveValueRedactor` is implemented for presentation, logging and future AI boundaries.

Sensitive-value handling is intentionally independent of project-specific business identifiers.

## Analyzer expansion cut-off

The planned generic analyzer expansion phase is complete for the current MVP checkpoint.

A new analyzer must not be introduced merely because another integration project contains different:

- field names;
- XML structures;
- component names;
- business identifiers;
- mappings;
- constants;
- endpoints.

A new analyzer or analyzer capability is justified when a real adoption case exposes a previously unsupported **generic Boomi platform representation or capability**.

This prevents Boomi Builder from becoming coupled to the SAP ↔ ZTE validation project.

## Project-agnostic principle

Boomi Builder must support future integration projects without source-code changes solely because their business integration is different.

Generic application logic must not depend on project-specific identifiers such as SAP/ZTE message names, segment names, field names, work-order codes, component IDs or business constants.

Such values may exist in:

- discovered Boomi definitions;
- project artifacts;
- project evidence;
- project configuration;
- desired state.

They must not define generic platform logic.

The target adoption lifecycle is:

`CREATE PROJECT → CONNECT → DISCOVER → ANALYZE → ADOPT`

A new project should be adoptable without changing Boomi Builder source code merely because its business data differs.

See [Architecture](docs/ARCHITECTURE.md) for the complete platform principle.

## Security model

The current implementation follows these principles:

1. Read before write.
2. Application read-only access is explicitly allow-listed.
3. Credentials are supplied to the embedded engine at runtime.
4. Secret material is separated from connection metadata.
5. Secrets must not enter AI context.
6. Raw Environment Extensions values must not enter normal presentation boundaries.
7. CLI stderr is not automatically exposed by application execution errors.
8. Unknown or unsafe data is not automatically classified as safe.
9. Write capability in the embedded engine does not imply application authorization to write.
10. Future application writes require explicit policy, authorization, approval, verification and audit.

## Repository structure

Current top-level areas include:

```text
boomi-builder/
├── ai/
├── app/
├── backend/
├── config/
├── data/
├── docs/
├── engine/
├── frontend/
├── logs/
├── projects/
├── tests/
├── .gitattributes
└── .gitignore
```

Some top-level directories are placeholders for planned product capabilities.

The primary backend package is:

`backend/src/boomi_builder/`

The backend is currently organized around:

- adapters;
- domain;
- repositories;
- services;
- API foundation.

The automated backend tests are under:

`backend/tests/`

The embedded engine is under:

`engine/boomi-cli/`

Project documentation is under:

`docs/`

## Development

The current backend development target is:

- Windows;
- Python 3.13.

See [Development guide](docs/DEVELOPMENT.md) for the current development baseline.

### Run the backend tests

From the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The full regression suite is the primary current automated verification gate.

### Run the development CLI

From the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m boomi_builder.dev_cli -h
```

The development CLI provides engineering access to implemented application capabilities. It is not the final product UI.

## Current validation project

The first real-world validation project is:

**SAP IS-U ↔ Boomi ↔ ZTE**

It is being used to prove that Boomi Builder can:

- connect safely to a real Boomi account;
- discover existing components;
- retrieve authoritative component definitions;
- understand dependency relationships;
- analyze supported Boomi representations;
- inspect environments safely;
- analyze Environment Extensions without exposing values;
- separate generic platform facts from project-specific evidence;
- support future ADOPT workflows.

Project-specific implementation facts belong to project evidence and project state, not to generic platform source logic.

## Not implemented yet

The following product capabilities are planned and must not be treated as completed:

- production-ready application authentication;
- full multi-user authorization;
- React + TypeScript product UI;
- Project domain implementation;
- Project membership;
- ADOPT workflow;
- ManagedComponent persistence;
- Evidence registry;
- Open Questions;
- Decisions;
- blocker management;
- SQLite application persistence;
- Desired State;
- Diff;
- Build Plan;
- Preview;
- Approval;
- controlled Apply;
- post-write authoritative verification;
- drift management;
- recovery workflows;
- application audit lifecycle;
- project-aware AI Chat.

The embedded engine may already contain lower-level capabilities related to some future write operations. Their existence does not make them authorized application write paths.

## Next development checkpoint

The immediate productization checkpoint is:

1. root README;
2. Windows + Python 3.13 CI;
3. read-only FastAPI surface for connections, discovery and analysis.

After that, the planned sequence is:

`Project domain → ADOPT → Evidence / blockers → SQLite persistence → Multi-user product surface`

The authoritative sequencing is maintained in [MVP plan](docs/MVP_PLAN.md).

## Design rule

The core separation is:

```text
Boomi Platform
      ↓
Embedded deterministic engine
      ↓
Application adapters
      ↓
Discovery / Analysis
      ↓
Platform Facts
      ↓
Project Context + Evidence
      ↓
Desired State / Plan
      ↓
Human approval
      ↓
Controlled deterministic execution
```

AI may assist with explanation, evidence analysis, questions and proposals over safe structured context.

AI must not become a direct uncontrolled write path to Boomi.