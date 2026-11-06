"""MVR archive model: load/write, members, reference graph, GDTF footprints."""
import hashlib
import io
import os
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from lxml import etree

SCENE_XML = "GeneralSceneDescription.xml"
KINDS = {"Layer": "l", "GroupObject": "g", "SceneObject": "o", "Fixture": "f", "FocusPoint": "p"}
CONTAINERS = ("Layer", "GroupObject")
MESH_EXT = (".glb", ".gltf", ".3ds", ".obj")
STRAY_EXT = (".bak", ".orig", ".tmp", ".swp", "~")


class MvrError(Exception):
    pass


def tag(el):
    t = el.tag
    return t.rsplit("}", 1)[-1] if isinstance(t, str) else None


def kind(el):
    t = tag(el)
    return t if t in KINDS else None


def child(el, name):
    for c in el:
        if tag(c) == name:
            return c
    return None


def sub(parent, name, text=None, attrs=None):
    ns = parent.tag.partition("}")[0] + "}" if parent.tag.startswith("{") else ""
    e = etree.SubElement(parent, ns + name, attrs or {})
    if text is not None:
        e.text = text
    return e


def is_mesh(name):
    return name.lower().endswith(MESH_EXT)


def is_gdtf(name):
    return name.lower().endswith(".gdtf")


def is_stray(name):
    return name.lower().endswith(STRAY_EXT)


@dataclass
class Scene:
    root: etree._Element
    files: dict = field(default_factory=dict)
    _digests: dict = field(default_factory=dict, repr=False)
    _gdtf: dict = field(default_factory=dict, repr=False)

    # ---- io
    @classmethod
    def load(cls, path):
        try:
            zf = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as e:
            raise MvrError(f"{path}: not a readable MVR (zip) file: {e}")
        with zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            if SCENE_XML not in names:
                raise MvrError(f"{path}: no {SCENE_XML} in archive")
            files = {n: zf.read(n) for n in names}
        try:
            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            root = etree.fromstring(files.pop(SCENE_XML), parser)
        except etree.XMLSyntaxError as e:
            raise MvrError(f"{path}: invalid {SCENE_XML}: {e}")
        return cls(root, files)

    def to_bytes(self):
        buf = io.BytesIO()
        xml = etree.tostring(self.root, xml_declaration=True, encoding="UTF-8")
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in [(SCENE_XML, xml)] + sorted(self.files.items()):
                zf.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)
        return buf.getvalue()

    def write(self, path):
        tmp = f"{path}.tmp-mutate"
        with open(tmp, "wb") as f:
            f.write(self.to_bytes())
        os.replace(tmp, path)

    # ---- tree access
    @property
    def layers_el(self):
        scene = child(self.root, "Scene")
        return child(scene, "Layers") if scene is not None else None

    def ensure_layers(self):
        if self.layers_el is None:
            scene = child(self.root, "Scene")
            if scene is None:
                scene = sub(self.root, "Scene")
            sub(scene, "Layers")
        return self.layers_el

    def members(self, k=None):
        lay = self.layers_el
        if lay is None:
            return []
        return [e for e in lay.iter() if kind(e) and (k is None or kind(e) == k)]

    def parent_member(self, el):
        p = el.getparent()
        if p is not None and tag(p) == "ChildList":
            p = p.getparent()
        return p if p is not None and kind(p) else None

    def ancestors(self, el):
        out = []
        p = self.parent_member(el)
        while p is not None:
            out.append(p)
            p = self.parent_member(p)
        return out

    def path(self, el):
        return tuple(a.get("name", "") for a in reversed(self.ancestors(el)))

    @staticmethod
    def child_list(el, create=False):
        """The element holding a container's member children."""
        if tag(el) == "Layers":
            return el
        c = child(el, "ChildList")
        if c is None and create:
            c = sub(el, "ChildList")
        return c

    def descendants(self, el):
        return [e for e in el.iter() if e is not el and kind(e)]

    # ---- files
    def digest(self, name):
        data = self.files[name]
        k = (name, len(data))
        if k not in self._digests:
            self._digests[k] = hashlib.sha1(data).hexdigest()
        return self._digests[k]

    def file_refs(self):
        """(element, name) for every mesh/GDTF reference anywhere in the scene document."""
        for e in self.root.iter():
            t = tag(e)
            if t == "Geometry3D" and e.get("fileName"):
                yield e, e.get("fileName")
            elif t == "GDTFSpec" and (e.text or "").strip():
                yield e, e.text.strip()

    @staticmethod
    def set_ref(e, name):
        if tag(e) == "Geometry3D":
            e.set("fileName", name)
        else:
            e.text = name

    def referenced_files(self):
        return {n for _, n in self.file_refs()}

    # ---- reference graph
    def focus_by_uuid(self):
        out = {}
        for f in self.members("FocusPoint"):
            out.setdefault(f.get("uuid"), f)
        return out

    def deps(self, el, focus=None):
        """Dependencies of a member subtree: (focus point elements, file names)."""
        focus = focus if focus is not None else self.focus_by_uuid()
        fps, files = [], set()
        for e in el.iter():
            t = tag(e)
            if t == "Focus" and (e.text or "").strip() in focus:
                fps.append(focus[e.text.strip()])
            elif t == "Geometry3D" and e.get("fileName"):
                files.add(e.get("fileName"))
            elif t == "GDTFSpec" and (e.text or "").strip():
                files.add(e.text.strip())
        return fps, files

    # ---- gdtf
    def gdtf_info(self, name):
        """{'name': FixtureType name, 'modes': {mode: channel footprint}} or None."""
        if name not in self.files:
            return None
        if name not in self._gdtf:
            info = None
            try:
                with zipfile.ZipFile(io.BytesIO(self.files[name])) as zf:
                    root = etree.fromstring(zf.read("description.xml"))
                ft = next(e for e in root.iter() if tag(e) == "FixtureType")
                modes = {}
                for m in (e for e in ft.iter() if tag(e) == "DMXMode"):
                    top = 0
                    for ch in (e for e in m.iter() if tag(e) == "DMXChannel"):
                        for o in (ch.get("Offset") or "").split(","):
                            if o.strip().isdigit():
                                top = max(top, int(o))
                    modes[m.get("Name", "")] = top
                info = {"name": ft.get("Name", ""), "modes": modes}
            except Exception:  # ponytail: unreadable GDTF -> no footprint info, treated as unknown
                pass
            self._gdtf[name] = info
        return self._gdtf[name]


