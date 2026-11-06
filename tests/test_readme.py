"""Runs every `mutate-mvr ...` line in README.md against synthetic files named as the README names them."""
import shlex
import shutil
from pathlib import Path

from mutate_mvr.cli import main
from helpers import fixture, group, layer, make_mvr, obj
from test_ingest import FILES, OLGA, POCKET

README = Path(__file__).parent.parent / "README.md"


def test_readme_commands_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    files = {**FILES, "a.glb": b"a", "b.glb": b"b"}
    make_mvr("stage.mvr", [layer("Lights", fixture("MHead Wall CR 1", POCKET, "11ch", fid=1)),
                           layer("Set", group("Wall", obj("Box"), obj("Brace", mesh="b.glb")))], files)
    make_mvr("wall.mvr", [layer("Set", obj("Extra", mesh="b.glb"))], files)
    shutil.copy(OLGA, "show.olga")
    cmds = [ln.strip() for ln in README.read_text().splitlines() if ln.strip().startswith("mutate-mvr ")]
    assert len(cmds) >= 10
    for cmd in cmds:
        assert main(shlex.split(cmd)[1:]) == 0, cmd
