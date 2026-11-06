from ..model import Scene, labels
from ..select import keep_set, prune, resolve
from . import Result


def run(args):
    scene = Scene.load(args.file)
    before = labels(scene)
    sel, _ = resolve(scene, args.select)
    prune(scene, keep_set(scene, sel))
    return Result(scene, [], before)
