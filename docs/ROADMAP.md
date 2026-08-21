# Ciros Paint - Development Roadmap

## Current validated version

Ciros Paint 0.10.8

This document describes what is already implemented, what is planned next,
and the intended order of future architectural work.

---

# CURRENT STATE - 0.10.8

## Local-first assistant foundation

Already implemented:

- AssistantLocalService.
- LocalEntityResolver.
- AssistantWorkflowEngine.
- Local paint queries.
- Local miniature queries.
- Local miniature status mutations.
- Fuzzy entity resolution.
- Contextual miniature autocomplete.
- Full catalog autocomplete when adding miniatures.
- Owned-miniature-only autocomplete when changing status.
- Deterministic guided miniature workflows.
- "Cambiar otra miniatura" chained workflow.
- Automatic Gemini fallback when local paint resolution fails.
- Gemini result validation against the real local catalog.
- Daily Gemini request counter.
- Local operations continue working without a Gemini API key.
- SQLite remains the source of truth.
- Gemini has no direct database access.

## Current Gemini integration

- Gemini 3.7 Flash.
- Interactions API.
- store=False.
- low thinking where applicable.
- Seven controlled paint tools.
- Temporary provider history only.
- Usage information shown when available.

---

# NEXT MAJOR BLOCK

The next update combines two goals:

1. Reduce Gemini usage aggressively.
2. Introduce the next layer of operations architecture.

---

# BLOCK 1 - LOCAL IMAGE RECOGNITION

## Goal

Routine recognition of paint bottles from photographs should normally use:

0 Gemini requests.

If local recognition fails:

maximum 1 Gemini request.

## Image preprocessing

Implement a local preprocessing pipeline.

Possible technologies:

- OpenCV.
- Qt image utilities where appropriate.

Possible operations:

- resize;
- crop;
- grayscale;
- contrast enhancement;
- sharpening;
- denoising;
- thresholding;
- perspective correction when useful.

Avoid unnecessarily large images.

## Local OCR

Introduce local OCR for paint labels.

Primary goal:
extract information such as:

- brand;
- product range;
- paint name;
- product/reference code;
- visible textual identifiers.

Example:

VALLEJO
GAME COLOR
72.051
BLACK

OCR must run locally and must not consume Gemini/API requests.

## OCR normalization

Normalize common OCR mistakes before entity resolution.

Examples:

- O <-> 0
- I <-> 1
- spacing errors
- punctuation errors
- line breaks
- accents
- case differences

Example:

72.O51

should be considered as a possible:

72.051

when supported by catalog evidence.

## Entity Resolver integration

OCR output must be passed through LocalEntityResolver.

Resolution priority should favour strong deterministic identifiers.

Suggested priority:

1. Exact product/reference code.
2. Code + brand.
3. Brand + range + exact name.
4. Normalized exact match.
5. High-confidence fuzzy match.
6. Candidate selection if ambiguous.
7. Gemini fallback only when necessary.

## Catalog validation

A locally or externally interpreted paint must always be validated against
the real Ciros Paint paint catalog.

Never create an entity solely because OCR or Gemini says that it exists.

## Confidence policy

Image recognition must produce a confidence result.

Possible outcomes:

### HIGH CONFIDENCE

Unique local match.

Action:
accept locally.

Gemini requests: 0.

### AMBIGUOUS

Several plausible catalog matches.

Action:
show candidate choices to the user.

Gemini requests:
0 when user selection can resolve the ambiguity.

### LOW CONFIDENCE / UNRESOLVED

Local systems cannot identify the paint safely.

Action:
Gemini visual fallback.

Gemini requests:
maximum 1.

The Gemini result must then be validated locally.

## Gemini visual fallback

Image fallback must be tool-less.

Do not enter a function-calling loop merely to identify a paint.

One visual analysis should generate at most one Gemini API interaction.

## Conversation entity context

After identifying a paint, store a local contextual reference inside the
current assistant conversation.

Example:

recognized_entity:
type: paint
catalog_id: ...
brand: Vallejo
range: Game Color
code: 72.051
name: Black

Subsequent requests such as:

- "añadir al inventario"
- "añadir a futuras compras"
- "cuánto stock tengo"
- "buscar alternativas"

should operate on this locally stored entity.

They must not require the image to be sent to Gemini again.

## Image reuse rule

Do not resend an already analyzed image to Gemini for later deterministic
operations.

After recognition, retain structured local information instead of depending
on repeated visual interpretation.

---

# BLOCK 2 - OPERATIONS ARCHITECTURE

This block should be implemented in the same architectural phase after
carefully inspecting the current 0.10.8 implementation.

---

## Expanded Local Intent Router

Create a clearer deterministic routing layer for known application intents.

Examples:

- SEARCH_PAINT
- GET_PAINT_STOCK
- ADD_PAINT
- SET_PAINT_QUANTITY
- ADD_FUTURE_PURCHASE
- COMPLETE_PURCHASE
- LIST_MINIATURES
- ADD_MINIATURE
- CHANGE_MINIATURE_STATUS
- ANALYZE_PAINT_IMAGE

