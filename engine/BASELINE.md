# Boomi Builder Embedded Engine Baseline

## Source

Standalone CLI:

C:\Users\miroslav.kostov\Boomi\boomi-cli

## Proven baseline

v6-controlled-restore-proven

## Imported

2026-09-11

## Verification

At import time:

- standalone CLI matched v6 checkpoint byte-for-byte;
- embedded engine matched standalone CLI byte-for-byte;
- source differences: 0;
- copy failures: 0.

## Isolation rule

The standalone `boomi-cli` and the Boomi Builder embedded engine are independent codebases from this point forward.

Changes under:

`boomi-builder\engine\`

MUST NOT automatically modify:

`Boomi\boomi-cli\`

Changes developed for Boomi Builder may be ported back to the standalone CLI only through an explicit, separately tested change.

## Project-data rule

The embedded engine is generic.

Project-specific workspaces, credentials, secrets, generated artifacts and project evidence MUST NOT be embedded in the engine source.