# mutate-mvr

Merge, isolate, delete and clean up MVR files (Blender/BlenderDMX/StageViz exports) without unzipping anything.

    pip install -e .[dev]
    pytest

Every command that writes an MVR first normalizes it: identical members are deduplicated, uuids made unique
(deterministically), and meshes/GDTFs nothing references (plus duplicate-content copies and stray backups) are dropped.
Warnings go to stderr and the exit code stays 0; `--strict` turns any warning into a failing exit code after writing.

Global flags go before the command: `-v`, `-q`, `--dry-run`, `--format text|json`, `--strict`.
Writing commands need `-o OUT` and refuse to overwrite an input unless `--in-place` is given (a `.bak` is saved beside it).

## Workflow: list, then select

`info` prints every member with an id (`l` layers, `g` groups, `o` objects, `f` fixtures, `p` focus points).
Ids are numbered by name then uuid and are valid only for the file they were printed from. Pass them to `--select`.

    mutate-mvr info stage.mvr
    mutate-mvr info fixtures stage.mvr
    mutate-mvr info patches stage.mvr
    mutate-mvr info --problems stage.mvr
    mutate-mvr --format json info stage.mvr

## merge

Everything in the first file plus the members, groups and patches of the others. Identical members are kept once;
same name with different content is added with a warning (`--on-conflict replace|skip` to choose otherwise).

    mutate-mvr merge stage.mvr wall.mvr -o merged.mvr
    mutate-mvr merge stage.mvr wall.mvr --select o1 -o with-one-object.mvr
    mutate-mvr --dry-run merge stage.mvr wall.mvr --on-conflict replace -o merged.mvr

## isolate / delete

`isolate` keeps the selection with its ancestors and dependencies (focus point, GDTF, meshes); `delete` removes it.
Selecting a group selects everything inside it.

    mutate-mvr isolate stage.mvr --select f1 -o only-f1.mvr
    mutate-mvr delete stage.mvr --select g1 -o without-g1.mvr
    mutate-mvr -v delete stage.mvr --in-place --select o1

## ingest blinderkitten

Copies fixture ids (only where the MVR has none; `--overwrite-ids` to force), names and patches from a BlinderKitten
`.olga` into the matching MVR fixtures (matched by id, then name; sub-fixture pods `<name> pod N` by trailing number),
and picks the GDTF and the mode with the same channel count. Universes come from the Art-Net/sACN interface's output
universe. Options: `--universe-offset N`, `--universe "INTERFACE=N"`, `--type-map "PROJECT TYPE=GDTF NAME"`
(repeatable) and `--type-map-file FILE` (one `A=B` per line). A resolved type is remembered inside the MVR.

    mutate-mvr ingest blinderkitten show.olga --mvr stage.mvr -o patched.mvr
    mutate-mvr ingest blinderkitten show.olga --mvr stage.mvr --universe-offset 1 --type-map "ADJ Pocket Pro 13ch=ADJ@Pocket_Pro@24-03-12_First_Release" -o patched.mvr
