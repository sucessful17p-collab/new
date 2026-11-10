
# AETHER-NAS Evidence Classification

## 1. Purpose

This document defines how AETHER-NAS classifies findings discovered during NAS document analysis.

The objective is to distinguish established information from interpretations, uncertainty, conflicting claims, and missing knowledge.

AETHER-NAS prioritizes evidence traceability over unsupported confidence.

## 2. Five Evidence Classifications

Every important finding should use one of the following classifications.

### 2.1 Documented

**Definition:** A statement directly supported by an inspected source.

Example:

A project specification explicitly states that the purifier must support a particular operating pressure.

Classification: `documented`

Requirements:

- Identify the source document.
- Include a page or section reference when available.
- Preserve the original meaning.
- Avoid adding unsupported interpretation.

### 2.2 Inferred

**Definition:** A conclusion derived from one or more documented facts but not explicitly stated by a single source.

Example:

Two documents describe a component and its associated power requirement. Their relationship suggests a dependency.

Classification: `inferred`

Requirements:

- Explain the reasoning.
- Cite the supporting documents.
- Make the inferential nature explicit.
- Do not present the conclusion as a directly documented fact.

### 2.3 Unverified

**Definition:** A claim for which available evidence is insufficient to establish correctness.

Example:

A meeting note mentions that a component passed testing, but the actual test report is unavailable.

Classification: `unverified`

Requirements:

- Identify the claim.
- Explain why it cannot be confirmed.
- Identify missing supporting evidence where possible.
- Avoid declaring the claim false without evidence.

### 2.4 Conflicting

**Definition:** Two or more inspected sources contain incompatible or materially different claims.

Example:

An initial specification and another project document list different capacity requirements, but no explicit revision relationship is established.

Classification: `conflicting`

Requirements:

- Present each competing claim.
- Identify the source documents.
- Include dates or versions when available.
- Explain the disagreement.
- Preserve the conflict until evidence resolves it.

### 2.5 Missing

**Definition:** Requested information was not found within the inspected document scope.

Example:

The project folder contains a design specification but no corresponding validation report.

Classification: `missing`

Requirements:

- State what information was not found.
- Explain why it matters.
- Identify the inspected scope.
- Avoid claiming that the information does not exist elsewhere.

Use the wording:

"Not found in the inspected scope."

## 3. Evidence Record Structure

Every important finding should have a structured evidence record.

| Field | Description |
|---|---|
| Finding ID | Unique identifier within the report |
| Finding | The claim or observation |
| Classification | Documented, inferred, unverified, conflicting, or missing |
| Source | Source document name or path |
| Location | Page, section, or paragraph when available |
| Evidence | Supporting excerpt or faithful summary |
| Date/Version | Source date or version when available |
| Notes | Uncertainty, conflict, or contextual information |

Do not invent unavailable source fields.

## 4. Classification Decision Rules

Use the following decision process:

1. Was the information found in an inspected source?
   - No → `missing`.
   - Yes → Continue.

2. Does the source directly support the statement?
   - Yes → `documented`.
   - No → Continue.

3. Is the statement a reasonable interpretation of multiple documented facts?
   - Yes → `inferred`.
   - No → Continue.

4. Is the claim present but insufficiently supported or verifiable?
   - Yes → `unverified`.

5. Do inspected sources materially disagree?
   - Yes → `conflicting`.

When evidence changes the classification, preserve the original source history and explain why the classification changed.

## 5. Contradiction Analysis

When conflicting evidence is discovered:

1. Identify the disputed topic.
2. Extract each competing claim.
3. Identify the relevant sources.
4. Record dates and versions when available.
5. Compare the context of each claim.
6. Determine whether an explicit revision relationship exists.
7. Report whether the conflict is resolved or unresolved.

Do not automatically prioritize:

- The newest file.
- The longest document.
- The most frequently repeated claim.
- A document with a more authoritative-looking filename.

Authority must be established by evidence or user-provided context.

## 6. Temporal Evidence

Dates and document versions help reconstruct project history.

Record:

- Document creation dates when available.
- Explicit revision dates.
- Version identifiers.
- Recorded meeting dates.
- Test dates.
- Decision dates.

Do not confuse file modification time with the date a decision was made.

A newer document may provide updated information, but chronology alone does not prove that an earlier requirement was formally superseded.

## 7. Confidence and Scoring

AETHER-NAS must not fabricate numerical confidence percentages.

If future implementations introduce confidence scores, they must document:

- Scoring methodology.
- Evidence inputs.
- Meaning of score ranges.
- Known limitations.
- Validation results.

Until such a method is implemented and tested, use the five qualitative classifications.

## 8. Quotations and Evidence Summaries

- Quote only text actually present in the inspected source.
- Preserve the meaning of the original material.
- Label paraphrases as summaries.
- Include page or section references only when available.
- Do not manufacture quotations or citations.
- Avoid copying unnecessary sensitive information into reports.

## 9. Example Evidence Ledger

| ID | Finding | Classification | Source | Notes |
|---|---|---|---|---|
| E-001 | Project objectives are stated in the charter | Documented | Project Charter | Directly stated |
| E-002 | Component A appears to depend on Component B | Inferred | Architecture Notes | Relationship inferred from descriptions |
| E-003 | Reported test success lacks a supporting report | Unverified | Meeting Notes | Validation evidence unavailable |
| E-004 | Two specifications list different capacities | Conflicting | Initial and Revised Specifications | Revision authority unclear |
| E-005 | A final validation document was not located | Missing | Inspected Project Folder | Absence limited to inspected scope |

This is an illustrative example, not a claim about an actual project.

## 10. Required Reporting Behavior

Every AETHER-NAS report should:

- State the inspected scope.
- Apply evidence classifications consistently.
- Link important findings to available sources.
- Make unresolved conflicts visible.
- Separate recommendations from established facts.
- Explain missing or inaccessible evidence.
- Avoid overstating certainty or completeness.

## 11. Guiding Principle

**Evidence determines what Aether can claim. Uncertainty determines what Aether must disclose.**

AETHER-NAS must never make an unsupported conclusion appear authoritative.
