from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .stats import Stats


@dataclass
class WeaponSkills:
	melee_damage: int = 0
	ranged_damage: int = 0
	magic_damage: int = 0
	
	def add_experience(self, skill_type: str, amount: int = 1) -> None:
		if skill_type == "melee":
			self.melee_damage += amount
		elif skill_type == "ranged":
			self.ranged_damage += amount
		elif skill_type == "magic":
			self.magic_damage += amount


@dataclass
class Weapon:
	id: str
	name: str
	description: str
	weapon_type: str
	base_damage: int
	abilities: List[str]
	skill_type: str


@dataclass
class Progression:
	weapon_skills: WeaponSkills
	equipped_weapon: Optional[str] = None
	
	def get_skill_bonus(self, skill_type: str) -> int:
		if skill_type == "melee":
			return self.weapon_skills.melee_damage
		elif skill_type == "ranged":
			return self.weapon_skills.ranged_damage
		elif skill_type == "magic":
			return self.weapon_skills.magic_damage
		return 0


WEAPONS = {
	"sword": Weapon(
		id="sword",
		name="Iron Sword",
		description="A reliable iron sword for melee combat",
		weapon_type="melee",
		base_damage=15,
		abilities=["boost", "charge", "slash"],
		skill_type="melee"
	),
	"bow": Weapon(
		id="bow",
		name="Wooden Bow",
		description="A wooden bow for ranged combat",
		weapon_type="ranged",
		base_damage=12,
		abilities=["boost", "precise_shot", "push_shot"],
		skill_type="ranged"
	),
	"staff": Weapon(
		id="staff",
		name="Magic Staff",
		description="A staff imbued with magical power",
		weapon_type="magic",
		base_damage=10,
		abilities=["boost", "fireball", "ice_shield"],
		skill_type="magic"
	)
}


def get_weapon_by_id(weapon_id: str) -> Optional[Weapon]:
	return WEAPONS.get(weapon_id)


def calculate_damage_with_skills(base_damage: int, skill_bonus: int) -> int:
	return base_damage + skill_bonus
