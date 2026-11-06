"""ingest blinderkitten: sync fixture ids, names, patches, types and modes from a .olga into an MVR."""
import posixpath
import re

from ..blinderkitten import read, slug
from ..model import (
    MvrError, Scene, child, fixture_id, is_gdtf, labels, set_address, set_child_text, sub, text_of, unit_number,
)
from ..problems import Problem
from . import Result

SUPPORTED = {"artnet", "sacn"}
POD = re.compile(r"^(?P<head>.*?)(?:\s+(?P<label>[^\d\s]\S*))?\s+(?P<n>\d+)$")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.casefold())


def _pairs(items, what):
    out = {}
    for it in items:
        k, sep, v = it.partition("=")
        if not sep or not k.strip() or not v.strip():
            raise MvrError(f"{what}: expected NAME=VALUE, got '{it}'")
        out[k.strip()] = v.strip()
    return out


def _type_map(args):
    items = list(args.type_map)
    if args.type_map_file:
        try:
            lines = open(args.type_map_file, encoding="utf-8").read().splitlines()
        except OSError as e:
            raise MvrError(f"{args.type_map_file}: {e}")
        items += [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    return _pairs(items, "--type-map")


def find_gdtf(scene, name):
    want = _norm(posixpath.splitext(name)[0] if is_gdtf(name) else name)
    for f in sorted(n for n in scene.files if is_gdtf(n)):
        info = scene.gdtf_info(f)
        if want in {_norm(posixpath.splitext(posixpath.basename(f))[0]), _norm(info["name"]) if info else None}:
            return f
    return None


# the project type a fixture was resolved from lives on the fixture itself, so it travels with it
def stored_type(fx):
    ud = child(fx, "UserData")
    for d in (ud if ud is not None else []):
        if d.get("provider") == "mutate-mvr":
            return text_of(d, "ProjectType")
    return ""


def store_type(fx, name):
    ud = child(fx, "UserData")
    if ud is None:
        ud = sub(fx, "UserData")
    data = next((d for d in ud if d.get("provider") == "mutate-mvr"), None)
    if data is None:
        data = sub(ud, "Data", attrs={"provider": "mutate-mvr", "ver": "1"})
    set_child_text(data, "ProjectType", name)


def _match(proj, fixtures):
    """[(project fixture, mvr fixture, sub index or None)] plus the unmatched on both sides."""
    claimed, out = set(), []
    subs = [p for p in proj.fixtures if p.type and p.type.subs]
    plain = [p for p in proj.fixtures if p not in subs]
    for by_name in (True, False):
        for p in subs:
            for fx in fixtures:
                if fx in claimed:
                    continue
                m = POD.match(fx.get("name", ""))
                if not m or not 1 <= int(m["n"]) <= len(p.type.subs):
                    continue
                if (by_name and m["head"] == p.name) or (not by_name and p.id and fixture_id(fx) == p.id):
                    claimed.add(fx)
                    out.append((p, fx, int(m["n"]), m["label"]))
    for by_name in (False, True):
        for p in plain:
            for fx in fixtures:
                if fx in claimed or any(o[0] is p for o in out):
                    continue
                if (by_name and fx.get("name") == p.name) or (not by_name and p.id and fixture_id(fx) == p.id):
                    claimed.add(fx)
                    out.append((p, fx, None, None))
    return out, [p for p in proj.fixtures if not any(o[0] is p for o in out)], [f for f in fixtures if f not in claimed]


def run(args):
    proj = read(args.olga)
    scene = Scene.load(args.mvr)
    before = labels(scene)
    tmap = _type_map(args)
    overrides = {k: int(v) for k, v in _pairs(args.universe, "--universe").items() if v.lstrip("-").isdigit()}
    if len(overrides) != len(args.universe):
        raise MvrError("--universe: expected INTERFACE=N with an integer N")
    warnings = []

    def warn(kind, msg):
        warnings.append(Problem(kind, msg))

    matches, lost_p, lost_f = _match(proj, scene.members("Fixture"))
    for p in lost_p:
        warn("unmatched-project-fixture", f"project fixture {p.id} '{p.name}' matches no MVR fixture")
    for f in lost_f:
        warn("unmatched-mvr-fixture", f"MVR fixture '{f.get('name')}' matches no project fixture")

    for p, fx, n, label in matches:
        # name: sub-fixture pods keep their ' <label> N' suffix
        new = p.name if n is None else f"{p.name} {label + ' ' if label else ''}{n}"
        fx.set("name", new)
        # id: only fill when absent
        cur = fixture_id(fx)
        if cur == 0 or (args.overwrite_ids and cur != p.id):
            set_child_text(fx, "FixtureIDNumeric", p.id)
        elif cur != p.id:
            warn("fixture-id-differs", f"fixture '{new}': keeping id {cur}, project has {p.id}")
        if n is not None and unit_number(fx) == 0:
            set_child_text(fx, "UnitNumber", n)
        _patch(p, fx, n, new, proj, args, overrides, warn)
        _type(scene, p, fx, n, new, tmap, warn)
    return Result(scene, warnings, before)


def _patch(p, fx, n, new, proj, args, overrides, warn):
    patch = next((x for x in p.patches if x.enabled), None)
    if patch is None:
        return warn("no-patch", f"project fixture '{p.name}' has no enabled patch; address of '{new}' unchanged")
    iface = proj.interfaces.get(patch.interface)
    if iface is None or iface.dmx_type not in SUPPORTED:
        return warn("unsupported-interface", f"'{new}': interface '{patch.interface}' ({iface.dmx_type if iface else 'unknown'}) is not Art-Net or sACN; address unchanged")
    uni = overrides.get(patch.interface, overrides.get(slug(patch.interface), iface.universe))
    if uni is None:
        return warn("no-universe", f"'{new}': interface '{patch.interface}' has no universe; address unchanged")
    uni += args.universe_offset
    if not 1 <= patch.address <= 512 or uni < 1:
        return warn("bad-patch", f"'{new}': address {patch.address} on universe {uni} is not usable; address unchanged")
    offset = sum(p.type.subs[: n - 1]) if n and p.type else 0
    set_address(fx, (uni - 1) * 512 + patch.address + offset)


def _type(scene, p, fx, n, new, tmap, warn):
    t = p.type
    if t is None:
        return warn("unresolved-type", f"'{new}': project fixture has no known type")
    if t.name in tmap:
        spec = find_gdtf(scene, tmap[t.name])
    elif stored_type(fx) == t.name and text_of(fx, "GDTFSpec") in scene.files:
        spec = text_of(fx, "GDTFSpec")
    else:
        spec = find_gdtf(scene, t.name)
    if spec is None:
        return warn("unresolved-type", f"'{new}': project type '{t.name}' matches no GDTF in the MVR")
    set_child_text(fx, "GDTFSpec", spec)
    store_type(fx, t.name)
    info = scene.gdtf_info(spec)
    want = t.subs[0] if t.subs else t.channels
    modes = [m for m, fp in (info["modes"] if info else {}).items() if fp == want]
    cur = text_of(fx, "GDTFMode")
    if not modes:
        have = sorted((info["modes"] if info else {}).values())
        return warn("no-matching-mode", f"'{new}': no mode of {spec} has {want} channels (modes: {have}); mode '{cur}' kept")
    if len(modes) > 1:
        warn("ambiguous-mode", f"'{new}': several modes of {spec} have {want} channels: {', '.join(modes)}")
    if cur not in modes:
        set_child_text(fx, "GDTFMode", modes[0])
