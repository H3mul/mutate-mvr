# Spec Delta

## Purpose

Defines how mutate-mvr reads and writes an MVR archive and what it treats as a member, a member's identity, and a reference between members, so every command works on the same model.

## ADDED Requirements

### Requirement: Read and write MVR archives
The tool SHALL read an MVR as a zip holding `GeneralSceneDescription.xml` plus the mesh and GDTF files it references, and SHALL write a valid MVR zip that keeps every file the scene still references.

#### Scenario: Round trip without changes
- **WHEN** a file is loaded and written with no operation applied
- **THEN** the output scene description is semantically equal to the input and every referenced file is present

#### Scenario: Unreadable input
- **WHEN** the input is not a zip or has no `GeneralSceneDescription.xml`
- **THEN** the tool exits non-zero with a message naming the file and the problem

### Requirement: Member kinds
The tool SHALL model layers, groups, scene objects, fixtures and focus points as members, with layers and groups able to contain other members.

#### Scenario: Nested member
- **WHEN** a scene object sits inside a group inside a layer
- **THEN** it is addressable as a member whose ancestors are that group and that layer

### Requirement: Content identity
The tool SHALL identify members by content, never by uuid: a scene object by its layer path, name, matrix and the hash of its geometry bytes; a fixture by its name, GDTF spec, GDTF mode and matrix; a GDTF or mesh file by the hash of its bytes. A fixture's address SHALL NOT be part of its identity.

#### Scenario: Same object re-exported
- **WHEN** two files hold an object with the same layer, name, matrix and mesh bytes but different uuids
- **THEN** the tool treats them as the same member

#### Scenario: Re-patched fixture
- **WHEN** two fixtures differ only in address
- **THEN** the tool treats them as the same member

### Requirement: Reference graph
The tool SHALL track references between members and files: a fixture to its focus point and GDTF file, a scene object to its mesh files, and any member to its parent group and layer.

#### Scenario: Fixture dependencies
- **WHEN** a fixture references a focus point and a GDTF file
- **THEN** both appear as dependencies of that fixture in the reference graph
