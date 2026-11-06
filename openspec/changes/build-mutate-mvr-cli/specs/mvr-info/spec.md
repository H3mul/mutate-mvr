# Spec Delta

## Purpose

Lets a user list the members of an MVR as a readable tree with stable ids, and see every integrity problem in one report, so selections for other commands are made from what `info` printed.

## ADDED Requirements

### Requirement: Info scopes
`info [objects|fixtures|patches|all] FILE` SHALL print the members of the chosen scope as a tree, defaulting to `all`: objects show layers, groups and scene objects with their meshes; fixtures show fixtures under their groups; patches show each fixture with its absolute address and universe.

#### Scenario: Fixtures scope
- **WHEN** `info fixtures stage.mvr` runs
- **THEN** only fixtures and their ancestor groups are printed, each with name, id, GDTF mode and address

#### Scenario: Default scope
- **WHEN** `info stage.mvr` runs with no scope
- **THEN** the output is the same as `info all stage.mvr`

### Requirement: Deterministic member ids
`info` SHALL assign each member a sequential id with a kind prefix (`o` objects, `f` fixtures, `g` groups, `l` layers), numbered from 1 in order of name and then uuid, so the same file always prints the same ids.

#### Scenario: Stable ids
- **WHEN** `info` runs twice on the same file
- **THEN** every member has the same id both times

#### Scenario: Ids are per file
- **WHEN** two files are listed
- **THEN** each file's ids are assigned independently of the other

### Requirement: Problems report
`info --problems` SHALL list every integrity problem found: duplicate uuids, duplicate members, unreferenced, empty or duplicate-content mesh files, unreferenced GDTF files, dangling references, fixture id collisions and address overlaps. Each problem SHALL name the affected members by id.

#### Scenario: Address overlap
- **WHEN** two fixtures occupy overlapping DMX channels in the same universe
- **THEN** the report lists the overlap with both fixture ids and the channel range

#### Scenario: Clean file
- **WHEN** a file has none of the listed problems
- **THEN** the report says no problems were found and the exit code is 0

### Requirement: Fixture id semantics
The tool SHALL treat `FixtureIDNumeric` as the integer fixture id, with `0` meaning unassigned, and SHALL treat `FixtureID` as an opaque string kept verbatim and never parsed as a number. Fixture id collisions SHALL be detected only between fixtures with the same non-zero `FixtureIDNumeric`.

#### Scenario: Unassigned ids do not collide
- **WHEN** several fixtures all have `FixtureIDNumeric` 0
- **THEN** the problems report lists no fixture id collision for them

#### Scenario: Real collision
- **WHEN** two fixtures have `FixtureIDNumeric` 9
- **THEN** the problems report lists the collision with both fixture ids

#### Scenario: Non-numeric legacy id
- **WHEN** a fixture has `FixtureID` `A12` and `FixtureIDNumeric` 0
- **THEN** `A12` is shown and preserved unchanged and no problem is reported

### Requirement: Machine-readable output
With `--format json`, `info` SHALL print the same tree and problems as one JSON document.

#### Scenario: JSON tree
- **WHEN** `info --format json stage.mvr` runs
- **THEN** stdout is valid JSON containing each member's id, kind, name, uuid and children
