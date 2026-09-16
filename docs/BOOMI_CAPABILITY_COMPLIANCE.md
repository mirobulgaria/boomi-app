# Boomi Builder --- Boomi Capability Compliance

## Purpose

This document is the authoritative capability registry for deterministic
Boomi component creation in Boomi Builder.

The objective is not merely to generate XML that resembles an existing
Boomi component.

The objective is to create Boomi components that conform to the
supported Boomi platform semantics and to proven Boomi component
serialization.

A component, process shape, connector, operation, field, attribute,
value, or XML structure must not be treated as generically supported
merely because it was observed in one existing component.

## Authoritative engineering rule

A writable Boomi capability requires two independent evidence layers:

1.  Current official Boomi documentation.
2.  Authoritative Boomi component serialization evidence.

Official Boomi documentation defines:

-   semantic behavior;
-   supported variants;
-   allowed values;
-   ranges;
-   cardinality;
-   dependencies;
-   runtime behavior;
-   connector-specific requirements;
-   documented limitations.

Authoritative Boomi component evidence defines:

-   XML elements;
-   XML attributes;
-   nesting;
-   ordering where relevant;
-   component references;
-   component types and subtypes;
-   shape configuration;
-   topology;
-   dragpoints;
-   connector-specific serialization.

Neither evidence layer replaces the other.

Official documentation without proven serialization is insufficient for
deterministic XML generation.

A single observed XML instance without documentation review is
insufficient to claim generic support.

## Capability lifecycle

Every writable capability follows this lifecycle:

``` text
Official Boomi Documentation
            +
Authoritative Boomi XML Evidence
            |
            v
Capability Contract
            |
            v
Desired-State Specification
            |
            v
Validate
            |
            v
Build
            |
            v
Verify
            |
            v
Positive and Negative Regression
            |
            v
Controlled Live Round-Trip
            |
            v
SUPPORTED
```

The application must not bypass this lifecycle.

## Capability statuses

### SUPPORTED

A capability can be marked `SUPPORTED` only when all required evidence
and implementation gates for the declared capability are complete.

This requires:

-   the relevant current official Boomi documentation has been reviewed;
-   semantic options and constraints are known;
-   required serialization is supported by authoritative Boomi evidence;
-   the desired-state specification represents the supported contract;
-   deterministic validation exists;
-   deterministic XML generation exists;
-   deterministic generated-XML verification exists;
-   positive regression coverage exists;
-   negative regression coverage exists;
-   references and dependencies are validated;
-   controlled live round-trip evidence exists where required for write
    confidence.

`SUPPORTED` always applies to an explicitly defined capability contract.

It must not be interpreted more broadly than the variants recorded in
this registry.

### PARTIALLY SUPPORTED

`PARTIALLY SUPPORTED` means that Boomi supports a broader capability
than Boomi Builder currently implements.

The supported subset must be explicit.

Unsupported variants must be rejected.

The application must never silently approximate, omit, replace, or
default an unsupported variant merely to make component creation
succeed.

### EVIDENCE REQUIRED

`EVIDENCE REQUIRED` means that a capability is known or documented to
exist, but Boomi Builder does not yet have sufficient evidence to create
it safely.

Possible missing evidence includes:

-   semantic documentation;
-   serialization evidence;
-   representative component definitions;
-   validation rules;
-   Build support;
-   Verify support;
-   regression coverage;
-   controlled live validation.

An `EVIDENCE REQUIRED` capability is build-blocked.

## Evidence model

### Official documentation evidence

Official Boomi documentation is authoritative for the documented
platform semantics of a capability.

It is used to establish:

-   what the capability does;
-   valid configuration variants;
-   allowed values;
-   numeric or enumerated constraints;
-   cardinality;
-   execution behavior;
-   dependencies;
-   runtime prerequisites;
-   documented limitations.

Documentation evidence must be reviewed against the current Boomi
documentation before a capability is added or materially expanded.

### Authoritative serialization evidence

Authoritative serialization evidence establishes how a supported
capability is represented in a Boomi component definition.

Preferred evidence is a current component definition retrieved directly
from Boomi.

Serialization evidence is used to establish:

-   XML element names;
-   XML attribute names;
-   nesting;
-   child cardinality;
-   ordering where relevant;
-   references;
-   component types and subtypes;
-   shape configuration;
-   dragpoint representation;
-   topology representation;
-   connector-specific configuration.

