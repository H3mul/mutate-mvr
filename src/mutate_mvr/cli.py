"""mutate-mvr command line: argparse routing, output safety, warnings and exit codes."""
import argparse
import os
import shutil
import sys

from .model import MvrError, labels
from .normalize import normalize

COMMANDS = ("info", "merge", "isolate", "delete", "ingest")


def build_parser():
    p = argparse.ArgumentParser(prog="mutate-mvr", description="Merge, isolate, delete and clean up MVR files.")
    p.add_argument("-v", "--verbose", action="store_true", help="also print each member added or removed")
    p.add_argument("-q", "--quiet", action="store_true", help="print only errors")
    p.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
    p.add_argument("--format", choices=("text", "json"), default="text", help="output format for info")
    p.add_argument("--strict", action="store_true", help="exit non-zero after writing if any warning was printed")
    sub = p.add_subparsers(dest="command", metavar="{" + ",".join(COMMANDS) + "}", required=True)

    def writing(sp):
        sp.add_argument("-o", "--output", metavar="OUT")
        sp.add_argument("--in-place", action="store_true", help="overwrite the input (a backup is written beside it)")

    i = sub.add_parser("info", help="list members as a tree with ids")
    i.add_argument("scope", nargs="?", choices=("objects", "fixtures", "patches", "all"), default="all")
    i.add_argument("file", metavar="FILE")
    i.add_argument("--problems", action="store_true", help="report integrity problems")

    m = sub.add_parser("merge", help="merge sources onto the first file")
    m.add_argument("files", nargs="+", metavar="BASE [SOURCE ...]")
    m.add_argument("--select", nargs="+", metavar="SEL", help="take only these members (ids from info) from the sources")
    m.add_argument("--on-conflict", choices=("add", "replace", "skip"), default="add")
    writing(m)

    for name, helptext in (("isolate", "keep only the selection"), ("delete", "remove the selection")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("file", metavar="FILE")
        s.add_argument("--select", nargs="+", required=True, metavar="SEL")
        writing(s)

    ing = sub.add_parser("ingest", help="sync fixtures from another project into an MVR")
    isub = ing.add_subparsers(dest="source", metavar="{blinderkitten}", required=True)
    b = isub.add_parser("blinderkitten", help="BlinderKitten .olga project")
    b.add_argument("olga", metavar="FILE.olga")
    b.add_argument("--mvr", required=True, metavar="MVR")
    b.add_argument("--universe-offset", type=int, default=0)
    b.add_argument("--universe", action="append", default=[], metavar="INTERFACE=N")
    b.add_argument("--type-map", action="append", default=[], metavar="'PROJECT TYPE=GDTF NAME'")
    b.add_argument("--type-map-file", metavar="FILE")
    b.add_argument("--overwrite-ids", action="store_true")
    writing(b)
    return p


def _inputs(args):
    if args.command == "merge":
        return args.files
    if args.command == "ingest":
        return [args.mvr]
    return [args.file]


def _backup_path(path):
    n, cand = 0, path + ".bak"
    while os.path.exists(cand):
        n += 1
        cand = f"{path}.bak.{n}"
    return cand


def _diff(before, after):
    return sorted(f"+ {k}" for k in (after - before)), sorted(f"- {k}" for k in (before - after))


def _run_writing(args):
    ins = _inputs(args)
    out = ins[0] if args.in_place else args.output
    if not out:
        raise MvrError("-o OUT is required (or --in-place)")
    if not args.in_place and any(os.path.realpath(out) == os.path.realpath(i) for i in ins + ([args.olga] if args.command == "ingest" else [])):
        raise MvrError(f"output {out} is also an input; choose another -o or pass --in-place")
    if args.command == "merge":
        from .commands import merge as mod
    elif args.command == "ingest":
        from .commands import ingest_blinderkitten as mod
    else:
        mod = __import__(f"mutate_mvr.commands.{args.command}", fromlist=["run"])
    res = mod.run(args)
    normalize(res.scene)
    added, removed = _diff(res.before, labels(res.scene))
    warnings = [w.message for w in res.warnings]
    if args.dry_run:
        for line in added + removed:
            print(line)
        for w in warnings:
            print(f"warning: {w}")
        print(f"dry run: {out} not written")
    else:
        if args.in_place:
            shutil.copy2(out, _backup_path(out))
        res.scene.write(out)
        if args.verbose and not args.quiet:
            for line in added + removed:
                print(line, file=sys.stderr)
        if not args.quiet:
            for w in warnings:
                print(f"warning: {w}", file=sys.stderr)
    return 1 if args.strict and warnings else 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "info":
            from .commands import info
            text, n = info.run(args)
            print(text)
            return 1 if args.strict and n else 0
        return _run_writing(args)
    except MvrError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
