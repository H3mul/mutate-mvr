# Spec Delta

## Purpose

Brings fixture ids, fixture names and patches from a BlinderKitten `.olga` project into an MVR, resolving universes, fixture types and GDTF modes automatically, so the MVR and the lighting console describe the same rig.

## ADDED Requirements

### Requirement: Ingest command
`ingest blinderkitten FILE.olga --mvr MVR -o OUT` SHALL read the project's fixtures and write OUT as MVR with the matched fixtures' ids, names and patches taken from the project, leaving everything else unchanged.

#### Scenario: Basic ingest
- **WHEN** `ingest blinderkitten show.olga --mvr stage.mvr -o out.mvr` runs
- **THEN** out.mvr has the matched fixtures renamed, numbered and patched as in show.olga

#### Scenario: Unreadable project
- **WHEN** the file is not valid JSON or has no `fixture` section
- **THEN** the tool exits non-zero naming the file and writes no output

### Requirement: Fixture matching
The tool SHALL match each project fixture to an MVR fixture by non-zero `FixtureIDNumeric` equal to the project fixture id, otherwise by fixture name, and SHALL warn about each project fixture and each MVR fixture left unmatched, leaving unmatched MVR fixtures unchanged.

#### Scenario: Match by id
- **WHEN** an MVR fixture has `FixtureIDNumeric` 3 and the project has fixture id 3
- **THEN** they are matched even if their names differ

#### Scenario: Match by name
- **WHEN** an MVR fixture has `FixtureIDNumeric` 0 and the same name as a project fixture
- **THEN** they are matched

#### Scenario: Unmatched project fixture
- **WHEN** a project fixture matches no MVR fixture
- **THEN** a warning names it and no MVR fixture is created

### Requirement: Sub-fixtures map to numbered MVR fixtures
A project fixture whose type has sub-fixtures SHALL match the MVR fixtures named after it with a trailing integer N (for example `LP-LED4X DR pod 2`), N selecting sub-fixture N; each such fixture's address SHALL be the fixture's start address plus the channel count of sub-fixtures 1 to N-1.

#### Scenario: Four pods
- **WHEN** a project fixture at address 79 has four 8-channel sub-fixtures and the MVR has pods 1 to 4 named after it
- **THEN** the pods are addressed 79, 87, 95 and 103

### Requirement: Fixture ids only filled when absent
The tool SHALL write the project fixture id into `FixtureIDNumeric` only when the MVR fixture's value is 0. When the MVR value is non-zero and different, the tool SHALL keep it and warn, unless `--overwrite-ids` is given.

#### Scenario: Absent id filled
- **WHEN** a matched MVR fixture has `FixtureIDNumeric` 0
- **THEN** it takes the project fixture id

#### Scenario: Differing id kept
- **WHEN** a matched MVR fixture has `FixtureIDNumeric` 5 and the project id is 7
- **THEN** 5 is kept and a warning names both values

### Requirement: Fixture names from the project
The tool SHALL set each matched MVR fixture's name to the project fixture name, with ` <label> N` kept for sub-fixture fixtures as already named in the MVR.

#### Scenario: Rename
- **WHEN** a matched fixture is named `PckPro wall RU` in the MVR and `MHead Wall CR 1` in the project
- **THEN** the output fixture is named `MHead Wall CR 1`

### Requirement: Universe and address mapping
For each enabled patch with an address from 1 to 512 on an Art-Net or sACN interface, the tool SHALL write the MVR address as `(universe - 1) * 512 + address`, where the universe is the interface's output universe plus `--universe-offset` (default 0). A patch on any other interface type, with no universe, with address 0, or giving a universe below 1 SHALL be left unwritten with a warning, and `--universe INTERFACE=N` SHALL override the universe of a named interface.

#### Scenario: Second universe
- **WHEN** a patch at address 1 is on an Art-Net interface whose output universe is 2
- **THEN** the MVR address is 513

#### Scenario: Unsupported interface
- **WHEN** a patch is on an Open DMX interface
- **THEN** its fixture's address is left unchanged and a warning names the interface

#### Scenario: Explicit override
- **WHEN** `--universe "DMX Universe 0=3"` is given
- **THEN** patches on that interface use universe 3

### Requirement: Fixture type resolution
The tool SHALL resolve each project fixture type to a GDTF in the MVR by matching the type name to the GDTF name, and SHALL accept an explicit map (`--type-map "PROJECT TYPE=GDTF NAME"`, repeatable, or `--type-map-file FILE`) which takes precedence over name matching. An unresolved type SHALL produce a warning and leave that fixture's GDTF unchanged.

#### Scenario: Name match
- **WHEN** a project type and a GDTF in the MVR have the same name
- **THEN** the type resolves to that GDTF

#### Scenario: Explicit map
- **WHEN** `--type-map "ADJ Pocket Pro 13ch=ADJ@Pocket_Pro@24-03-12_First_Release"` is given
- **THEN** that type resolves to the named GDTF regardless of name similarity

### Requirement: Mode resolution by channel count
After a type resolves, the tool SHALL pick the GDTF mode whose channel footprint equals the project type's DMX channel count (or the per-sub-fixture count for types with sub-fixtures). If several modes match it SHALL keep the fixture's current mode when it is among them, else the first, and warn; if none match it SHALL keep the current mode and warn.

#### Scenario: One matching mode
- **WHEN** a project type has 13 DMX channels and a GDTF has modes of 13 and 11 channels
- **THEN** the 13-channel mode is set

#### Scenario: No matching mode
- **WHEN** no GDTF mode has the project type's channel count
- **THEN** the current mode is kept and a warning names the counts

### Requirement: Remember resolved project type
Once a fixture type resolves, the tool SHALL store the project fixture type name in the MVR so a later ingest uses it before name matching, and the stored value SHALL survive merge, isolate and delete of that fixture.

#### Scenario: Second ingest without a map
- **WHEN** a type was resolved with an explicit map on a first ingest and the second ingest has no map
- **THEN** the second ingest resolves it from the stored value

### Requirement: Ingest is idempotent
Running the same ingest on its own output SHALL produce an output equal to its input.

#### Scenario: Repeat ingest
- **WHEN** `ingest blinderkitten show.olga --mvr out.mvr -o out2.mvr` runs after producing out.mvr
- **THEN** out2.mvr equals out.mvr
