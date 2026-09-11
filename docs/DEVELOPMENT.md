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