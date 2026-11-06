# Spec Delta

## Purpose

Combines members, groups and patches from one or more source MVRs onto a base MVR in a single repeatable operation, covering both syncing into an existing target and merging several files into a new one.

## ADDED Requirements

### Requirement: Merge onto a base
`merge BASE [SOURCE ...] -o OUT` SHALL write OUT containing everything in BASE plus the members, groups and patches of each SOURCE, applied in the order given.

#### Scenario: Merge several files
- **WHEN** `merge a.mvr b.mvr c.mvr -o out.mvr` runs
- **THEN** out.mvr holds the members of a, then b, then c, with a as the base

#### Scenario: Sync into an existing target
- **WHEN** the target file is passed as BASE and a source as SOURCE
- **THEN** the output holds the target's members plus the source's new members

### Requirement: Selecting source members
With `--select SEL`, `merge` SHALL take only the selected members, with their ancestors and dependencies, from the sources; selectors are the ids printed by `info` on each source.

#### Scenario: One member from a source
- **WHEN** `merge base.mvr wall.mvr --select o3 -o out.mvr` runs and o3 is an object in wall.mvr
- **THEN** only that object, its group and layer shell, and its mesh are added to base

### Requirement: Identical members are deduplicated
When an incoming member has the same content identity as one already present, `merge` SHALL keep one copy and add nothing.

#### Scenario: Merging the same file twice
- **WHEN** `merge a.mvr a.mvr -o out.mvr` runs
- **THEN** out.mvr has the same members as a.mvr

### Requirement: Conflicting members are added with a warning
When an incoming member has the same layer and name as an existing member but different content, `merge` SHALL add it alongside the existing one and print a warning naming both. `--on-conflict replace` SHALL replace the existing member and `--on-conflict skip` SHALL drop the incoming one.

#### Scenario: Same name, different mesh
- **WHEN** a source object shares a layer and name with a base object but has different mesh bytes
- **THEN** both are present in the output and a warning names them

#### Scenario: Explicit replace
- **WHEN** the same merge runs with `--on-conflict replace`
- **THEN** the base object is replaced by the source object and no duplicate remains

### Requirement: Patch and fixture id collisions are reported, not resolved
`merge` SHALL write incoming fixtures with the fixture ids and addresses they carry, and SHALL warn about each fixture id collision and address overlap the result contains.

#### Scenario: Colliding fixture id
- **WHEN** an incoming fixture has the same non-zero `FixtureIDNumeric` as a different base fixture
- **THEN** both are written unchanged and a warning names the id and both fixtures

#### Scenario: Unassigned ids are not collisions
- **WHEN** incoming and base fixtures all have `FixtureIDNumeric` 0
- **THEN** no fixture id collision warning is printed

#### Scenario: Legacy string id preserved
- **WHEN** an incoming fixture has a `FixtureID` string
- **THEN** the string is written unchanged

### Requirement: Merge is idempotent
Running the same merge again on its own output with the same sources SHALL produce an output equal to its input.

#### Scenario: Repeated merge
- **WHEN** `merge out.mvr b.mvr -o out2.mvr` runs after `merge a.mvr b.mvr -o out.mvr`
- **THEN** out2.mvr is equal to out.mvr