Routine recognized intents should not require Gemini.

Important regression:

queries such as:

"Buscar pintura: Gris"

must be handled locally and must not unnecessarily fall through to Gemini.

---

## Command Bus

Introduce explicit commands for application mutations.

Possible commands:

- AddPaintToInventory
- SetPaintQuantity
- AddPaintToFuturePurchases
- CompletePaintPurchase
- AddMiniatures
- ChangeMiniatureStatus

Goals:

- keep mutation logic outside the UI;
- centralize validation;
- make operations testable;
- provide a foundation for operation history and Undo.

Commands must return explicit success/failure results.

Never confirm success before the command finishes successfully.

---

## Rule / Event Engine

Introduce local domain events for successful operations.

Possible events:

- PaintAddedToInventory
- PaintQuantityChanged
- PaintPurchaseCompleted
- PaintAddedToFuturePurchases
- MiniatureAdded
- MiniatureStatusChanged

Rules may react to these events.

Examples:

PaintPurchaseCompleted
-> update inventory
-> update/remove future purchase entry

PaintQuantityChanged
-> reevaluate availability

MiniatureStatusChanged
-> keep state bucket totals consistent

Events must remain local.

Gemini must not be responsible for business rules.

---

## Centralized Query Service

Create a centralized read/query layer.

The UI and Assistant should not independently recreate database-query logic.

Possible responsibilities:

- paint catalog queries;
- paint inventory queries;
- stock queries;
- future purchase queries;
- miniature collection queries;
- miniature catalog queries.

Goals:

- avoid duplicated reads;
- maintain consistent filters;
- simplify assistant workflows;
- simplify future performance optimization.

---

## Confidence / Escalation Gateway

Formalize the local-to-Gemini escalation policy.

Expected pipeline:

1. Intent recognition.
2. Exact local match.
3. Normalization.
4. Fuzzy/entity resolution.
5. Confidence evaluation.
6. Candidate selection when appropriate.
7. Gemini only if unresolved.
8. Validate Gemini interpretation locally.
9. Execute local command if safe.

Gemini is the final interpreter, not the first resolver.

---

# TARGET AFTER NEXT MAJOR BLOCK

Routine operations:

> 95% locally resolved where practical.

Expected Gemini requests:

Paint searches:
0

Inventory operations:
0

Miniature operations:
0

Future purchase operations:
0

Clear OCR paint recognition:
0

Ambiguous OCR paint recognition resolved by user selection:
0

Visual recognition where local OCR fails:
maximum 1

Open-ended hobby advice:
Gemini when appropriate.

---

# LATER ADVANCED BLOCK

Do not implement this block until the operations architecture is stable.

---

## Learned local aliases

Allow confirmed aliases to be stored locally.

Example:

Stormtruper
-> Stormtroopers

After confirmation, future resolution should be local.

Aliases must not silently create unsafe mappings.

---

## Operation history

Store successfully executed application operations.

Possible information:

- timestamp;
- command type;
- affected entity;
- previous value;
- new value;
- source:
  - UI
  - Assistant local
  - Gemini-assisted interpretation

This should become the basis for auditability and Undo.

---

## Undo last operation

Support safe reversal of compatible commands.

Examples:

Miniature:
Montado -> Pintado

Undo:
Pintado -> Montado

Paint quantity:
2 -> 3

Undo:
3 -> 2

Undo must operate on recorded local command history.

Gemini is not required for Undo.

---

## Local vs Gemini statistics

Extend Assistant telemetry.

Possible metrics:

- operations today;
- local operations today;
- Gemini operations today;
- Gemini requests today;
- percentage resolved locally;
- percentage of Gemini calls avoided.

Example:

47 operaciones
45 locales
2 Gemini
95.7% local

Do not invent estimated Gemini requests.

Only count actual provider calls.

---

## Performance optimization

Do not prematurely optimize.

After architecture is stable:

- profile application startup;
- profile catalog loading;
- profile SQLite queries;
- inspect repeated repository calls;
- inspect OCR processing latency;
- inspect memory usage.

Optimize only where measurements show meaningful benefit.

---

# IMPLEMENTATION ORDER

Recommended order:

## Phase A

Audit 0.10.8 architecture.

No code changes initially.

## Phase B

Expanded Intent Router + confidence policy.

## Phase C

Centralized Query Service.

## Phase D

Command Bus.

## Phase E

Rule/Event Engine.

## Phase F

Local image preprocessing + OCR.

## Phase G

Image Entity Resolver integration.

## Phase H

Single-request Gemini visual fallback.

## Phase I

Conversation entity context and local follow-up operations.

## Phase J

Full regression suite + Windows build.

Then manually validate the resulting version before beginning the advanced block.

---

# DEVELOPMENT PRINCIPLE

Ciros Paint should progressively become:

Application logic
-> deterministic local services
-> SQLite/catalog
-> Gemini only when genuinely necessary

Not:

User request
-> Gemini
-> application logic

The application must remain useful even when Gemini is unavailable or the
user has exhausted the external API quota.
