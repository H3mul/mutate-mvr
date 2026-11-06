from mutate_mvr.model import Scene
from mutate_mvr.normalize import normalize
from mutate_mvr.problems import find_problems
from helpers import fixture, focus, gdtf, group, layer, make_mvr, obj


def norm(tmp_path, layers, files, name="s.mvr"):
    s = Scene.load(make_mvr(tmp_path / name, layers, files))
    normalize(s)
    return s


def test_doubled_layer_collapses(tmp_path):
    objs = [obj("A", uuid="1"), obj("B", uuid="2")]
    dup = [obj("A", uuid="3"), obj("B", uuid="4")]
    s = norm(tmp_path, [layer("L", *objs, *dup, group("G", obj("C")), group("G", obj("C")))], {"a.glb": b"x"})
    assert [m.get("name") for m in s.members("SceneObject")] == ["A", "B", "C"]
    assert len(s.members("GroupObject")) == 1


def test_uuid_repair_deterministic(tmp_path):
    layers = [layer("L", obj("A", uuid="same"), obj("B", uuid="same"), obj("C", uuid=""), obj("D", uuid="ok"))]
    f = {"a.glb": b"x"}
    u1 = [m.get("uuid") for m in norm(tmp_path, layers, f, "1.mvr").members()]
    u2 = [m.get("uuid") for m in norm(tmp_path, layers, f, "2.mvr").members()]
    assert u1 == u2 and len(set(u1)) == len(u1) and "ok" in u1 and u1.count("same") == 1 and "" not in u1


def test_gc(tmp_path):
    files = {"a.glb": b"AAA", "a_1.glb": b"AAA", "unused.glb": b"zzz", "f.gdtf": gdtf(), "g.gdtf": gdtf(), "x.mvr.bak": b"b"}
    s = norm(tmp_path, [layer("L", obj("A", mesh="a.glb"), obj("B", mesh="a_1.glb"), fixture("F", gdtf="f.gdtf"))], files)
    assert sorted(s.files) == ["a.glb", "f.gdtf"]
    assert {r for _, r in s.file_refs()} == {"a.glb", "f.gdtf"}


def test_idempotent(tmp_path):
    layers = [layer("L", obj("A", uuid="s"), obj("B", uuid="s"), obj("A", uuid="t"))]
    s = norm(tmp_path, layers, {"a.glb": b"x", "b.glb": b"x"})
    first = s.to_bytes()
    normalize(s)
    assert s.to_bytes() == first


def kinds(s):
    return {p.kind for p in find_problems(s)}


def test_detectors(tmp_path):
    f = {"a.glb": b"AAA", "dup.glb": b"AAA", "empty.glb": b"", "orphan.glb": b"q", "f.gdtf": gdtf({"Mode": 4}), "orphan.gdtf": gdtf()}
    layers = [layer("L", obj("A", uuid="u"), obj("B", uuid="u", mesh="dup.glb"), obj("A", uuid="v"), obj("E", mesh="empty.glb"), obj("M", mesh="missing.glb"),
                    fixture("F1", fid=3, addr=10), fixture("F2", fid=3, addr=12, uuid="x2"), fixture("F3", addr=2, focus="nope", uuid="x3"))]
    s = Scene.load(make_mvr(tmp_path / "p.mvr", layers, f))
    assert kinds(s) == {"duplicate-uuid", "duplicate-member", "duplicate-mesh", "empty-mesh", "unreferenced-mesh",
                        "unreferenced-gdtf", "dangling-reference", "fixture-id-collision", "address-overlap"}


def test_unassigned_ids_do_not_collide(tmp_path):
    s = Scene.load(make_mvr(tmp_path / "p.mvr", [layer("L", fixture("A", addr=1), fixture("B", addr=100))], {"f.gdtf": gdtf()}))
    assert not kinds(s) & {"fixture-id-collision", "address-overlap"}


def test_same_address_overlap_does_not_crash(tmp_path):
    s = Scene.load(make_mvr(tmp_path / "p.mvr", [layer("L", fixture("A", addr=5), fixture("B", addr=5))], {"f.gdtf": gdtf()}))
    assert "address-overlap" in kinds(s)
