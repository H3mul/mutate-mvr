import json

import pytest

from mutate_mvr.cli import main
from mutate_mvr.model import Scene
from helpers import fixture, focus, gdtf, group, layer, make_mvr, obj, read

FILES = {"a.glb": b"AAA", "f.gdtf": gdtf({"Mode": 4})}


def sample(tmp_path, name="s.mvr"):
    return make_mvr(tmp_path / name, [layer("Stage", group("Wall", obj("Box"), fixture("Spot", fid=3, addr=513, focus="fp")), focus("FP", "fp"))], FILES)


GOLDEN = """l1 Stage
  g1 Wall
    o1 Box  [a.glb]
    f1 Spot  id=3 mode=Mode addr=513 (u2.1)
  p1 FP"""


def test_info_golden_and_stable(tmp_path, capsys):
    p = str(sample(tmp_path))
    assert main(["info", p]) == 0
    out = capsys.readouterr().out.strip()
    assert out == GOLDEN
    main(["info", "all", p])
    assert capsys.readouterr().out.strip() == out


def test_info_scopes(tmp_path, capsys):
    p = str(sample(tmp_path))
    main(["info", "fixtures", p])
    out = capsys.readouterr().out
    assert "f1 Spot" in out and "Box" not in out and "g1 Wall" in out
    main(["info", "patches", p])
    assert capsys.readouterr().out.strip() == "f1 Spot  id=3 mode=Mode addr=513 (u2.1)"


def test_info_json_and_problems(tmp_path, capsys):
    p = str(sample(tmp_path))
    assert main(["--format", "json", "info", "--problems", p]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["tree"][0]["children"][0]["children"][0]["id"] == "o1" and doc["problems"] == []
    assert main(["info", "--problems", p]) == 0
    assert "no problems found" in capsys.readouterr().out


def test_unknown_command(capsys):
    with pytest.raises(SystemExit) as e:
        main(["frobnicate"])
    assert e.value.code != 0
    assert "info" in capsys.readouterr().err


def test_output_equals_input_refused(tmp_path, capsys):
    p = sample(tmp_path)
    before = p.read_bytes()
    assert main(["isolate", str(p), "-o", str(p), "--select", "o1"]) == 1
    assert p.read_bytes() == before


def test_in_place_backup_beside(tmp_path):
    p = sample(tmp_path)
    orig = p.read_bytes()
    assert main(["-q", "delete", str(p), "--in-place", "--select", "o1"]) == 0
    assert (tmp_path / "s.mvr.bak").read_bytes() == orig
    assert not Scene.load(p).members("SceneObject")


def test_dry_run_writes_nothing(tmp_path, capsys):
    p = sample(tmp_path)
    out = tmp_path / "out.mvr"
    assert main(["--dry-run", "delete", str(p), "-o", str(out), "--select", "o1"]) == 0
    assert not out.exists() and "- SceneObject Stage/Wall/Box" in capsys.readouterr().out


def test_strict_fails_after_writing(tmp_path, capsys):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", fixture("A", fid=9, addr=1))], FILES)
    b = make_mvr(tmp_path / "b.mvr", [layer("L", fixture("B", fid=9, addr=100))], FILES)
    out = tmp_path / "o.mvr"
    assert main(["merge", str(a), str(b), "-o", str(out)]) == 0
    assert "fixture id 9" in capsys.readouterr().err
    out2 = tmp_path / "o2.mvr"
    assert main(["--strict", "merge", str(a), str(b), "-o", str(out2)]) == 1
    assert out2.exists()
    capsys.readouterr()
    assert main(["-q", "--strict", "merge", str(a), str(b), "-o", str(tmp_path / "o3.mvr")]) == 1
    assert capsys.readouterr().err == ""


def test_bad_input_message(tmp_path, capsys):
    bad = tmp_path / "bad.mvr"
    bad.write_text("x")
    assert main(["info", str(bad)]) == 1
    assert "bad.mvr" in capsys.readouterr().err


def test_noop_equals_normalized(tmp_path):
    a = make_mvr(tmp_path / "a.mvr", [layer("L", obj("A", uuid="s"), obj("B", uuid="s"))], FILES)
    o1, o2 = tmp_path / "o1.mvr", tmp_path / "o2.mvr"
    main(["merge", str(a), "-o", str(o1)])
    main(["merge", str(o1), "-o", str(o2)])
    assert o1.read_bytes() == o2.read_bytes()
