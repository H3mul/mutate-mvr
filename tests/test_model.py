import zipfile

import pytest

from mutate_mvr import identity
from mutate_mvr.model import MvrError, Scene
from mutate_mvr.select import assign_ids
from helpers import fixture, focus, gdtf, group, layer, make_mvr, obj, read

FILES = {"a.glb": b"AAA", "f.gdtf": gdtf()}


def sample(tmp_path):
    return make_mvr(tmp_path / "s.mvr", [layer("L", group("G", obj("Box"), fixture("Fx", focus="fp1"), focus("FP", "fp1")))], FILES)


def test_smoke_zip(tmp_path):
    with zipfile.ZipFile(sample(tmp_path)) as z:
        assert "GeneralSceneDescription.xml" in z.namelist()


def test_round_trip(tmp_path):
    p = sample(tmp_path)
    s = Scene.load(p)
    s.write(tmp_path / "o.mvr")
    assert read(tmp_path / "o.mvr") == read(p)


def test_not_a_zip(tmp_path):
    bad = tmp_path / "bad.mvr"
    bad.write_text("nope")
    with pytest.raises(MvrError, match="bad.mvr"):
        Scene.load(bad)


def test_ancestors_and_deps(tmp_path):
    s = Scene.load(sample(tmp_path))
    fx = s.members("Fixture")[0]
    assert [a.get("name") for a in s.ancestors(fx)] == ["G", "L"]
    fps, files = s.deps(fx)
    assert [f.get("name") for f in fps] == ["FP"] and files == {"f.gdtf"}
    assert s.deps(s.members("SceneObject")[0])[1] == {"a.glb"}


def test_identity(tmp_path):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", obj("Box", uuid="u1"), obj("Box", uuid="u2"), obj("Box", matrix="{9}"),
                                            fixture("F", addr=1), fixture("F", addr=50))], FILES)
    s = Scene.load(a)
    o1, o2, o3 = s.members("SceneObject")
    assert identity.key(s, o1) == identity.key(s, o2)
    assert identity.key(s, o1) != identity.key(s, o3)
    f1, f2 = s.members("Fixture")
    assert identity.key(s, f1) == identity.key(s, f2)


def test_ids_stable(tmp_path):
    s = Scene.load(sample(tmp_path))
    assert sorted(assign_ids(s).values()) == sorted(assign_ids(Scene.load(sample(tmp_path))).values())
