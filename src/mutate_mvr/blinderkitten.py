"""Reader for BlinderKitten .olga projects (JSON): fixtures, types, patches, interfaces."""
import json
import re
from dataclasses import dataclass, field

from .model import MvrError


@dataclass
class Patch:
    interface: str  # interface display name
    address: int
    enabled: bool


@dataclass
class PType:
    name: str
    channels: int  # DMX footprint of the whole type
    subs: list = field(default_factory=list)  # channel count per sub-fixture 1..n; empty without sub-fixtures


@dataclass
class PFixture:
    id: int
    name: str
    type: PType | None
    patches: list


@dataclass
class Interface:
    name: str
    dmx_type: str  # normalized: 'artnet', 'sacn', 'opendmx', ...
    universe: int | None


@dataclass
class Project:
    fixtures: list
    interfaces: dict  # display name -> Interface


def slug(name):
    """BlinderKitten control-address form of a display name: 'ADJ Pocket Pro 13ch' -> 'adjPocketPro13ch'."""
    out, first = [], True
    for word in re.split(r"(\s+)", name.strip()):
        if not word.strip():
            continue
        word = re.sub(r"[^0-9A-Za-z]", "_", word)
        out.append(word.lower() if first else word[0].upper() + word[1:])
        first = False
    return "".join(out)


def _params(node):
    return {p.get("controlAddress"): p.get("value") for p in node.get("parameters", [])}


def _width(bits):
    m = re.match(r"(\d+)", str(bits))
    return int(m.group(1)) // 8 if m else 1


def _type(node):
    chans = (node.get("containers", {}).get("channels") or {}).get("items", [])
    top, per_sub = 0, {}
    for c in chans:
        p = _params(c)
        w = _width(p.get("/resolution", "8bits"))
        top = max(top, int(p.get("/dmxChannel", 0)) + w - 1)
        sid = p.get("/subFixtureID")
        if sid:
            per_sub[int(sid)] = per_sub.get(int(sid), 0) + w
    subs = [per_sub[k] for k in sorted(per_sub)] if len(per_sub) > 1 else []
    return PType(node.get("niceName", ""), top, subs)


def _interface(node):
    dmx = re.sub(r"[^a-z0-9]", "", str(_params(node).get("/dmxType", "")).lower())
    cont = node.get("containers", {})
    uni = None
    for key in ("artNet", "sACN", "sacn"):
        out = (cont.get(key, {}).get("containers", {}).get("output"))
        if out is not None and "/universe" in _params(out):
            uni = int(_params(out)["/universe"])
            break
    return Interface(node.get("niceName", ""), dmx, uni)


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        raise MvrError(f"{path}: not a readable BlinderKitten project: {e}")
    if not isinstance(doc, dict) or "fixture" not in doc:
        raise MvrError(f"{path}: no 'fixture' section; not a BlinderKitten project")
    types = {slug(t["niceName"]): _type(t) for t in doc.get("fixtureType", {}).get("items", [])}
    ifaces = {i["niceName"]: _interface(i) for i in doc.get("interfaces", {}).get("items", [])}
    by_slug = {slug(n): n for n in ifaces}
    fixtures = []
    for f in doc["fixture"].get("items", []):
        p = _params(f)
        patches = []
        for pt in (f.get("containers", {}).get("patch") or {}).get("items", []):
            q = _params(pt)
            ref = str(q.get("/interface", "")).lstrip("/")
            patches.append(Patch(by_slug.get(ref, ref), int(q.get("/address", 0)), bool(q.get("/enabled", True))))
        fixtures.append(PFixture(int(p.get("/id", 0)), p.get("/name", ""), types.get(str(p.get("/fixtureType", "")).lstrip("/")), patches))
    return Project(fixtures, ifaces)
