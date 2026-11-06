from ..model import Scene, child, drop, labels, tag
from ..problems import Problem
from ..select import assign_ids, label, resolve
from . import Result


def run(args):
    scene = Scene.load(args.file)
    before = labels(scene)
    ids = assign_ids(scene)
    sel, _ = resolve(scene, args.select)
    removed = set(sel)
    for s in sel:
        removed.update(scene.descendants(s))
    focus = scene.focus_by_uuid()
    warnings = []
    for f in scene.members("Fixture"):
        c = child(f, "Focus")
        if f not in removed and c is not None and focus.get((c.text or "").strip()) in removed:
            f.remove(c)
            warnings.append(Problem("dangling-reference", f"fixture {label(ids, f)} lost its focus point (deleted)", [ids[f]]))
    for s in sel:
        if s.getparent() is not None:
            drop(s)
    return Result(scene, warnings, before)