Multiple representative components are required when a documented
capability has multiple variants and those variants serialize
differently.

### Regression evidence

Regression tests prove that the implementation continues to preserve a
declared capability contract.

Regression tests do not expand the capability contract by themselves.

A passing test for one observed variant must not be interpreted as
evidence that every documented Boomi variant is supported.

### Live round-trip evidence

For writable capabilities, controlled creation and retrieval from Boomi
provides the strongest integration-level evidence that generated
component definitions are accepted and interpreted by the platform.

Live round-trip evidence supplements documentation, serialization
evidence, and deterministic tests.

It does not replace them.

## Build safety rule

When desired state contains a capability or variant outside the
registered writable subset, the correct result is:

``` text
BUILD BLOCKED
```

Boomi Builder must not:

-   invent Boomi XML;
-   infer XML from similar names;
-   silently remove unsupported configuration;
-   manufacture component references;
-   substitute a different process shape;
-   guess connector settings;
-   invent environment-specific configuration;
-   invent undocumented defaults merely to make generation succeed;
-   treat one observed component as the universal Boomi contract.

The deterministic engine must fail before a Boomi API write when the
requested desired state cannot be represented safely.

## Current process-shape capability registry

The registry below is intentionally conservative.

A capability is not promoted to `SUPPORTED` until its declared Builder
contract has passed the required compliance gates.

  --------------------------------------------------------------------------------------------
  Capability               Status      Current Builder position     Required work
  ------------------------ ----------- ---------------------------- --------------------------
  Start                    PARTIALLY   Proven Start serialization   Complete documentation and
                           SUPPORTED   exists for currently         serialization audit for
                                       implemented variants         every Start variant
                                                                    intended for creation

  Map                      EVIDENCE    Process shape can reference  Complete formal
                           REQUIRED    an existing Map component    documentation and
                                                                    serialization compliance
                                                                    review

  Connector Action         EVIDENCE    Generic connection/operation Establish generic
                           REQUIRED    reference model exists       process-step contract and
                                                                    connector-specific
                                                                    capability contracts

  Return Documents         EVIDENCE    Existing process creation    Complete documentation,
                           REQUIRED    support exists               serialization and
                                                                    return-semantics audit

  Process Call             EVIDENCE    Existing process creation    Audit documented options,
                           REQUIRED    and return-path support      return paths and
                                       exists                       serialization variants

  Stop                     EVIDENCE    Observed serialization is    Complete official semantic
                           REQUIRED    implemented                  and serialization
                                                                    compliance review

  Branch                   PARTIALLY   `numBranches` serialization  Enforce documented integer
                           SUPPORTED   exists                       range 2--25 and verify
                                                                    topology/cardinality
                                                                    behavior

  Try/Catch                PARTIALLY   `catchAll` and `retryCount`  Enforce documented retry
  (`catcherrors`)          SUPPORTED   serialization exists for an  range 0--5 and prove
                                       observed variant             failure-trigger
                                                                    serialization variants

  Decision                 PARTIALLY   Validate/Build/Verify exist  Audit documented
                           SUPPORTED   for exactly two operands     parameter-value types and
                                       using                        obtain serialization
                                       proven`process + static`     evidence before expanding
                                       serialization                

  Message                  EVIDENCE    Real Message instances are   Documentation and
                           REQUIRED    available as evidence        serialization audit
                                                                    required before Build
                                                                    implementation

  Data Process             EVIDENCE    Real Data Process instances  Audit supported processing
                           REQUIRED    are available as evidence    operations and
                                                                    representative
                                                                    serialization

  Set Properties           EVIDENCE    Real document-property       Audit property types,
  (`documentproperties`)   REQUIRED    serialization evidence       source values,
                                       exists                       multiplicity and supported
                                                                    variants

  Exception                EVIDENCE    Requested Builder capability Documentation and
                           REQUIRED                                 serialization evidence
                                                                    required

  Notify                   EVIDENCE    Requested Builder capability Documentation and
                           REQUIRED                                 serialization evidence
                                                                    required
  --------------------------------------------------------------------------------------------

## Current connector capability registry

