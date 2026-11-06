import json
from pathlib import Path

import pytest

from mutate_mvr.blinderkitten import read, slug
from mutate_mvr.cli import main
from mutate_mvr.commands.ingest_blinderkitten import find_gdtf
from mutate_mvr.model import Scene, fixture_address, fixture_id, text_of
from mutate_mvr.problems import find_problems
from helpers import fixture, gdtf, layer, make_mvr, read as read_archive

OLGA = Path(__file__).parent / "fixtures" / "concert.olga"
POCKET = "ADJ@Pocket_Pro@24-03-12_First_Release.gdtf"  # file name unrelated to the project type name
FILES = {
    POCKET: gdtf({"11ch": 11, "13ch": 13}, name="Pocket Pro"),
    "Yorkville_LP-LED4X.gdtf": gdtf({"Pod": 8, "Full": 32}, name="Yorkville LP-LED4X 32ch"),
    "Antari Z-350 Fazer 2ch.gdtf": gdtf({"2ch": 2}, name="Hazer"),
    "Channel.gdtf": gdtf({"1ch": 1}, name="Channel"),
}


def rig(tmp_path, name="stage.mvr"):
    """An MVR for concert.olga with deliberately different ids/names/addresses."""
    fx = [
        fixture("PckPro wall RU", POCKET, "11ch", addr=300, fid=1),        # match by id, renamed
        fixture("MHead Wall CR 2", POCKET, "11ch", addr=301),             # match by name, id absent
        fixture("MHead Floor UR", POCKET, "11ch", addr=302, fid=33),      # match by name, id differs
    ]
    for tag in ("DR", "UR", "DL", "UL"):
        fx += [fixture(f"LP-LED4X {tag} pod {k}", "Yorkville_LP-LED4X.gdtf", "Full", addr=400 + k) for k in range(1, 5)]
    fx.append(fixture("Hazer", "Antari Z-350 Fazer 2ch.gdtf", "2ch", addr=500))
    fx += [fixture(f"Key Spot #{k}", "Channel.gdtf", "1ch", addr=600 + k) for k in range(1, 5)]
    return make_mvr(tmp_path / name, [layer("Lights", *fx)], FILES)


def ingest(tmp_path, *extra, mvr=None, olga=OLGA, out="out.mvr", expect=0):
    out = tmp_path / out
    code = main(["ingest", "blinderkitten", str(olga), "--mvr", str(mvr or rig(tmp_path)), "-o", str(out), *extra])
    assert code == expect
    return out


def fixtures(path):
    return {f.get("name"): f for f in Scene.load(path).members("Fixture")}


TYPE_MAP = ("--type-map", "ADJ Pocket Pro 13ch=ADJ@Pocket_Pro@24-03-12_First_Release")


def test_slug_matches_every_project_reference():
    proj = read(OLGA)
    assert all(f.type is not None for f in proj.fixtures)
    assert slug("DMX Universe 0") == "dmxUniverse0" and slug("Yorkville LP-LED4X 32ch") == "yorkvilleLP_LED4X32ch"


def test_basic_ingest(tmp_path):
    out = ingest(tmp_path, *TYPE_MAP)
    fx = fixtures(out)
    assert fixture_id(fx["MHead Wall CR 1"]) == 1 and fixture_address(fx["MHead Wall CR 1"]) == 1   # matched by id
    assert fixture_id(fx["MHead Wall CR 2"]) == 2 and fixture_address(fx["MHead Wall CR 2"]) == 14  # by name, id filled
    assert fixture_id(fx["MHead Floor UR"]) == 33                                                    # differing id kept
    assert [fixture_address(fx[f"LP-LED4X DR pod {k}"]) for k in range(1, 5)] == [79, 87, 95, 103]
    assert [fixture_address(fx[f"Key Spot #{k}"]) for k in range(1, 5)] == [513, 514, 515, 516]      # second universe
    assert text_of(fx["MHead Wall CR 1"], "GDTFMode") == "13ch" and text_of(fx["LP-LED4X UL pod 3"], "GDTFMode") == "Pod"
    assert fixture_id(fx["LP-LED4X UL pod 3"]) == 12
    assert not [p for p in find_problems(Scene.load(out)) if p.kind in ("address-overlap", "fixture-id-collision")]


def test_differing_id_warns_and_overwrite(tmp_path, capsys):
    ingest(tmp_path, *TYPE_MAP)
    assert "keeping id 33, project has 3" in capsys.readouterr().err
    out = ingest(tmp_path, *TYPE_MAP, "--overwrite-ids", out="o2.mvr")
    assert fixture_id(fixtures(out)["MHead Floor UR"]) == 3


