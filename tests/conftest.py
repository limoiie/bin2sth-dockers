import dataclasses
from typing import Any, Tuple


@dataclasses.dataclass
class Raises:
    exc: Any or Tuple[Any, ...]
    kwargs: dict = dataclasses.field(default_factory=dict)


def case_name(case):
    return case.name
