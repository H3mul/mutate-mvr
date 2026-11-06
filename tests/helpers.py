"""Build small synthetic MVRs in code."""
import io
import itertools
import zipfile
from pathlib import Path

from lxml import etree

IDENT = "{1,0,0}{0,1,0}{0,0,1}{0,0,0}"
_n = itertools.count(1)


def _uuid():
    return f"{next(_n):08x}-0000-4000-8000-000000000000"


def gdtf(modes=None, name="Fix"):
    modes = modes or {"Mode": 8}
    dm = "".join(
        f'<DMXMode Name="{m}"><DMXChannels>'
        + "".join(f'<DMXChannel Offset="{i}"/>' for i in range(1, n + 1))
        + "</DMXChannels></DMXMode>"
        for m, n in modes.items()
    )
    xml = f'<GDTF><FixtureType Name="{name}"><DMXModes>{dm}</DMXModes></FixtureType></GDTF>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("description.xml", xml)
    return buf.getvalue()


def obj(name, mesh="a.glb", uuid=None, matrix=IDENT):
    return (f'<SceneObject uuid="{uuid if uuid is not None else _uuid()}" name="{name}"><Matrix>{matrix}</Matrix>'
            f'<Geometries><Geometry3D fileName="{mesh}"/></Geometries></SceneObject>')


def focus(name, uuid, matrix=IDENT):
    return f'<FocusPoint uuid="{uuid}" name="{name}"><Matrix>{matrix}</Matrix></FocusPoint>'


def fixture(name, gdtf="f.gdtf", mode="Mode", addr=1, fid=0, focus=None, uuid=None, unit=None, matrix=IDENT):
    return (f'<Fixture uuid="{uuid if uuid is not None else _uuid()}" name="{name}"><Matrix>{matrix}</Matrix>'
            f"<GDTFSpec>{gdtf}</GDTFSpec><GDTFMode>{mode}</GDTFMode>"
            + (f'<Addresses><Address break="0">{addr}</Address></Addresses>' if addr else "")
            + f"<FixtureIDNumeric>{fid}</FixtureIDNumeric>"
            + (f"<UnitNumber>{unit}</UnitNumber>" if unit else "")
            + (f"<Focus>{focus}</Focus>" if focus else "") + "</Fixture>")


def group(name, *children, uuid=None, matrix=IDENT):
    return (f'<GroupObject uuid="{uuid if uuid is not None else _uuid()}" name="{name}"><Matrix>{matrix}</Matrix>'
            f'<ChildList>{"".join(children)}</ChildList></GroupObject>')


def layer(name, *children, uuid=None):
    return f'<Layer uuid="{uuid if uuid is not None else _uuid()}" name="{name}"><ChildList>{"".join(children)}</ChildList></Layer>'


def make_mvr(path, layers, files=None):
    xml = ('<GeneralSceneDescription verMajor="1" verMinor="6"><UserData/><Scene><Layers>'
           + "".join(layers) + "</Layers></Scene></GeneralSceneDescription>")
    etree.fromstring(xml)  # fail early on bad test XML
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("GeneralSceneDescription.xml", xml)
        for n, data in (files or {}).items():
            z.writestr(n, data)
    return Path(path)


def read(path):
    """(c14n scene xml, {file: bytes}) for comparing archives."""
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    xml = files.pop("GeneralSceneDescription.xml")
    return etree.tostring(etree.fromstring(xml), method="c14n"), files
