# Spec Delta

## Purpose

Guarantees that every MVR written by mutate-mvr has unique uuids, no duplicate members and no unreferenced files, and that this cleanup is repeatable.

## ADDED Requirements

### Requirement: Deduplicate members on write
Every command that writes an MVR SHALL remove members whose content identity equals that of an earlier member in the same parent, keeping the first.

#### Scenario: Doubled layer contents
- **WHEN** a layer lists each of its objects twice with identical content
- **THEN** the output lists each once

### Requirement: Unique uuids
Every written MVR SHALL have no empty and no repeated uuid. A unique existing uuid SHALL be kept; a repeated or empty one SHALL be replaced by a uuid derived deterministically from the old uuid and the member's content identity.

#### Scenario: Colliding uuids
- **WHEN** two different members share a uuid
- **THEN** one keeps it and the other gets a new derived uuid, and the same input always yields the same result

#### Scenario: Unique uuids untouched
- **WHEN** all uuids are already unique
- **THEN** no uuid in the output differs from the input

### Requirement: Garbage collection
Every written MVR SHALL omit mesh and GDTF files no member references, files with duplicate content under another name (references SHALL be re-pointed to the kept file), and stray files such as backups.

#### Scenario: Duplicate mesh content
- **WHEN** two mesh files have identical bytes
- **THEN** one is written and both members reference it

### Requirement: Normalization is idempotent
Writing a file that was already normalized SHALL produce an output equal to it.

#### Scenario: Second pass
- **WHEN** a command's output is passed through a no-op command
- **THEN** the result equals that output
