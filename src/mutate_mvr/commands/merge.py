import hashlib
import posixpath
import uuid
from collections import defaultdict

from .. import identity
from ..model import CONTAINERS, MvrError, Scene, drop, kind, labels, tag
from ..normalize import NS, normalize
from ..problems import Problem, collisions
from ..select import assign_ids, keep_set, prune, resolve
from . import Result


def _where(path, el):
    return "/".join(path + (el.get("name", ""),))


def _import_files(base, src):
    """Copy src files into base; a name clash with different bytes gets a content-hash suffix."""
    rename = {}
    for name, data in src.files.items():
        if name in base.files and base.files[name] != data:
            stem, ext = posixpath.splitext(name)
            rename[name] = f"{stem}_{hashlib.sha1(data).hexdigest()[:8]}{ext}"
        base.files[rename.get(name, name)] = data
    for el, n in list(src.file_refs()):
        if n in rename:
            src.set_ref(el, rename[n])


class _Merger:
    def __init__(self, base, mode, warnings):
        self.base, self.mode, self.warnings = base, mode, warnings
        self.uuids = {m.get("uuid") for m in base.members()}
        self.umap, self.added = {}, []

    def claim_uuids(self, el):
        for m in [el] + self.base.descendants(el):
            u = m.get("uuid") or ""
            if not u or u in self.uuids:
                new = str(uuid.uuid5(NS, f"{u}|{identity.key(self.base, m, ())!r}|merge"))
                self.umap[u] = new
                m.set("uuid", new)
                u = new
            self.uuids.add(u)

    def merge_list(self, dst, src, path):
        base = self.base
        index = {}
        names = defaultdict(list)
        for e in dst:
            if kind(e):
                index.setdefault(identity.key(base, e, path), e)
                names[(kind(e), e.get("name", ""))].append(e)
        for m in [e for e in src if kind(e)]:
            k = kind(m)
            key = identity.key(base, m, path)
            twin = index.get(key)
            if k in CONTAINERS:
                if twin is not None:
                    scl = base.child_list(m)
                    if scl is not None:
                        self.merge_list(base.child_list(twin, create=True), scl, path + (m.get("name", ""),))
                    continue
            elif twin is not None:
                self.umap[m.get("uuid")] = twin.get("uuid")
                continue
            clash = names.get((k, m.get("name", "")), [])
            if clash and k not in CONTAINERS:
                if self.mode == "skip":
                    self.warnings.append(Problem("merge-conflict", f"skipped {k} {_where(path, m)}: same name as an existing member with different content"))
                    continue
                if self.mode == "replace":
                    for c in clash:
                        drop(c)
                    for key2 in [i for i, e in index.items() if e in clash]:
                        del index[key2]
                    names[(k, m.get("name", ""))] = []
                else:
                    self.warnings.append(Problem("merge-conflict", f"{k} {_where(path, m)} added next to an existing member of the same name with different content"))
            dst.append(m)
            self.claim_uuids(m)
            self.added.append(m)
            index[key] = m
            names[(k, m.get("name", ""))].append(m)

    def fix_focus(self):
        for el in self.added:
            for e in el.iter():
                if tag(e) == "Focus" and (e.text or "").strip() in self.umap:
                    e.text = self.umap[e.text.strip()]


def merge_scene(base, src, mode, warnings):
    if src.layers_el is None:
        return
    _import_files(base, src)
    m = _Merger(base, mode, warnings)
    # ponytail: source AUXData (symbol definitions) is not merged; add if sources use symbols
    m.merge_list(base.ensure_layers(), src.layers_el, ())
    m.fix_focus()


def run(args):
    base = Scene.load(args.files[0])
    before = labels(base)
    normalize(base)
    sources = [Scene.load(p) for p in args.files[1:]]
    warnings, unmatched = [], None
    for src in sources:
        if args.select:
            sel, un = resolve(src, args.select, strict=False)
            unmatched = set(un) if unmatched is None else unmatched & set(un)
            prune(src, keep_set(src, sel))
        normalize(src)
        merge_scene(base, src, args.on_conflict, warnings)
    if unmatched:
        raise MvrError(f"selector matches no member in any source: {', '.join(sorted(unmatched))}")
    normalize(base)
    warnings += collisions(base, assign_ids(base))
    return Result(base, warnings, before)
