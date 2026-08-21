# Ciros Paint - Codex Instructions

## Project

Ciros Paint is a Windows desktop application for miniature painting and hobby management.

Current validated version: 0.10.8

Main stack:

- Python 3.12
- PySide6
- SQLAlchemy
- SQLite
- PyInstaller
- google-genai
- Gemini 3.7 Flash

## Core architecture

Ciros Paint follows a LOCAL-FIRST architecture.

The local application, repositories and SQLite database are always the source of truth.

Gemini must be used only when deterministic local systems cannot safely resolve the request or when genuine generative/visual reasoning is required.

Gemini must NEVER:

- have direct SQL/ORM/SQLite access;
- be treated as the source of truth for inventory data;
- invent paints, miniatures or database entities;
- confirm a database mutation before the local write succeeds.

## User data

User data is stored outside the executable.

Main database:

%LOCALAPPDATA%\CirosPaint\ciros_paint.db

Application upgrades must preserve all existing user data.

Never delete, recreate or overwrite the user's real database as part of an upgrade.

Tests must use isolated test databases.

## Assistant principles

Routine operations should consume 0 Gemini requests whenever possible.

Current architecture already includes:

- AssistantLocalService
- LocalEntityResolver
- AssistantWorkflowEngine
- local paint queries
- local miniature queries and mutations
- contextual miniature autocomplete
- fuzzy entity resolution
- Gemini fallback for unresolved names
- daily Gemini request counter
- seven controlled Gemini paint tools

Paint similarity alternatives must use a minimum threshold of >=85%.

Ambiguous matches must never cause unsafe mutations.

## Miniatures

When ADDING miniatures:

- search the complete miniature catalog.

When CHANGING the state of an existing miniature:

- search only miniatures currently owned by the user.

Supported stored states:

- Sin montar
- Montado
- Pintado
- Terminado

Guided state-change workflows currently expose the relevant states according to the UI workflow.

After a successful miniature state change, the assistant can offer:
"Cambiar otra miniatura"

## Gemini usage

Gemini is an interpreter of last resort.

For local deterministic operations:
Expected Gemini requests = 0.

Gemini interactions:

- use store=False;
- use low thinking where appropriate;
- keep provider conversation history minimal;
- must not receive unrestricted database access.

Image analysis is currently an area targeted for major optimization.

## Repository structure

The repository historically reconstructs Ciros Paint through a chain of source + version overlays.

Do not assume the repository root itself is the final reconstructed application source.

The validated chain currently ends with:

0.10.6
-> 0.10.7
-> 0.10.8

Before making architectural changes:

1. Inspect the repository.
2. Understand the reconstruction/build workflow.
3. Reconstruct the current source when necessary.
4. Do not blindly edit historical overlays.
5. Preserve reproducibility.

## Required development workflow

Before implementing:

1. Read this AGENTS.md completely.
2. Read README.md.
3. Read PROJECT_STATUS.md.
4. Read ASSISTANT_ARCHITECTURE.md.
5. Read CHANGELOG.md.
6. Read docs/ROADMAP.md if present.
7. Inspect the actual current implementation.
8. Understand existing tests before refactoring.

During implementation:

- prefer small, well-defined architectural components;
- avoid duplicating repository/database logic;
- keep business logic outside PySide6 widgets where practical;
- keep SQLite as the source of truth;
- write deterministic local operations whenever possible;
- do not increase Gemini usage unnecessarily;
- preserve backward compatibility with existing user data.

After implementation:

1. Add or update automated tests.
2. Run the complete test suite.
3. Run PySide6 UI smoke tests.
4. Verify database compatibility.
5. Build the Windows executable.
6. Verify the generated EXE.
7. Record its SHA-256.
8. Update CHANGELOG.md.
9. Update PROJECT_STATUS.md and architecture documentation when applicable.
10. Provide a manual test checklist for the user.

Never claim an implementation is complete when tests or build are failing.

## Current next architecture block

The next major implementation block is expected to include:

### Local image recognition

- local image preprocessing;
- local OCR;
- extraction of paint brand, range, name and product code;
- Entity Resolver integration;
- validation against the real paint catalog;
- confidence scoring;
- Gemini visual fallback only when local recognition fails;
- maximum 1 Gemini request for a visual-recognition operation;
- do not resend an already analyzed image unnecessarily;
- after a paint is identified, subsequent inventory actions must be local.

### Operations architecture

- expanded Local Intent Router;
- Command Bus;
- local rule/event engine;
- centralized Query Service;
- formal confidence/escalation policy before using Gemini.

## Later advanced block

After the operations architecture is stable:

- locally learned aliases;
- operation history;
- undo last change;
- statistics for local operations vs Gemini operations;
- Gemini request savings percentage;
- additional performance optimization based on profiling if necessary.

## Important implementation philosophy

Do not implement every future architecture idea at once.

Prefer staged changes with tests between architectural blocks.

When requirements conflict or something is ambiguous:

- do not guess;
- explain the conflict;
- ask before making a destructive or architectural decision.
