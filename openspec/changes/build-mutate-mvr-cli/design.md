# Design

## Context

Starting from an empty repository. MVR input is a zip with `GeneralSceneDescription.xml` (layers, groups, scene objects, fixtures, focus points) plus referenced `.glb` meshes and `.gdtf` files. Real exports from Blender/StageViz carry repeated objects, repeated or empty uuids, `_1.glb` copies, empty stub meshes and stray backups; the tool exists to tame these. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- One load, select, transform, normalize, write pipeline shared by `merge`, `isolate` and `delete`.
- Deterministic and idempotent output so repeated runs are safe.
- Faithful XML round trip: unknown elements and attributes survive untouched.

**Non-Goals:**
- Editing geometry, transforms or GDTF contents.
- Computing or assigning patches (that stays with the lighting console project).
- Full MVR schema validation.

## Decisions

- **Pipeline.** Each command builds a `Scene` (lxml tree plus a file table keyed by archive name), applies its transform, then runs `normalize(scene)` before writing. Alternative considered: per-command cleanup; rejected because the same bugs reappeared in every hand fix.
- **lxml, not ElementTree.** Keeps namespaces, attribute order and unknown elements intact on round trip, and gives parent pointers for the reference graph. Cost: one compiled dependency.
- **Content identity, not uuid** (see mvr-model). uuids are regenerated on every export, so they cannot match a re-exported member. Identity keys are computed once per member and cached.
- **Deterministic uuid repair.** Keep a unique uuid; on collision use `uuid5(namespace, old_uuid + content key + occurrence index)`. Alternative: regenerate all uuids, which breaks idempotence and external references.
- **Ids for selection.** `info` sorts members by (name, uuid) per kind and numbers from 1 with a prefix. Selection resolves ids with the same function on the same file, so list-then-select always agrees. Ids are valid only against the file they were listed from.
- **Selection as a set of member nodes plus closure.** `isolate` keeps selected nodes, ancestors and dependencies; `delete` is `isolate` with the selection inverted, then dangling references are cleared with a warning.
- **Warnings as data.** Operations return a list of `Problem` records; the CLI prints them as warnings, and `info --problems` prints the same records for a file. One source for both, so they cannot drift.
- **CLI.** `argparse` with subparsers: zero dependencies, enough for four commands. Alternative: click or typer; rejected as unneeded.
- **Ingest as a pure mapping step.** `ingest blinderkitten` parses the `.olga` JSON into plain fixture records (id, name, type, sub-fixtures, patch interface and universe, channel count) and applies them to the `Scene` like any other transform, then normalizes. Universes come from `containers.artNet.containers.output` `/universe` (the sACN equivalent is verified at implementation time); fixture types have no numeric id in the project, so the type name is the key stored in the MVR. Alternative considered: importing via BlinderKitten's own fixture-type export; rejected because the `.olga` is the artifact in hand.
- **Layout.** `src/mutate_mvr/` with `model.py` (load, write, graph), `identity.py`, `normalize.py`, `select.py`, `problems.py`, `commands/{info,merge,isolate,delete,ingest_blinderkitten}.py`, `blinderkitten.py` (olga reader) and `cli.py`; tests in `tests/` build small synthetic MVRs in code.

## Risks / Trade-offs

- [Content identity treats a moved object as a different member] -> matrix is part of identity on purpose; a moved object is a conflict and is warned about.
- [Large meshes make hashing slow] -> hash once per archive file and cache by name and size.
- [Selectors by id are unstable across edits] -> ids are documented as per-file and the `info` to `--select` workflow is the supported path.
- [Unrecognized MVR elements (e.g. custom AUXData)] -> kept verbatim and counted as non-members; dropped only with their parent.
- [`--in-place` data loss] -> a backup file is written beside the input before any rewrite.

## Open Questions

- Sub-fixture pods all carry the same project fixture id. Recommended: record the sub-fixture index in `UnitNumber` and treat (id, unit) as the collision key, to avoid permanent collision warnings. Not specified yet.
- Where in the MVR the remembered project type is stored (fixture-level custom data vs a root `UserData` entry keyed by fixture uuid); settled against the MVR 1.6 schema during implementation.
- Whether `info` should also accept `--select` to preview what an `isolate` or `delete` would keep (can be added later without changing the specs).
