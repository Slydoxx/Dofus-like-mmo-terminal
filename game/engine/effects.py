from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass
class Damage:
	amount: int


@dataclass
class Push:
	distance: int


@dataclass
class BuffAp:
	amount: int
	duration: int


@dataclass
class Charge:
	amount: int


Effect = Union[Damage, Push, BuffAp, Charge]