Connector families must be treated independently because their
Connection, Operation, action, profile and runtime contracts differ.

  -----------------------------------------------------------------------------
  Capability   Status     Required compliance
  ------------ ---------- -----------------------------------------------------
  SAP JCo      EVIDENCE   Connection, Operation, supported actions,
               REQUIRED   IDoc/BAPI/RFM semantics, references, runtime
                          prerequisites and serialization

  Web Services EVIDENCE   Connection, Operation, WSDL behavior, SOAP version,
  SOAP Client  REQUIRED   authentication, profiles and serialization

  Web Services EVIDENCE   Listener/start semantics, Operation contract,
  Server       REQUIRED   request/response behavior, deployment/runtime
                          requirements and serialization

  Database     EVIDENCE   Connection, Operation, supported actions,
               REQUIRED   JDBC/runtime requirements, profiles and serialization
  -----------------------------------------------------------------------------

## Known documentation constraints requiring remediation

### Branch

Official Boomi documentation defines Number of Branches as an integer in
the range 2 through 25.

The Builder must therefore enforce:

``` text
numBranches is integer
AND
2 <= numBranches <= 25
```

Accepting an arbitrary numeric value is insufficient.

Validation must reject:

-   values below 2;
-   values above 25;
-   non-integer numeric values;
-   non-numeric values.

Build must serialize only a value that has already passed this
validation.

Verify must confirm that generated serialization preserves the validated
branch count.

### Try/Catch

Official Boomi documentation defines Retry Count in the range 0 through
5.

The documented failure trigger distinguishes Document Errors from All
Errors.

The observed serialization values:

``` text
catchAll=true
retryCount=0
```

prove one real serialization instance only.

They do not prove every supported Try/Catch variant.

The Builder must enforce the documented retry range for the supported
contract.

Additional failure-trigger variants must not be implemented by
assumption.

Their serialization must be established from authoritative component
evidence.

### Decision

Decision compares exactly two values.

The currently implemented Builder contract supports the proven
serialization:

``` text
value 1 = process
value 2 = static
```

The current implementation includes deterministic:

-   Validate;
-   Build;
-   Verify;
-   positive regression;
-   negative regression.

This establishes a working subset.

It must not be interpreted as the complete Boomi Decision
parameter-value model.

Additional documented parameter-value types require both documentation
review and authoritative serialization evidence before Build support is
added.

Until then, unsupported Decision variants must be rejected.

### Start

Start has multiple documented execution variants.

The Builder must distinguish between:

-   the full documented Boomi Start capability;
-   the Start variants for which deterministic serialization has
    actually been proven.

A working Connector Start or Data Passthrough Start does not establish
serialization support for every Start type.

Each supported Start variant requires its own capability evidence.

## Parameter-value architecture

Parameter values are a cross-cutting Boomi concept.

They occur in multiple contexts including:

-   Decision;
-   Message;
-   Set Properties;
-   connector operations;
-   other process configurations.

Boomi Builder must not define a universal parameter-value contract from
a single observed shape.

The domain model should support typed parameter values.

The owning shape or component determines which parameter-value variants
are valid.

For example:

``` text
ParameterValue
    |
    +-- Static
    +-- Process
    +-- Document Property
    +-- Profile Element
    +-- Connector/Query-derived variant
    +-- Other documented variant
```

This diagram represents a domain-model direction, not a declaration that
all variants are currently writable.

Each writable serialized variant requires authoritative evidence.

## Connector architecture rule

A generic `connectoraction` process shape does not prove that all Boomi
connectors share the same creation contract.

Connector capabilities must be modeled by at least:

-   connector type;
-   connection component type;
-   connection subtype where applicable;
-   operation component type;
-   operation subtype where applicable;
-   action;
-   request profile behavior;
-   response profile behavior;
-   component references;
-   documented prerequisites;
-   proven serialization.

SAP JCo, Web Services SOAP Client, Web Services Server and Database are
therefore separate capability families.

The application must not reuse a connector contract merely because two
connectors expose similarly named Connection or Operation concepts.

## Component-reference rule

A generated process must not contain guessed component identifiers.

References used during Build must resolve deterministically to
components that satisfy the expected:

-   component type;
-   component subtype where applicable;
-   branch;
-   folder/write policy where relevant;
-   connector contract where relevant.

Reference validation must occur before component creation.

## Topology rule

Supporting a shape requires more than supporting its configuration XML.

Boomi Builder must also preserve valid process topology.

The supported contract must account for:

