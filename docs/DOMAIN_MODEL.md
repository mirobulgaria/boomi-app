# Boomi Builder — Domain Model v1

## User

Represents an authenticated application user.

Core fields:

- id
- username
- display_name
- email
- status
- created_at
- updated_at

---

## BoomiConnection

Represents a user-owned Boomi authentication/configuration profile.

Core fields:

- id
- owner_user_id
- name
- account_id
- boomi_username
- secret_reference
- status
- last_tested_at
- created_at
- updated_at

The API token is NOT stored in this entity.

---

## SecretReference

Opaque reference to secret material managed outside normal application data.

Core fields:

- id
- owner_user_id
- provider
- external_key
- created_at
- rotated_at

Secret value is never exposed through normal domain serialization.

---

## Project

Logical integration project.

Examples:

- SAP ↔ ZTE
- CallFlow DDS

Core fields:

- id
- name
- description
- status
- created_by
- created_at
- updated_at

---

## ProjectMember

Associates users with projects.

Core fields:

- project_id
- user_id
- role

Possible roles may include:

- viewer
- developer
- approver
- administrator

Exact authorization policy is to be defined separately.

---

## ProjectEnvironment

Represents a project-specific target context.

Core fields:

- id
- project_id
- name
- environment_class
- boomi_account_id
- branch_name
- managed_scope
- write_policy
- created_at
- updated_at

Credentials do not belong to ProjectEnvironment.

The logged-in user's authorized BoomiConnection is selected at execution time.

---

## Artifact

A project input or supporting file.

Core fields:

- id
- project_id
- file_name
- media_type
- storage_path
- sha256
- classification
- uploaded_by
- uploaded_at

Possible classifications:

- XML
- XSD
- WSDL
- DOCX
- PDF
- transcript
- screenshot
- configuration
- specification
- other

---

## Evidence

Evidence-backed project statement.

Core fields:

- id
- project_id
- statement
- status
- confidence
- scenario
- source_artifact_id
- source_location
- created_by
- created_at
- updated_at

Status:

- CONFIRMED
- SUPPORTING_CONTEXT
- TO_CONFIRM

---

## OpenQuestion

Unresolved project question.

Core fields:

- id
- project_id
- question
- reason
- blocking
- owner
- expected_source
- status
- created_at
- resolved_at

---

## Decision

Explicit approved project decision.

Core fields:

- id
- project_id
- statement
- rationale
- approved_by
- approved_at
- supersedes_decision_id

---

## BoomiComponent

Normalized Actual State representation of a Boomi component.

Core fields:

- id
- project_environment_id
- component_id
- name
- type
- subtype
- version
- current_version
- deleted
- folder_id
- folder_full_path
- branch_id
- branch_name
- definition_hash
- discovered_at
- modified_at
- modified_by

---

## ComponentReference

Directed relationship between Boomi components.

Core fields:

- id
- project_environment_id
- source_component_id
- target_component_id
- relationship_type
- discovered_at

Examples:

- process_call
- map
- connector_connection
- connector_operation
- profile
- other_reference

---

## ManagedComponent

Links a project logical component to an existing or future Boomi component.

Core fields:

- id
- project_id
- logical_name
- component_type
- management_state
- boomi_component_id
- adopted_at
- adopted_by

Possible management states:

- DISCOVERED
- ADOPTED
- MANAGED
- IGNORED

---

## BoomiCapability

Represents an explicitly registered Boomi platform capability available to the deterministic creation engine.

Core fields:

- `capability_id`
- `category`
- `boomi_type`
- `boomi_subtype`
- `variant`
- `status`
- `documentation_evidence`
- `serialization_evidence`
- `supported_constraints`
- `unsupported_variants`
- `validator_contract`
- `builder_contract`
- `verifier_contract`
- `regression_evidence`
- `live_round_trip_evidence`
- `last_documentation_reviewed_at`

Allowed status values:

- `SUPPORTED`
- `PARTIALLY SUPPORTED`
- `EVIDENCE REQUIRED`

`SUPPORTED` applies only to the explicitly declared capability contract.

It must not imply support for undocumented or unimplemented variants of the same Boomi component or process shape.

