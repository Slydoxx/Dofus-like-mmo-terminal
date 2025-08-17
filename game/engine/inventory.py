from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

from .stats import Stats


@dataclass
class Item:
	id: str
	name: str
	description: str
	weight: float
	value: int
	stackable: bool = False
	max_stack: int = 1
	quantity: int = 1


@dataclass
class Equipment:
	id: str
	name: str
	description: str
	weight: float
	value: int
	slot: str
	stats_bonus: Stats
	stackable: bool = field(default=False)
	max_stack: int = field(default=1)
	quantity: int = field(default=1)


@dataclass
class Consumable:
	id: str
	name: str
	description: str
	weight: float
	value: int
	effect_type: str
	effect_value: int
	stackable: bool = field(default=True)
	max_stack: int = field(default=10)
	quantity: int = field(default=1)


@dataclass
class Weapon:
	id: str
	name: str
	description: str
	weight: float
	value: int
	weapon_type: str
	base_damage: int
	abilities: List[str]
	stackable: bool = field(default=False)
	max_stack: int = field(default=1)
	quantity: int = field(default=1)


@dataclass
class Inventory:
	items: List[Item] = field(default_factory=list)
	total_weight: float = 0.0
	max_weight: float = 50.0
	
	def add_item(self, item: Item) -> bool:
		incoming_weight = item.weight * item.quantity
		if self.total_weight + incoming_weight > self.max_weight:
			return False
		
		if item.stackable:
			remaining = item.quantity
			# Fill existing stacks first
			for existing_item in self.items:
				if remaining <= 0:
					break
				if existing_item.id == item.id and existing_item.quantity < existing_item.max_stack:
					space_left = existing_item.max_stack - existing_item.quantity
					amount_to_add = min(space_left, remaining)
					existing_item.quantity += amount_to_add
					self.total_weight += amount_to_add * item.weight
					remaining -= amount_to_add
			# Create new stacks for any remaining
			while remaining > 0:
				create_qty = min(item.max_stack, remaining)
				new_stack = replace(item, quantity=create_qty)
				self.items.append(new_stack)
				self.total_weight += create_qty * item.weight
				remaining -= create_qty
			return True
		
		# Non-stackable: append as-is
		self.items.append(item)
		self.total_weight += item.weight * item.quantity
		return True
	
	def remove_item(self, item_id: str, quantity: int = 1) -> bool:
		remaining = quantity
		i = 0
		while i < len(self.items) and remaining > 0:
			item = self.items[i]
			if item.id != item_id:
				i += 1
				continue
			if item.quantity <= remaining:
				self.total_weight -= item.weight * item.quantity
				remaining -= item.quantity
				self.items.pop(i)
				continue
			# Partial remove from this stack
			item.quantity -= remaining
			self.total_weight -= item.weight * remaining
			remaining = 0
			break
		return remaining == 0
	
	def has_item(self, item_id: str, quantity: int = 1) -> bool:
		total_quantity = 0
		for item in self.items:
			if item.id == item_id:
				total_quantity += item.quantity
		return total_quantity >= quantity


@dataclass
class EquipmentSlots:
	weapon: Optional[Weapon] = None
	armor: Optional[Equipment] = None
	helmet: Optional[Equipment] = None
	boots: Optional[Equipment] = None
	
	def equip_item(self, item: Item) -> Optional[Item]:
		if isinstance(item, Weapon):
			unequipped = self.weapon
			self.weapon = item
			return unequipped
		elif isinstance(item, Equipment):
			if item.slot == "armor":
				unequipped = self.armor
				self.armor = item
				return unequipped
			elif item.slot == "helmet":
				unequipped = self.helmet
				self.helmet = item
				return unequipped
			elif item.slot == "boots":
				unequipped = self.boots
				self.boots = item
				return unequipped
		return None
	
	def get_equipped_stats(self) -> Stats:
		total_bonus = Stats(hp=0, ap=0, mp=0, atk=0, res=0, armor=0)
		
		if self.weapon:
			total_bonus.atk += self.weapon.base_damage
		if self.armor:
			total_bonus.hp += self.armor.stats_bonus.hp
			total_bonus.ap += self.armor.stats_bonus.ap
			total_bonus.mp += self.armor.stats_bonus.mp
			total_bonus.atk += self.armor.stats_bonus.atk
			total_bonus.res += self.armor.stats_bonus.res
			total_bonus.armor += self.armor.stats_bonus.armor
		if self.helmet:
			total_bonus.hp += self.helmet.stats_bonus.hp
			total_bonus.ap += self.helmet.stats_bonus.ap
			total_bonus.mp += self.helmet.stats_bonus.mp
			total_bonus.atk += self.helmet.stats_bonus.atk
			total_bonus.res += self.helmet.stats_bonus.res
			total_bonus.armor += self.helmet.stats_bonus.armor
		if self.boots:
			total_bonus.hp += self.boots.stats_bonus.hp
			total_bonus.ap += self.boots.stats_bonus.ap
			total_bonus.mp += self.boots.stats_bonus.mp
			total_bonus.atk += self.boots.stats_bonus.atk
			total_bonus.res += self.boots.stats_bonus.res
			total_bonus.armor += self.boots.stats_bonus.armor
		
		return total_bonus


ITEMS = {
	"health_potion": Consumable(
		id="health_potion",
		name="Health Potion",
		description="Restores 50 HP",
		weight=0.5,
		value=20,
		effect_type="heal",
		effect_value=50
	),
	"mana_potion": Consumable(
		id="mana_potion",
		name="Mana Potion",
		description="Restores 30 MP",
		weight=0.5,
		value=15,
		effect_type="mana",
		effect_value=30
	),
	"iron_sword": Weapon(
		id="iron_sword",
		name="Iron Sword",
		description="A reliable iron sword for melee combat",
		weight=2.0,
		value=100,
		weapon_type="sword",
		base_damage=15,
		abilities=["boost", "charge", "slash"]
	),
	"wooden_bow": Weapon(
		id="wooden_bow",
		name="Wooden Bow",
		description="A wooden bow for ranged combat",
		weight=1.5,
		value=80,
		weapon_type="bow",
		base_damage=12,
		abilities=["boost", "precise_shot", "push_shot"]
	),
	"magic_staff": Weapon(
		id="magic_staff",
		name="Magic Staff",
		description="A staff imbued with magical power",
		weight=1.0,
		value=120,
		weapon_type="staff",
		base_damage=10,
		abilities=["boost", "fireball", "ice_shield"]
	),
	"leather_armor": Equipment(
		id="leather_armor",
		name="Leather Armor",
		description="Light leather armor",
		weight=3.0,
		value=50,
		slot="armor",
		stats_bonus=Stats(hp=0, ap=0, mp=0, atk=0, res=0, armor=3)
	)
}


def get_item_by_id(item_id: str) -> Optional[Item]:
	return ITEMS.get(item_id)
