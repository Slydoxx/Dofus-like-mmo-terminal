from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set


@dataclass
class TaggableMixin:
	tags: Set[str] = field(default_factory=set, kw_only=True)

	def has_tag(self, tag: str) -> bool:
		return tag in self.tags

	def has_any(self, tags: Iterable[str]) -> bool:
		for t in tags:
			if t in self.tags:
				return True
		return False


def damage_multiplier_for_target(target_tags: Set[str]) -> float:
	if "boss" in target_tags:
		return 1.1
	return 1.0