# ---- fixture field helpers
def text_of(el, name, default=""):
    c = child(el, name)
    return (c.text or "").strip() if c is not None and c.text else default


def fixture_id(el):
    t = text_of(el, "FixtureIDNumeric", "0")
    return int(t) if t.lstrip("-").isdigit() else 0


def unit_number(el):
    t = text_of(el, "UnitNumber", "0")
    return int(t) if t.lstrip("-").isdigit() else 0


def _address_els(el):
    a = child(el, "Addresses")
    return [c for c in (a if a is not None else el) if tag(c) == "Address"]


def fixture_address(el):
    """Absolute DMX address of the first break, or None."""
    for a in _address_els(el):
        t = (a.text or "").strip()
        if "." in t:
            u, _, ch = t.partition(".")
            if u.isdigit() and ch.isdigit():
                return (int(u) - 1) * 512 + int(ch)
        elif t.isdigit():
            return int(t)
    return None


def set_address(el, absolute):
    els = _address_els(el)
    if els:
        els[0].text = str(absolute)
        return
    addrs = child(el, "Addresses")
    if addrs is None:
        addrs = sub(el, "Addresses")
    sub(addrs, "Address", str(absolute), {"break": "0"})


def set_child_text(el, name, text):
    c = child(el, name)
    if c is None:
        c = sub(el, name)
    c.text = str(text)


def labels(scene):
    """Counter of 'Kind path/name' strings, for add/remove summaries."""
    return Counter(
        f"{kind(e)} {'/'.join(scene.path(e) + (e.get('name', ''),))}" for e in scene.members()
    )


def drop(el):
    el.getparent().remove(el)
