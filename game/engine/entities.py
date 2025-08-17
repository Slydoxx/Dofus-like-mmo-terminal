from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, List

from .stats import Stats
from .tags import TaggableMixin
from .progression import Progression, get_weapon_by_id, calculate_damage_with_skills
from .inventory import Inventory, EquipmentSlots
from .quests import QuestLog


Position = Tuple[int, int]


@dataclass
class Entity(TaggableMixin):
	id: str
	name: str
	stats: Stats
	position: Position


@dataclass
class Player(Entity):
	progression: Progression
	inventory: Inventory
	equipment: EquipmentSlots
	quest_log: QuestLog
	gold: int = 0
	
	def get_total_stats(self) -> Stats:
		base_stats = self.stats
		equipment_bonus = self.equipment.get_equipped_stats()
		
		return Stats(
			hp=base_stats.hp,
			ap=base_stats.ap + equipment_bonus.ap,
			mp=base_stats.mp + equipment_bonus.mp,
			atk=base_stats.atk + equipment_bonus.atk,
			res=base_stats.res + equipment_bonus.res,
			current_hp=base_stats.current_hp,
			current_mp=base_stats.current_mp,
			armor=base_stats.armor + equipment_bonus.armor
		)
	
	def get_weapon_damage(self) -> int:
		if not self.progression.equipped_weapon:
			return 5
		
		weapon = get_weapon_by_id(self.progression.equipped_weapon)
		if not weapon:
			return 5
		
		skill_bonus = self.progression.get_skill_bonus(weapon.skill_type)
		return calculate_damage_with_skills(weapon.base_damage, skill_bonus)
	
	def get_weapon_abilities(self) -> List[str]:
		if not self.progression.equipped_weapon:
			return []
		
		weapon = get_weapon_by_id(self.progression.equipped_weapon)
		if not weapon:
			return []
		
		return weapon.abilities
	
	def add_weapon_experience(self, amount: int = 1) -> None:
		if not self.progression.equipped_weapon:
			return
		
		weapon = get_weapon_by_id(self.progression.equipped_weapon)
		if not weapon:
			return
		
		self.progression.weapon_skills.add_experience(weapon.skill_type, amount)
	
	def add_gold(self, amount: int) -> None:
		self.gold += amount
	
	def can_afford(self, amount: int) -> bool:
		return self.gold >= amount


@dataclass
class Monster(Entity):
	pass


