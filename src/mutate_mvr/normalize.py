"""The normalize pass every writing command runs: dedupe, unique uuids, garbage-collect files."""
import hashlib
import posixpath
import uuid
from collections import defaultdict

from . import identity
from .model import CONTAINERS, Scene, drop, is_gdtf, is_mesh, is_stray, kind

NS = uuid.UUID("6f1c2d3e-4b5a-4c6d-8e7f-0a1b2c3d4e5f")


def _dedupe(scene, lst, path):
    seen = {}
    for el in list(lst):
        k = kind(el)
        if not k:
            continue
        key = identity.key(scene, el, path)
        if key not in seen:
            seen[key] = el
        elif k in CONTAINERS:
            dst = scene.child_list(seen[key], create=True)
            src = scene.child_list(el)
            for c in list(src) if src is not None else []:
                dst.append(c)
            drop(el)
        else:
            drop(el)
    for el in list(lst):
        if kind(el) in CONTAINERS:
            cl = scene.child_list(el)
            if cl is not None:
                _dedupe(scene, cl, path + (el.get("name", ""),))


def dedupe(scene):
    if scene.layers_el is not None:
        _dedupe(scene, scene.layers_el, ())


def repair_uuids(scene):
    seen = set()
    for el in scene.members():
        u = el.get("uuid") or ""
        if not u or u in seen:
            base = f"{u}|{identity.key(scene, el)!r}"
            n = 0
            while True:
                u = str(uuid.uuid5(NS, f"{base}|{n}"))
                if u not in seen:
                    break
                n += 1
            el.set("uuid", u)
        seen.add(u)


def gc(scene):
    # duplicate content: re-point references to the smallest name, per file class
    for pred in (is_mesh, is_gdtf):
        by_digest = defaultdict(list)
        for n in scene.files:
            if pred(n):
                by_digest[scene.digest(n)].append(n)
        canon = {n: min(g) for g in by_digest.values() for n in g}
        for el, n in list(scene.file_refs()):
            if canon.get(n, n) != n:
                scene.set_ref(el, canon[n])
    used = scene.referenced_files()
    for n in list(scene.files):
        if (is_mesh(n) or is_gdtf(n)) and n not in used or is_stray(n):
            del scene.files[n]


def normalize(scene):
    dedupe(scene)
    repair_uuids(scene)
    gc(scene)