def test_unmatched_warnings(tmp_path, capsys):
    mvr = make_mvr(tmp_path / "small.mvr", [layer("L", fixture("Hazer", "Antari Z-350 Fazer 2ch.gdtf", "2ch"), fixture("Stranger", "Channel.gdtf", "1ch"))], FILES)
    out = ingest(tmp_path, mvr=mvr)
    err = capsys.readouterr().err
    assert "project fixture 1 'MHead Wall CR 1' matches no MVR fixture" in err and "MVR fixture 'Stranger'" in err
    assert sorted(fixtures(out)) == ["Hazer", "Stranger"]


def test_sub_fixture_pods_not_collisions(tmp_path):
    f = fixtures(ingest(tmp_path, *TYPE_MAP))
    assert {fixture_id(x) for k, x in f.items() if "DR pod" in k} == {9}


def test_unresolved_type_warns_then_map_and_remembered(tmp_path, capsys):
    ingest(tmp_path)
    assert "'ADJ Pocket Pro 13ch' matches no GDTF" in capsys.readouterr().err
    first = ingest(tmp_path, *TYPE_MAP, out="first.mvr")
    capsys.readouterr()
    second = ingest(tmp_path, mvr=first, out="second.mvr")   # no map: resolved from the stored type
    assert "matches no GDTF" not in capsys.readouterr().err
    assert read_archive(second) == read_archive(first)       # idempotent


def test_type_map_file_and_name_match(tmp_path):
    mf = tmp_path / "map.txt"
    mf.write_text("# comment\nADJ Pocket Pro 13ch = ADJ@Pocket_Pro@24-03-12_First_Release\n")
    out = ingest(tmp_path, "--type-map-file", str(mf))
    assert text_of(fixtures(out)["MHead Wall CR 1"], "GDTFMode") == "13ch"
    assert find_gdtf(Scene.load(out), "Channel") == "Channel.gdtf"


def test_no_matching_mode_keeps_current(tmp_path, capsys):
    mvr = make_mvr(tmp_path / "m.mvr", [layer("L", fixture("Hazer", "Antari Z-350 Fazer 2ch.gdtf", "2ch"))], {"Antari Z-350 Fazer 2ch.gdtf": gdtf({"2ch": 5}, name="Hazer")})
    out = ingest(tmp_path, mvr=mvr)
    assert "no mode of" in capsys.readouterr().err and text_of(fixtures(out)["Hazer"], "GDTFMode") == "2ch"


def edited_olga(tmp_path, edit):
    doc = json.loads(OLGA.read_text())
    edit(doc)
    p = tmp_path / "edited.olga"
    p.write_text(json.dumps(doc))
    return p


def test_unsupported_interface_and_overrides(tmp_path, capsys):
    def edit(doc):
        for p in doc["interfaces"]["items"][1]["parameters"]:
            if p["controlAddress"] == "/dmxType":
                p["value"] = "Open DMX"
    out = ingest(tmp_path, olga=edited_olga(tmp_path, edit))
    assert "DMX Universe 1" in capsys.readouterr().err and fixture_address(fixtures(out)["Key Spot #1"]) == 601
    out = ingest(tmp_path, "--universe", "DMX Universe 0=3", "--universe-offset", "1", out="o3.mvr")
    assert fixture_address(fixtures(out)["MHead Wall CR 1"]) == 3 * 512 + 1       # override 3, +1 offset -> universe 4
    assert fixture_address(fixtures(out)["Key Spot #1"]) == 2 * 512 + 1           # universe 2 + 1 -> 3


def test_unreadable_project(tmp_path, capsys):
    bad = tmp_path / "bad.olga"
    bad.write_text("{not json")
    ingest(tmp_path, olga=bad, expect=1)
    err = capsys.readouterr().err
    assert "bad.olga" in err and not (tmp_path / "out.mvr").exists()
    nofix = tmp_path / "nofix.olga"
    nofix.write_text("{}")
    ingest(tmp_path, olga=nofix, expect=1)
    assert "nofix.olga" in capsys.readouterr().err


def test_ingest_twice_equal(tmp_path):
    first = ingest(tmp_path, *TYPE_MAP)
    second = ingest(tmp_path, *TYPE_MAP, mvr=first, out="second.mvr")
    assert read_archive(second) == read_archive(first)
