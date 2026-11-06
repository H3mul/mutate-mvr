"""Content identity keys: members are matched by content, never by uuid."""
from .model import child, kind, tag


def matrix(el):
    m = child(el, "Matrix")
    return "".join(m.text.split()) if m is not None and m.text else ""


def _geoms(scene, el):
    out = []
    for g in el.iter():
        if tag(g) == "Geometry3D" and g.get("fileName"):
            n = g.get("fileName")
            out.append((scene.digest(n) if n in scene.files else n, matrix(g)))
    return tuple(out)


def file_key(scene, name):
    return scene.digest(name) if name in scene.files else name


def key(scene, el, path=None):
    """Hashable identity of member `el`; `path` overrides its container path (for detached members)."""
    k = kind(el)
    name = el.get("name", "")
    path = scene.path(el) if path is None else path
    if k == "Layer":
        return (k, name)
    if k == "GroupObject":
        return (k, path, name, matrix(el))
    if k == "Fixture":
        spec = child(el, "GDTFSpec")
        mode = child(el, "GDTFMode")
        return (
            k, name, file_key(scene, (spec.text or "").strip()) if spec is not None else "",
            (mode.text or "").strip() if mode is not None else "", matrix(el),
        )
    return (k, path, name, matrix(el), _geoms(scene, el))
