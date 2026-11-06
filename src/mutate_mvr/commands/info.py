"""info: members as a tree with deterministic ids, plus the problems report."""
import json

from ..model import Scene, fixture_address, fixture_id, kind, text_of
from ..problems import find_problems
from ..select import assign_ids

SCOPES = ("objects", "fixtures", "patches", "all")
OBJECT_KINDS = {"Layer", "GroupObject", "SceneObject", "FocusPoint"}
FIXTURE_KINDS = {"Layer", "GroupObject", "Fixture"}


def _detail(scene, el):
    k = kind(el)
    if k in ("SceneObject", "FocusPoint"):
        return {"meshes": sorted(scene.deps(el, {})[1])}
    if k == "Fixture":
        a = fixture_address(el)
        return {
            "fixture_id": fixture_id(el), "gdtf": text_of(el, "GDTFSpec"), "mode": text_of(el, "GDTFMode"),
            "address": a, "universe": (a - 1) // 512 + 1 if a else None, "channel": (a - 1) % 512 + 1 if a else None,
        }
    return {}


def _node(scene, ids, el, keep):
    node = {"id": ids[el], "kind": kind(el), "name": el.get("name", ""), "uuid": el.get("uuid", ""), **_detail(scene, el), "children": []}
    cl = scene.child_list(el)
    for c in cl if cl is not None and kind(el) in ("Layer", "GroupObject") else []:
        if kind(c) in keep:
            n = _node(scene, ids, c, keep)
            if n["kind"] not in ("Layer", "GroupObject") or n["children"]:
                node["children"].append(n)
    return node


def build_tree(scene, scope="all"):
    ids = assign_ids(scene)
    if scope == "patches":
        fx = [e for e in scene.members("Fixture") if fixture_address(e) is not None]
        fx.sort(key=lambda e: (fixture_address(e), ids[e]))
        return [_node(scene, ids, e, ()) for e in fx]
    keep = {"objects": OBJECT_KINDS, "fixtures": FIXTURE_KINDS}.get(scope, set(OBJECT_KINDS) | {"Fixture"})
    lay = scene.layers_el
    return [_node(scene, ids, e, keep) for e in (lay if lay is not None else []) if kind(e) == "Layer"]


def _cols(n):
    if n["kind"] in ("SceneObject", "FocusPoint"):
        return [f"[{', '.join(n['meshes'])}]"] if n["meshes"] else []
    if n["kind"] == "Fixture":
        addr = f"{n['address']} (u{n['universe']}.{n['channel']})" if n["address"] else "unpatched"
        return [f"id={n['fixture_id']}", f"mode={n['mode'] or '-'}", f"addr={addr}"]
    return []


def _rows(nodes, prefix="", root=True):
    """(left text, kind, detail columns) per node, with box-drawing hierarchy."""
    rows = []
    for i, n in enumerate(nodes):
        last = i == len(nodes) - 1
        branch = "" if root else "└── " if last else "├── "
        rows.append((f"{prefix}{branch}{n['id']}  {n['name']}", n["kind"], _cols(n)))
        rows += _rows(n["children"], prefix if root else prefix + ("    " if last else "│   "), False)
    return rows


def render_text(nodes):
    rows = _rows(nodes)
    left = max((len(r[0]) for r in rows), default=0)
    widths = {}
    for _, k, cols in rows:
        for j, c in enumerate(cols):
            widths[(k, j)] = max(widths.get((k, j), 0), len(c))
    out = []
    for text, k, cols in rows:
        cells = [c.ljust(widths[(k, j)]) for j, c in enumerate(cols)]
        out.append((text.ljust(left) + "  " + "  ".join(cells)).rstrip())
    return out


def run(args):
    """Returns (stdout text, number of problems)."""
    scene = Scene.load(args.file)
    tree = build_tree(scene, args.scope)
    probs = find_problems(scene) if args.problems else []
    if args.format == "json":
        doc = {"tree": tree}
        if args.problems:
            doc["problems"] = [p.to_dict() for p in probs]
        return json.dumps(doc, indent=2), len(probs)
    if args.problems:
        lines = [f"{p.kind}: {p.message}" for p in probs] or ["no problems found"]
        return "\n".join(lines), len(probs)
    return "\n".join(render_text(tree)), 0
