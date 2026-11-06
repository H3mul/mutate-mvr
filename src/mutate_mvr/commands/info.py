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


def _line(n):
    s = f"{n['id']} {n['name']}"
    if n["kind"] in ("SceneObject", "FocusPoint") and n["meshes"]:
        s += f"  [{', '.join(n['meshes'])}]"
    if n["kind"] == "Fixture":
        addr = f"{n['address']} (u{n['universe']}.{n['channel']})" if n["address"] else "unpatched"
        s += f"  id={n['fixture_id']} mode={n['mode'] or '-'} addr={addr}"
    return s


def render_text(nodes, depth=0):
    out = []
    for n in nodes:
        out.append("  " * depth + _line(n))
        out += render_text(n["children"], depth + 1)
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
