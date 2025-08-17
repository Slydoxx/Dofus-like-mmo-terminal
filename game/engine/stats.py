from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Stats:
	hp: int
	ap: int
	mp: int
	atk: int
	res: int
	current_hp: int = 0
	current_mp: int = 0
	armor: int = 0
	
	def __post_init__(self):
		if self.current_hp == 0:
			self.current_hp = self.hp
		if self.current_mp == 0:
			self.current_mp = self.mp
	
	def heal(self, amount: int) -> int:
		old_hp = self.current_hp
		self.current_hp = min(self.hp, self.current_hp + amount)
		return self.current_hp - old_hp
	
	def restore_mana(self, amount: int) -> int:
		old_mp = self.current_mp
		self.current_mp = min(self.mp, self.current_mp + amount)
		return self.current_mp - old_mp
	
	def take_damage(self, damage: int) -> int:
		actual_damage = max(1, damage - self.armor)
		self.current_hp = max(0, self.current_hp - actual_damage)
		return actual_damage
	
	def is_alive(self) -> bool:
		return self.current_hp > 0


