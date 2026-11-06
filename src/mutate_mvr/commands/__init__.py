from dataclasses import dataclass, field

from ..model import Scene


@dataclass
class Result:
    scene: Scene
    warnings: list = field(default_factory=list)  # list[Problem]
    before: object = None  # model.labels() snapshot of the input, for add/remove summaries
