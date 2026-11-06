# Spec Delta

## Purpose

Lets a user keep only a selection of members from an MVR, or remove a selection and keep the rest, while the result stays consistent and carries no files or patches nothing uses.

## ADDED Requirements

### Requirement: Isolate keeps a selection
`isolate FILE -o OUT --select SEL ...` SHALL write OUT containing only the selected members, their ancestor groups and layers, and everything they reference.

#### Scenario: Keep one fixture
- **WHEN** a fixture is isolated
- **THEN** the output holds that fixture, its group and layer shell, its focus point and its GDTF file, and nothing else

#### Scenario: Selecting a group
- **WHEN** a group is selected
- **THEN** all of its descendants are kept

### Requirement: Delete removes a selection
`delete FILE -o OUT --select SEL ...` SHALL write OUT containing every member except the selected ones and their descendants.

#### Scenario: Delete a group
- **WHEN** a group is deleted
- **THEN** it and every member inside it are absent from the output and all other members are unchanged

### Requirement: Cleanup of unused files and patches
After `isolate` or `delete`, the output SHALL NOT contain mesh files, GDTF files or patches that no remaining member references.

#### Scenario: GDTF no longer used
- **WHEN** the last fixture using a GDTF file is removed
- **THEN** that GDTF file is absent from the output archive

### Requirement: Removing a referenced member warns
When `delete` removes a member that remaining members reference, the tool SHALL still remove it, clear the dangling reference, and print a warning naming the referencing members.

#### Scenario: Delete a focus point
- **WHEN** a focus point targeted by a remaining fixture is deleted
- **THEN** the fixture is kept without a focus reference and a warning names the fixture

### Requirement: Selector errors
A selector that matches no member SHALL cause a non-zero exit before any output is written, naming the unmatched selector.

#### Scenario: Unknown id
- **WHEN** `--select f99` is given and no member has that id
- **THEN** the tool exits non-zero, reports `f99`, and writes no output file
