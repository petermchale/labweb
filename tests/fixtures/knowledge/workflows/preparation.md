---
id: https://example.org/synthetic/workflow/preparation
type: kg:Workflow
label: Synthetic preparation
status: synthetic fixture
inputs:
- https://example.org/synthetic/artifact/raw-inputs
outputs:
- https://example.org/synthetic/artifact/prepared-inputs
steps:
- id: https://example.org/synthetic/workflow/preparation/step/0
  type: kg:PlanStep
  label: Synthetic preparation step 1
  inputs:
  - https://example.org/synthetic/artifact/raw-inputs
  outputs:
  - https://example.org/synthetic/artifact/prepared-inputs
  dependsOn: []
  derivedFrom: https://example.org/synthetic/documentation
  sourceDigest: '0000000000000000000000000000000000000000000000000000000000000000'
  sourceStartLine: 1
  sourceEndLine: 1
  sourceQuote: Synthetic workflow documentation for parser and graph tests.
- id: https://example.org/synthetic/workflow/preparation/step/1
  type: kg:PlanStep
  label: Synthetic preparation step 2
  inputs:
  - https://example.org/synthetic/artifact/raw-inputs
  outputs:
  - https://example.org/synthetic/artifact/prepared-inputs
  dependsOn:
  - https://example.org/synthetic/workflow/preparation/step/0
  derivedFrom: https://example.org/synthetic/documentation
  sourceDigest: '0000000000000000000000000000000000000000000000000000000000000000'
  sourceStartLine: 1
  sourceEndLine: 1
  sourceQuote: Synthetic workflow documentation for parser and graph tests.
derivedFrom: https://example.org/synthetic/documentation
sourceDigest: '0000000000000000000000000000000000000000000000000000000000000000'
sourceStartLine: 1
sourceEndLine: 1
sourceQuote: Synthetic workflow documentation for parser and graph tests.
---

Synthetic workflow used only for software tests.
