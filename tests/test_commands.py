import pytest

from mutate_mvr.cli import main
from mutate_mvr.model import Scene, fixture_address
from helpers import fixture, focus, gdtf, group, layer, make_mvr, obj, read


def names(path, k=None):
    return sorted(m.get("name") for m in Scene.load(path).members(k))


def run(*argv):
    assert main(["-q", *map(str, argv)]) == 0


G = gdtf({"Mode": 4})


def test_merge_three_files(tmp_path):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", obj("A"))], {"a.glb": b"1"})
    b = make_mvr(tmp_path / "b.mvr", [layer("L", obj("B", mesh="b.glb")), layer("M", obj("B2", mesh="b.glb"))], {"b.glb": b"2"})
    c = make_mvr(tmp_path / "c.mvr", [layer("L", group("G", obj("C", mesh="c.glb")))], {"c.glb": b"3"})
    out = tmp_path / "o.mvr"
    run("merge", a, b, c, "-o", out)
    s = Scene.load(out)
    assert [m.get("name") for m in s.members("SceneObject")] == ["A", "B", "C", "B2"]
    assert sorted(s.files) == ["a.glb", "b.glb", "c.glb"]
    assert len(s.members("Layer")) == 2


def test_merge_same_file_twice_and_idempotent(tmp_path):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", obj("A"), fixture("F", addr=5))], {"a.glb": b"1", "f.gdtf": G})
    b = make_mvr(tmp_path / "b.mvr", [layer("L", obj("B", mesh="b.glb"))], {"b.glb": b"2"})
    out, out2, out3 = tmp_path / "o.mvr", tmp_path / "o2.mvr", tmp_path / "o3.mvr"
    run("merge", a, a, "-o", out)
    assert names(out) == names(a)
    run("merge", a, b, "-o", out2)
    run("merge", out2, b, "-o", out3)
    assert read(out3) == read(out2)


def test_sync_into_target(tmp_path):
    target = make_mvr(tmp_path / "t.mvr", [layer("L", obj("A"))], {"a.glb": b"1"})
    src = make_mvr(tmp_path / "s.mvr", [layer("L", obj("A"), obj("New", mesh="n.glb"))], {"a.glb": b"1", "n.glb": b"n"})
    out = tmp_path / "o.mvr"
    run("merge", target, src, "-o", out)
    assert names(out, "SceneObject") == ["A", "New"]


def test_merge_select(tmp_path):
    base = make_mvr(tmp_path / "base.mvr", [layer("Base", obj("X"))], {"a.glb": b"1"})
    wall = make_mvr(tmp_path / "wall.mvr", [layer("W", group("G", obj("o1"), obj("o2", mesh="b.glb"), obj("o3", mesh="c.glb")))], {"a.glb": b"1", "b.glb": b"2", "c.glb": b"3"})
    out = tmp_path / "o.mvr"
    run("merge", base, wall, "--select", "o3", "-o", out)   # o3 = third by name = 'o3'
    s = Scene.load(out)
    assert names(out, "SceneObject") == ["X", "o3"] and [m.get("name") for m in s.members("GroupObject")] == ["G"]
    assert sorted(s.files) == ["a.glb", "c.glb"]
    assert main(["-q", "merge", str(base), str(wall), "--select", "o99", "-o", str(tmp_path / "bad.mvr")]) == 1
    assert not (tmp_path / "bad.mvr").exists()


@pytest.mark.parametrize("mode,expect", [("add", ["Same", "Same"]), ("replace", ["Same"]), ("skip", ["Same"])])
def test_conflict_modes(tmp_path, mode, expect, capsys):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", obj("Same"))], {"a.glb": b"1"})
    b = make_mvr(tmp_path / "b.mvr", [layer("L", obj("Same"))], {"a.glb": b"DIFFERENT"})
    out = tmp_path / "o.mvr"
    assert main(["merge", str(a), str(b), "-o", str(out), "--on-conflict", mode]) == 0
    s = Scene.load(out)
    assert names(out, "SceneObject") == expect
    if mode == "add":
        assert "Same" in capsys.readouterr().err and len(s.files) == 2
    sole = [s.files[o.find(".//{*}Geometry3D").get("fileName")] for o in s.members("SceneObject")]
    assert sole == {"add": [b"1", b"DIFFERENT"], "replace": [b"DIFFERENT"], "skip": [b"1"]}[mode]