A `PARTIALLY SUPPORTED` capability is writable only inside its explicitly registered subset.

An `EVIDENCE REQUIRED` capability is build-blocked.

Capability status represents Boomi platform engineering state and must remain separate from project-specific business evidence.

A `BoomiCapability` may describe:

- a process shape;
- a process-shape variant;
- a connector family;
- a Connection component contract;
- an Operation component contract;
- a parameter-value variant;
- another deterministic Boomi creation capability.

The authoritative human-readable capability registry is:

`docs/BOOMI_CAPABILITY_COMPLIANCE.md`

---
## DesiredComponent

Approved or proposed Desired State.
A `DesiredComponent` may use only `BoomiCapability` variants that the deterministic engine can validate and serialize.

An `EVIDENCE REQUIRED` capability is build-blocked.

A `PARTIALLY SUPPORTED` capability is writable only inside its explicitly declared subset.

Core fields:

- id
- project_id
- logical_name
- component_type
- specification
- specification_hash
- evidence_status
- approval_status
- created_at
- updated_at

Desired State must not silently resolve TO_CONFIRM information.

---

## ComponentDiff

Difference between Desired State and Actual State.

Core fields:

- id
- desired_component_id
- actual_component_id
- classification
- diff_payload
- calculated_at

Classification:

- MATCH
- MISSING
- EXTRA
- DIFFERENT
- INCOMPLETE
- UNKNOWN
- BLOCKED
- DRIFTED

---

## BuildPlan

Ordered proposed change set.
A `BuildPlan` must not contain an executable write step for an unresolved `EVIDENCE REQUIRED` capability.

Capability validation must complete before the plan can authorize a deterministic write step.

Core fields:

- id
- project_id
- project_environment_id
- created_by
- status
- actual_state_revision
- desired_state_revision
- created_at
- approved_at

Possible status:

- DRAFT
- BLOCKED
- READY
- APPROVED
- EXECUTING
- COMPLETED
- FAILED
- SUPERSEDED

---

## BuildPlanStep

One deterministic operation in a BuildPlan.

Core fields:

- id
- build_plan_id
- sequence
- action
- target_logical_name
- target_component_id
- specification_reference
- preconditions
- expected_result
- status

Possible actions include:

- CREATE
- UPDATE
- ADOPT
- DELETE
- RESTORE
- VERIFY

---

## Execution

One execution attempt of an approved plan or read operation.

Core fields:

- id
- project_id
- project_environment_id
- build_plan_id
- application_user_id
- boomi_connection_id
- boomi_username
- operation
- started_at
- finished_at
- status
- verification_status
- correlation_id

---

## ExecutionStep

Detailed execution result.

Core fields:

- id
- execution_id
- sequence
- action
- component_id
- before_version
- after_version
- result
- verification_result
- started_at
- finished_at

---

## AuditEvent

Immutable security/operational audit event.

Core fields:

- id
- timestamp
- application_user_id
- project_id
- event_type
- entity_type
- entity_id
- correlation_id
- result
- metadata

Secret material is forbidden in AuditEvent metadata.

---

## Core relationships
Additional capability relationships:

`BoomiCapability`
- has documentation, serialization, regression and optional live round-trip evidence;
- constrains the writable variants available to `DesiredComponent`;
- constrains executable write steps in `BuildPlan`.

`DesiredComponent`
- may reference one or more `BoomiCapability` variants required to represent its desired state.

`BuildPlan`
- may execute only capability variants whose registered status and supported subset permit deterministic creation.

User
  1 ─── * BoomiConnection

User
  * ─── * Project
        through ProjectMember

Project
  1 ─── * ProjectEnvironment

Project
  1 ─── * Artifact

Project
  1 ─── * Evidence

Project
  1 ─── * OpenQuestion

Project
  1 ─── * Decision

ProjectEnvironment
  1 ─── * BoomiComponent

BoomiComponent
  * ─── * BoomiComponent
        through ComponentReference

Project
  1 ─── * DesiredComponent

DesiredComponent
  1 ─── * ComponentDiff

Project
  1 ─── * BuildPlan

BuildPlan
  1 ─── * BuildPlanStep

BuildPlan
  1 ─── * Execution

Execution
  1 ─── * ExecutionStep