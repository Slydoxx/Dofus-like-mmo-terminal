from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .effects import Damage, Push, BuffAp


@dataclass
class Ability:
	id: str
	name: str
	tags: List[str]
	cost_ap: int
	range_min: int
	range_max: int
	effects: List[Dict[str, any]]
	weapon_type: str = ""


REGISTRY: Dict[str, Ability] = {}


def register(ability: Ability) -> None:
	REGISTRY[ability.id] = ability


def get_abilities_for_weapon(weapon_type: str) -> List[Ability]:
	return [ab for ab in REGISTRY.values() if ab.weapon_type == weapon_type]


def create_weapon_abilities() -> None:
	sword_abilities = [
		Ability(
			id="boost",
			name="Boost",
			tags=["buff", "self"],
			cost_ap=2,
			range_min=0,
			range_max=0,
			effects=[{"type": "buff_ap", "amount": 2, "duration": 1}],
			weapon_type="sword"
		),
		Ability(
			id="charge",
			name="Charge",
			tags=["movement", "melee"],
			cost_ap=3,
			range_min=1,
			range_max=4,
			effects=[{"type": "charge", "amount": 25}],
			weapon_type="sword"
		),
		Ability(
			id="slash",
			name="Slash",
			tags=["melee"],
			cost_ap=4,
			range_min=1,
			range_max=1,
			effects=[{"type": "damage", "amount": 35}],
			weapon_type="sword"
		)
	]
	
	bow_abilities = [
		Ability(
			id="boost",
			name="Boost",
			tags=["buff", "self"],
			cost_ap=2,
			range_min=0,
			range_max=0,
			effects=[{"type": "buff_ap", "amount": 2, "duration": 1}],
			weapon_type="bow"
		),
		Ability(
			id="precise_shot",
			name="Precise Shot",
			tags=["ranged"],
			cost_ap=3,
			range_min=2,
			range_max=6,
			effects=[{"type": "damage", "amount": 30}],
			weapon_type="bow"
		),
		Ability(
			id="push_shot",
			name="Push Shot",
			tags=["ranged", "control"],
			cost_ap=4,
			range_min=2,
			range_max=5,
			effects=[{"type": "damage", "amount": 20}, {"type": "push", "distance": 2}],
			weapon_type="bow"
		)
	]
	
	staff_abilities = [
		Ability(
			id="boost",
			name="Boost",
			tags=["buff", "self"],
			cost_ap=2,
			range_min=0,
			range_max=0,
			effects=[{"type": "buff_ap", "amount": 2, "duration": 1}],
			weapon_type="staff"
		),
		Ability(
			id="fireball",
			name="Fireball",
			tags=["magic", "ranged"],
			cost_ap=4,
			range_min=2,
			range_max=5,
			effects=[{"type": "damage", "amount": 40}],
			weapon_type="staff"
		),
		Ability(
			id="ice_shield",
			name="Ice Shield",
			tags=["magic", "defensive"],
			cost_ap=3,
			range_min=0,
			range_max=0,
			effects=[{"type": "buff_ap", "amount": 3, "duration": 2}],
			weapon_type="staff"
		)
	]
	
	for ability in sword_abilities + bow_abilities + staff_abilities:
		register(ability)


def in_range(ability: Ability, source: Tuple[int, int], target: Tuple[int, int]) -> bool:
	dx = abs(target[0] - source[0])
	dy = abs(target[1] - source[1])
	distance = dx + dy
	return ability.range_min <= distance <= ability.range_max


