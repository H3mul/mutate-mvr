# Proposal

## Why

MVR files exported from Blender/BlenderDMX and edited in StageViz accumulate duplicate objects, duplicate uuids, duplicate or empty meshes and stale patches. Combining pieces of several exports (a back wall from one, a re-patched fixture set from another) currently means unzipping, hand-editing `GeneralSceneDescription.xml` with regexes, and re-zipping, which is slow and error-prone. A small CLI that lists members, merges, isolates and deletes them, and always leaves a clean file, removes that manual loop.

## What Changes

- New Python project `mutate-mvr` with console script `mutate-mvr [global flags] <info|merge|isolate|delete|ingest> [command flags]`.
- `info [objects|fixtures|patches|all] FILE` prints a pretty tree of members (geometry, fixtures, groups) with sequential, deterministic ids; `--problems` lists integrity problems.
- `merge BASE [SOURCE ...] -o OUT` merges members, groups and patches from the sources onto the first file; the same command covers "sync into an existing target" and "merge N files into a new one".
- `isolate FILE -o OUT --select SEL ...` keeps only the selection; `delete` removes the selection and keeps everything else. Both clean up unreferenced meshes, GDTFs and patches.
- `ingest blinderkitten FILE.olga --mvr MVR -o OUT` syncs fixture ids, names and patches from a BlinderKitten project into an MVR, resolving universes, fixture types and GDTF modes.
- Every write goes through one normalize pass: dedupe identical members, make uuids unique, garbage-collect unreferenced files.
- The tool does what it is asked and warns; warnings are also reported by `info --problems`, and `--strict` turns them into a failing exit code.

## Capabilities

### New Capabilities
- `mvr-model`: reading and writing an MVR archive, member identity, and the reference graph between members.
- `mvr-info`: member listing with deterministic ids, tree output, JSON output, and the `--problems` report.
- `mvr-merge`: merging members, groups and patches from sources onto a base, and conflict handling.
- `mvr-isolate-delete`: keeping or removing a selection with reference closure and cleanup.
- `mvr-integrity`: deduplication, uuid uniqueness and garbage collection applied on every write.
- `blinderkitten-ingest`: syncing fixture ids, names, patches, types and modes from a `.olga` project into an MVR.
- `cli-conventions`: global flags, output safety, warning and exit-code behavior.

### Modified Capabilities

None; this is a new project.

## Impact

- New repository contents: `pyproject.toml`, `src/mutate_mvr/`, `tests/`.
- Dependencies: `lxml` (runtime), `pytest` (dev). CLI parsing uses stdlib `argparse`.
- No existing code or APIs are affected. Tests use small synthetic MVRs built in code, not the real stage files.
