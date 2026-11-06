import json

from mutate_mvr.cli import main
from mutate_mvr.model import Scene, fixture_address
from helpers import group, layer, make_mvr, obj
from test_ingest import OLGA, TYPE_MAP, rig


def test_merge_isolate_delete_ingest_chain(tmp_path, capsys):
    stage = rig(tmp_path)
    set_ = make_mvr(tmp_path / "set.mvr", [layer("Set", group("Wall", obj("Box", mesh="box.glb")), obj("Floor", mesh="floor.glb"))],
                    {"box.glb": b"b", "floor.glb": b"f"})
    a, b, c, d = (str(tmp_path / n) for n in ("a.mvr", "b.mvr", "c.mvr", "d.mvr"))
    assert main(["-q", "merge", str(stage), str(set_), "-o", a]) == 0
    assert main(["-q", "delete", a, "--select", "g1", "-o", b]) == 0            # drop the Wall group
    assert main(["-q", "isolate", b, "--select", "l1", "-o", c]) == 0           # keep Lights only
    s = Scene.load(c)
    assert [m.get("name") for m in s.members("Layer")] == ["Lights"] and "floor.glb" not in s.files
    assert main(["-q", "ingest", "blinderkitten", str(OLGA), "--mvr", c, "-o", d, *TYPE_MAP]) == 0
    assert fixture_address(Scene.load(d).members("Fixture")[0]) == 1
    capsys.readouterr()
    assert main(["--format", "json", "info", "--problems", d]) == 0
    assert json.loads(capsys.readouterr().out)["problems"] == []
