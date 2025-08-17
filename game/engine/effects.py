from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Damage:
	amount: int


@dataclass
class Push:
	amount: int


@dataclass
class BuffAp:
	amount: int
	duration_turns: int