-   outgoing connections;
-   required number of paths;
-   path identifiers;
-   path labels/text where applicable;
-   child shape references;
-   Process Call return paths where applicable;
-   terminal shape behavior.

Topology rules established by documentation must be enforced when
deterministic representation is known.

Observed dragpoint serialization must be verified against authoritative
component evidence.

## Validation rule

Validation is not merely JSON/schema validation.

The deterministic validator is responsible for enforcing the supported
Boomi capability contract.

Validation includes, where applicable:

-   required properties;
-   property types;
-   enumerated values;
-   numeric ranges;
-   cardinality;
-   mutually exclusive options;
-   required component references;
-   connector-specific constraints;
-   topology constraints;
-   capability status.

A syntactically valid desired-state specification can still be invalid
for Boomi.

Such a specification must be rejected before Build.

## Build rule

Build is a deterministic serialization operation.

Build must:

-   consume only validated desired state;
-   generate only registered serialization variants;
-   preserve references;
-   preserve required hierarchy;
-   preserve topology;
-   avoid environment-specific hard-coding;
-   avoid inferred defaults;
-   avoid unsupported variants.

Build must not contain fallback behavior that silently converts an
unsupported capability into another representation.

## Verify rule

Verify is independent from Build.

The verifier must compare generated component XML with the desired-state
capability contract.

Verify should detect, where applicable:

-   missing elements;
-   unexpected elements;
-   missing attributes;
-   unexpected attributes;
-   incorrect values;
-   incorrect child cardinality;
-   incorrect parameter-value variants;
-   incorrect references;
-   incorrect topology;
-   incorrect return paths.

Build success without Verify success is not sufficient for a writable
capability.

## Negative regression rule

Every writable capability requires negative tests for meaningful invalid
states.

Examples include:

-   invalid numeric range;
-   invalid enum;
-   unsupported parameter-value type;
-   incorrect child cardinality;
-   invalid component reference;
-   unexpected XML child;
-   invalid topology;
-   invalid combination of options.

Negative tests are essential because Boomi Builder must reject
unsupported desired state rather than generate best-effort XML.

## Controlled live round-trip

For writable capabilities, the strongest validation is a controlled
round-trip in an approved test location:

``` text
Desired State
    |
    v
Validate
    |
    v
Build XML
    |
    v
Verify XML
    |
    v
Create in approved Boomi test folder
    |
    v
Retrieve component from Boomi
    |
    v
Analyze returned definition
    |
    v
Compare structural contract
```

Component creation does not imply deployment.

Component creation does not imply execution.

Production must not be used as a capability-discovery environment.

The existing CLI safety model and allowed-write-folder controls remain
mandatory.

## Documentation maintenance

Official Boomi documentation is an external dependency and can change.

Before adding or materially extending a writable capability:

1.  review the current official Boomi documentation;
2.  record semantic constraints;
3.  compare them with this registry;
4.  collect missing serialization evidence;
5.  update desired-state contracts;
6.  update Validate;
7.  update Build;
8.  update Verify;
9.  add positive regression tests;
10. add negative regression tests;
11. run targeted regression;
12. run full regression;
13. perform controlled live validation where appropriate;
14. update this registry.

A capability must be downgraded if later evidence shows that the
implementation does not correctly represent its declared Boomi contract.

## Compliance remediation priority

Before broad expansion of process creation, review the existing
capabilities in this order:

1.  Start
2.  Map
3.  Connector Action
4.  Return Documents
5.  Process Call
6.  Stop
7.  Branch
8.  Try/Catch
9.  Decision
10. Message
11. Data Process
12. Set Properties
13. Exception
14. Notify
15. SAP JCo
16. Web Services SOAP Client
17. Web Services Server
18. Database

The first objective is to bring already implemented capabilities into
explicit compliance.

The second objective is to expand process creation only through
evidence-backed capability contracts.

## Definition of success

Boomi Builder is successful when it can deterministically create Boomi
components without relying on undocumented guesses.

For a supported process, the expected path is:

``` text
Desired State
    -> Validate
    -> Resolve References
    -> Build
    -> Verify
    -> Preview
    -> Human Approval
    -> Controlled Create
    -> Retrieve
    -> Verify Returned Component
```

The application should ultimately provide the same deterministic
confidence for component creation that the embedded CLI provides at the
execution boundary.

The objective is not maximum shape count.

The objective is reliable creation of Boomi components that Boomi
accepts and interprets correctly.
