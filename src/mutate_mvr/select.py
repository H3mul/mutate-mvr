"""Deterministic member ids and selection (shared by info, merge, isolate, delete)."""
from .model import KINDS, MvrError, drop, kind


def assign_ids(scene):
    """{element: id}: per kind, numbered from 1 in (name, uuid) order."""
    ids = {}
    for k, prefix in KINDS.items():
        els = sorted(scene.members(k), key=lambda e: (e.get("name", ""), e.get("uuid", "")))
        for i, e in enumerate(els, 1):
            ids[e] = f"{prefix}{i}"
    return ids


def label(ids, el):
    return f"{ids[el]} '{el.get('name', '')}'"


def resolve(scene, tokens, strict=True):
    """Elements for selector tokens (ids, comma separated allowed). Returns (elements, unmatched)."""
    by_id = {v: k for k, v in assign_ids(scene).items()}
    toks = [t for tok in tokens for t in tok.split(",") if t]
    found = [by_id[t] for t in toks if t in by_id]
    unmatched = [t for t in toks if t not in by_id]
    if strict and unmatched:
        raise MvrError(f"selector matches no member: {', '.join(unmatched)}")
    return found, unmatched


def keep_set(scene, selected):
    """Selected members + their descendants, ancestors and dependencies (closure)."""
    focus = scene.focus_by_uuid()
    keep, todo = set(), list(selected)
    while todo:
        el = todo.pop()
        if el in keep:
            continue
        keep.add(el)
        keep.update(scene.descendants(el))
        keep.update(scene.ancestors(el))
        todo.extend(scene.deps(el, focus)[0])
    return keep


def prune(scene, keep):
    for m in scene.members():
        if m not in keep:
            drop(m)
