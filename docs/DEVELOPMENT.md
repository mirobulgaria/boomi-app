# Boomi Builder — Development Environment

## Baseline date

2026-09-11

## Operating system

Microsoft Windows 11 Enterprise
64-bit

## Shell

Windows PowerShell 5.1

The proven embedded Boomi CLI currently executes in Windows PowerShell 5.1.

## Git

Git 2.55.0.windows.3

## Python

Python 3.13.15

Backend virtual environment:

backend\.venv

pip baseline:

26.2.1

## Backend direct dependencies

- FastAPI 0.141.1
- Uvicorn 0.52.4
- HTTPX 0.28.1
- pytest 9.1.1

Observed relevant transitive dependencies at initial bootstrap:

- Pydantic 2.13.5
- Starlette 1.6.0

Initial dependency integrity check:

No broken requirements found.

## Frontend toolchain

Not initialized yet.

Node.js and npm are intentionally deferred until the frontend architecture is activated.

The planned frontend direction is React + TypeScript, but frontend bootstrap is not part of the current backend baseline.

## Backend source layout

backend\
  src\
    boomi_builder\
      api\
      domain\
      services\
      repositories\
      adapters\
  tests\

## Initial API

GET /health

Expected response:

{
  "status": "ok",
  "service": "boomi-builder-api",
  "version": "0.1.0"
}

## Security

Secrets MUST NOT be committed to Git.

BOOMI_API_TOKEN must never be stored in source code, project JSON, logs, AI context or plaintext application data.

## Engine isolation

The embedded engine lives under:

engine\boomi-cli\

The standalone CLI lives outside this repository under:

C:\Users\miroslav.kostov\Boomi\boomi-cli

Boomi Builder development MUST NOT automatically modify the standalone CLI.
## Capability development gate

Every new or materially expanded writable Boomi capability must follow the capability compliance lifecycle.

Required sequence:

1. review the current official Boomi documentation;
2. identify documented semantic variants, constraints, cardinality, dependencies and runtime requirements;
3. collect authoritative Boomi component XML for the variants being implemented;
4. define the Builder desired-state capability contract;
5. define unsupported variants explicitly;
6. implement deterministic validation;
7. implement deterministic XML generation;
8. implement independent generated-XML verification;
9. add positive regression tests;
10. add meaningful negative regression tests;
11. run targeted regression;
12. run the full regression suite;
13. perform a controlled live round-trip when required for write confidence;
14. update `docs/BOOMI_CAPABILITY_COMPLIANCE.md`.

The following do not independently establish generic Boomi support:

- a passing XML generation test;
- a single discovered Boomi component;
- a single working project scenario;
- naming similarity;
- an AI inference;
- an undocumented default.

If documentation and serialization evidence are incomplete, the capability must remain:

- `PARTIALLY SUPPORTED`; or
- `EVIDENCE REQUIRED`.

Unsupported variants must fail deterministically before a Boomi API write.

Development must prefer explicit build refusal over generation of a component whose Boomi contract has not been proven.

## Capability regression rule

Every writable capability requires positive and meaningful negative regression coverage.

Negative coverage should include, where applicable:

- invalid numeric ranges;
- invalid enumerated values;
- unsupported variants;
- cardinality violations;
- invalid component references;
- invalid topology;
- mutually incompatible options;
- unexpected serialization.

Regression evidence proves continued implementation behavior for an already declared capability contract.

Regression evidence does not expand the capability contract by itself.