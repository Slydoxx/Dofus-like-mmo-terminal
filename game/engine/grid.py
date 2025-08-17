from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple


Coord = Tuple[int, int]


@dataclass
class Grid:
	width: int
	height: int
	blocked: Set[Coord]

	def in_bounds(self, x: int, y: int) -> bool:
		return 0 <= x < self.width and 0 <= y < self.height

	def is_blocked(self, x: int, y: int) -> bool:
		return (x, y) in self.blocked

	def walkable(self, x: int, y: int) -> bool:
		if not self.in_bounds(x, y):
			return False
		return not self.is_blocked(x, y)

	def add_blocked(self, coords: Iterable[Coord]) -> None:
		for c in coords:
			self.blocked.add(c)


