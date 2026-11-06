"""Integrity problems as data: one source for warnings and `info --problems`."""
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from . import identity
from .model import (
    CONTAINERS, fixture_address, fixture_id, is_gdtf, is_mesh, kind, text_of, unit_number,
)
from .select import assign_ids, label


@dataclass
class Problem:
    kind: str
    message: str
    members: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def footprint(scene, fx):
    info = scene.gdtf_info(text_of(fx, "GDTFSpec"))
    return max(1, (info or {"modes": {}})["modes"].get(text_of(fx, "GDTFMode"), 1))


def collisions(scene, ids):
    """Fixture id collisions and address overlaps."""
    out = []
    fixtures = scene.members("Fixture")
    by_id = defaultdict(list)
    for f in fixtures:
        if fixture_id(f):
            by_id[(fixture_id(f), unit_number(f))].append(f)  # unit splits sub-fixture pods
    for (fid, _), fs in sorted(by_id.items()):
        if len(fs) > 1:
            out.append(Problem("fixture-id-collision", f"fixture id {fid} used by " + ", ".join(label(ids, f) for f in fs), [ids[f] for f in fs]))
    spans = sorted(
        ((a, a + footprint(scene, f) - 1, f) for f in fixtures if (a := fixture_address(f)) is not None),
        key=lambda s: (s[0], s[1], ids[s[2]]),
    )
    for i, (a1, e1, f1) in enumerate(spans):
        for a2, e2, f2 in spans[i + 1:]:
            if a2 > e1:
                break
            lo, hi = a2, min(e1, e2)
            out.append(Problem("address-overlap", f"{label(ids, f1)} and {label(ids, f2)} overlap on absolute channels {lo}-{hi}", [ids[f1], ids[f2]]))
    return out


def find_problems(scene):
    ids = assign_ids(scene)
    out = []
    members = scene.members()
    by_uuid = defaultdict(list)
    for m in members:
        by_uuid[m.get("uuid") or ""].append(m)
    for u, ms in by_uuid.items():
        if u == "" or len(ms) > 1:
            out.append(Problem("duplicate-uuid", f"uuid {u or '(empty)'} on " + ", ".join(label(ids, m) for m in ms), [ids[m] for m in ms]))
    groups = defaultdict(list)
    for m in members:
        p = scene.parent_member(m)
        groups[(id(p) if p is not None else None, identity.key(scene, m))].append(m)
    for ms in groups.values():
        if len(ms) > 1:
            out.append(Problem("duplicate-member", "identical members: " + ", ".join(label(ids, m) for m in ms), [ids[m] for m in ms]))
    used = scene.referenced_files()
    digests = defaultdict(list)
    for n in sorted(scene.files):
        if is_mesh(n):
            digests[scene.digest(n)].append(n)
            if not scene.files[n]:
                out.append(Problem("empty-mesh", f"mesh file {n} is empty"))
            if n not in used:
                out.append(Problem("unreferenced-mesh", f"mesh file {n} is not referenced"))
        elif is_gdtf(n) and n not in used:
            out.append(Problem("unreferenced-gdtf", f"GDTF file {n} is not referenced"))
    for g in digests.values():
        if len(g) > 1:
            out.append(Problem("duplicate-mesh", "mesh files with identical content: " + ", ".join(g)))
    focus = scene.focus_by_uuid()
    for m in members:
        if kind(m) in CONTAINERS:
            continue
        for e in m.iter():
            if (e.tag.rsplit("}", 1)[-1] if isinstance(e.tag, str) else None) == "Focus" and (e.text or "").strip() not in focus:
                out.append(Problem("dangling-reference", f"{label(ids, m)} references missing focus point {(e.text or '').strip()}", [ids[m]]))
        for n in sorted(scene.deps(m, {})[1]):
            if n not in scene.files:
                out.append(Problem("dangling-reference", f"{label(ids, m)} references missing file {n}", [ids[m]]))
    out += collisions(scene, ids)
    return out
