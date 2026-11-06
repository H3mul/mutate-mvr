# Tasks

## 1. Project scaffold

- [ ] 1.1 Create `pyproject.toml` (src layout, `lxml` dependency, `pytest` dev extra, console script `mutate-mvr`) and verify `pip install -e .[dev]` succeeds and `mutate-mvr --help` runs
- [ ] 1.2 Add a test helper that builds small synthetic MVRs in code (layers, groups, objects with meshes, fixtures with focus points and GDTFs) and verify a smoke test loads one with `zipfile`

## 2. Model and identity (mvr-model)

- [ ] 2.1 Implement archive load/write with a file table and lxml scene tree; verify a round-trip test shows equal XML and all referenced files kept, and a non-zip input exits non-zero with a clear message
- [ ] 2.2 Implement member kinds, ancestor links and the reference graph (fixture to focus point and GDTF, object to meshes); verify tests for dependency lookup
- [ ] 2.3 Implement content identity keys for objects, fixtures and files; verify tests: same content with different uuids matches, address-only difference matches, moved matrix does not

## 3. Normalize (mvr-integrity)

- [ ] 3.1 Implement member dedupe per parent; verify a doubled-layer test collapses to single copies
- [ ] 3.2 Implement deterministic uuid repair; verify colliding and empty uuids are fixed identically across runs and unique uuids are untouched
- [ ] 3.3 Implement garbage collection (unreferenced meshes/GDTFs, duplicate-content meshes re-pointed, stray backups); verify tests incl. second pass equals first (idempotence)

## 4. Problems and info (mvr-info)

- [ ] 4.1 Implement `Problem` records and detectors (duplicate uuids and members, bad meshes, dangling refs, fixture id collisions, address overlaps); verify one test per detector
- [ ] 4.2 Implement deterministic ids and the tree printer for objects, fixtures, patches and all; verify ids are stable across runs and output matches golden text
- [ ] 4.3 Implement `info --problems` and `--format json`; verify the JSON parses and a clean file exits 0

## 5. CLI conventions (cli-conventions)

- [ ] 5.1 Implement `argparse` skeleton with global flags, command routing, `-o` and `--in-place` safety with beside-file backup; verify tests for unknown command, output-equals-input refusal and backup location
- [ ] 5.2 Implement `--dry-run`, `-q`/`-v` and warning collection with `--strict` exit code; verify tests for dry-run writing nothing and strict failing after writing

## 6. Merge (mvr-merge)

- [ ] 6.1 Implement selector parsing and resolution against the `info` ids; verify an unknown id exits non-zero before writing
- [ ] 6.2 Implement merge of base plus sources with dedupe of identical members and merging of groups and patches; verify merge of three files, merge of the same file twice, and sync into a target
- [ ] 6.3 Implement `--select` on sources and `--on-conflict add|replace|skip` with warnings; verify same-name-different-mesh tests for each mode
- [ ] 6.4 Verify collision handling and idempotence: fixture id collision writes both with a warning, and re-merging onto the output equals the output

## 7. Isolate and delete (mvr-isolate-delete)

- [ ] 7.1 Implement `isolate` with ancestor and dependency closure; verify keeping one fixture keeps its group, layer, focus point and GDTF only
- [ ] 7.2 Implement `delete` as the inverted selection with dangling-reference clearing and warnings; verify deleting a group and deleting a referenced focus point
- [ ] 7.3 Verify cleanup after both commands: an unused GDTF, mesh and patch are absent from the output archive

## 8. BlinderKitten ingest (blinderkitten-ingest)

- [ ] 8.1 Implement the `.olga` reader (fixtures, types with channel counts and sub-fixtures, patches, interface universes); verify against a trimmed copy of `concert.olga` in tests
- [ ] 8.2 Implement fixture matching (by id, then name, sub-fixture pods by trailing integer) with unmatched warnings; verify one test per match path
- [ ] 8.3 Implement universe and address mapping with `--universe-offset` and `--universe` overrides and warnings for unsupported interfaces; verify a second-universe and an Open DMX case
- [ ] 8.4 Implement type resolution (name match, `--type-map`, `--type-map-file`), mode resolution by channel count, and remembering the resolved type; verify tests incl. second ingest without a map
- [ ] 8.5 Implement id fill rules (`--overwrite-ids`) and renaming; verify absent, differing and overwrite cases, and that ingesting twice gives an equal file

## 9. Integration and docs

- [ ] 9.1 Add an end-to-end test chaining merge, isolate, delete and ingest on synthetic files and asserting `info --problems` reports none
- [ ] 9.2 Write `README.md` with the list-then-select workflow and one example per command including ingest; verify each documented command runs as written against a synthetic file

## Workflow follow-up

- Archive the change after review.