def test_merge_collision_warns_and_keeps(tmp_path, capsys):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", fixture("A", fid=9, addr=1))], {"f.gdtf": G})
    b = make_mvr(tmp_path / "b.mvr", [layer("L", fixture("B", fid=9, addr=2, mode="Mode"))], {"f.gdtf": G})
    out = tmp_path / "o.mvr"
    assert main(["merge", str(a), str(b), "-o", str(out)]) == 0
    err = capsys.readouterr().err
    assert "fixture id 9" in err and "overlap" in err
    assert [fixture_address(f) for f in Scene.load(out).members("Fixture")] == [1, 2]


def test_merge_focus_uuid_remap(tmp_path):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", focus("FP", "same"))], {})
    b = make_mvr(tmp_path / "b.mvr", [layer("M", focus("FP2", "same"), fixture("F", focus="same"))], {"f.gdtf": G})
    out = tmp_path / "o.mvr"
    run("merge", a, b, "-o", out)
    s = Scene.load(out)
    fx = s.members("Fixture")[0]
    fps, _ = s.deps(fx)
    assert [f.get("name") for f in fps] == ["FP2"]


def rig(tmp_path):
    return make_mvr(tmp_path / "rig.mvr", [
        layer("Lights", group("Wash", fixture("F1", fid=1, focus="fp1"), fixture("F2", gdtf="g.gdtf", addr=20)), focus("FP", "fp1")),
        layer("Set", obj("Wall", mesh="wall.glb"), obj("Floor", mesh="floor.glb")),
    ], {"f.gdtf": G, "g.gdtf": gdtf({"Mode": 4}, name="Other"), "wall.glb": b"w", "floor.glb": b"f"})


def test_isolate_one_fixture(tmp_path):
    out = tmp_path / "o.mvr"
    run("isolate", rig(tmp_path), "-o", out, "--select", "f1")
    s = Scene.load(out)
    assert [(m.tag, m.get("name")) for m in s.members()] == [("Layer", "Lights"), ("GroupObject", "Wash"), ("Fixture", "F1"), ("FocusPoint", "FP")]
    assert sorted(s.files) == ["f.gdtf"]


def test_isolate_group_keeps_descendants(tmp_path):
    out = tmp_path / "o.mvr"
    run("isolate", rig(tmp_path), "-o", out, "--select", "g1")
    assert names(out, "Fixture") == ["F1", "F2"] and not names(out, "SceneObject")


def test_delete_group_and_cleanup(tmp_path):
    out = tmp_path / "o.mvr"
    run("delete", rig(tmp_path), "-o", out, "--select", "g1")
    s = Scene.load(out)
    assert not s.members("Fixture") and names(out, "SceneObject") == ["Floor", "Wall"]
    assert sorted(s.files) == ["floor.glb", "wall.glb"]   # both gdtf files gone


def test_delete_referenced_focus_point_warns(tmp_path, capsys):
    out = tmp_path / "o.mvr"
    assert main(["delete", str(rig(tmp_path)), "-o", str(out), "--select", "p1"]) == 0
    assert "F1" in capsys.readouterr().err
    s = Scene.load(out)
    assert not s.members("FocusPoint") and "Focus" not in {c.tag for f in s.members("Fixture") for c in f}


def test_unknown_selector_writes_nothing(tmp_path, capsys):
    out = tmp_path / "o.mvr"
    assert main(["isolate", str(rig(tmp_path)), "-o", str(out), "--select", "f99"]) == 1
    assert "f99" in capsys.readouterr().err and not out.exists()
