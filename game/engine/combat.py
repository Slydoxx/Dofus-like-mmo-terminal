from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

from .ability import Ability
from .grid import Grid
from .entities import Entity, Player, Monster


@dataclass
class IntentLog:
	entries: List[str]

	def log(self, message: str) -> None:
		self.entries.append(message)


@dataclass
class CombatArena:
	width: int = 10
	height: int = 6
	player_start: Tuple[int, int] = (1, 3)
	monster_start: Tuple[int, int] = (8, 3)
	
	def create_combat_grid(self) -> Grid:
		blocked = set()
		
		for x in range(self.width):
			blocked.add((x, 0))
			blocked.add((x, self.height - 1))
		for y in range(self.height):
			blocked.add((0, y))
			blocked.add((self.width - 1, y))
		
		return Grid(width=self.width, height=self.height, blocked=blocked)


@dataclass
class CombatState:
	player: Player
	monsters: List[Monster]
	current_turn: int
	player_ap: int
	player_mp: int
	log: IntentLog
	arena: CombatArena
	combat_grid: Grid
	is_active: bool = True
	current_phase: str = "player_turn"
	monster_ap: int = 0
	monster_mp: int = 0
	can_move: bool = True
	can_cast: bool = True

	def reset_turn(self) -> None:
		self.player_ap = self.player.get_total_stats().ap
		self.player_mp = self.player.get_total_stats().mp
		if self.monsters:
			self.monster_ap = self.monsters[0].stats.ap
			self.monster_mp = self.monsters[0].stats.mp
		self.current_turn += 1
		self.current_phase = "player_turn"
		self.can_move = True
		self.can_cast = True
		self.log.log(f"=== TURN {self.current_turn} ===")
		self.log.log(f"Your turn! AP: {self.player_ap}, MP: {self.player_mp}")

	def start_combat(self) -> None:
		self.player.position = self.arena.player_start
		if self.monsters:
			self.monsters[0].position = self.arena.monster_start
			self.monster_ap = self.monsters[0].stats.ap
			self.monster_mp = self.monsters[0].stats.mp
		self.log.log("=== COMBAT ARENA ===")
		self.log.log(f"Fighting: {self.monsters[0].name if self.monsters else 'Unknown'}")


def validate_and_log_intent(
	ability: Ability,
	source_pos: Tuple[int, int],
	target_pos: Tuple[int, int],
	current_ap: int,
	intent_log: IntentLog,
) -> bool:
	if current_ap < ability.cost_ap:
		intent_log.log(f"insufficient AP for {ability.id}")
		return False
	if not ability.in_range(source_pos, target_pos):
		intent_log.log(f"target out of range for {ability.id}")
		return False
	intent_log.log(
		f"would cast {ability.id} from {source_pos} to {target_pos} costing {ability.cost_ap} AP"
	)
	return True


def validate_in_bounds_and_log(
	ability: Ability,
	source_pos: Tuple[int, int],
	target_pos: Tuple[int, int],
	current_ap: int,
	grid: Grid,
	intent_log: IntentLog,
) -> bool:
	if not grid.in_bounds(target_pos[0], target_pos[1]):
		intent_log.log("target out of bounds")
		return False
	return validate_and_log_intent(ability, source_pos, target_pos, current_ap, intent_log)


def resolve_damage(attacker: Entity, target: Entity, base_damage: int) -> int:
	damage = max(1, base_damage - target.stats.res)
	return target.stats.take_damage(damage)


def _bresenham_line(a: Tuple[int, int], b: Tuple[int, int]) -> List[Tuple[int, int]]:
	x0, y0 = a
	x1, y1 = b
	points: List[Tuple[int, int]] = []
	dx = abs(x1 - x0)
	dy = -abs(y1 - y0)
	sx = 1 if x0 < x1 else -1
	sy = 1 if y0 < y1 else -1
	err = dx + dy
	x, y = x0, y0
	while True:
		points.append((x, y))
		if x == x1 and y == y1:
			break
		e2 = 2 * err
		if e2 >= dy:
			err += dy
			x += sx
		if e2 <= dx:
			err += dx
			y += sy
	return points


def has_line_of_sight(grid: Grid, src: Tuple[int, int], dst: Tuple[int, int]) -> bool:
	line = _bresenham_line(src, dst)
	if not line:
		return True
	for cell in line[1:-1]:
		if cell in grid.blocked:
			return False
	return True


def try_move_in_combat(combat_state: CombatState, dx: int, dy: int) -> bool:
	if not combat_state.can_move or combat_state.player_mp <= 0:
		return False
	
	new_x = combat_state.player.position[0] + dx
	new_y = combat_state.player.position[1] + dy
	
	if combat_state.combat_grid.walkable(new_x, new_y):
		combat_state.player.position = (new_x, new_y)
		combat_state.player_mp -= 1
		combat_state.log.log(f"👤 Moved to ({new_x}, {new_y}) - MP: {combat_state.player_mp}")
		return True
	else:
		combat_state.log.log("🚫 Can't move there!")
		return False


def resolve_ability_effects(
	ability: Ability,
	source: Entity,
	target_pos: Tuple[int, int],
	combat_state: CombatState,
	monsters: List[Monster]
) -> None:
	combat_state.player_ap -= ability.cost_ap
	
	for effect in ability.effects:
		if effect["type"] == "damage":
			for monster in monsters:
				if monster.position == target_pos:
					# If this is a ranged tag, require line-of-sight; melee ignores LoS
					if "ranged" in ability.tags and not has_line_of_sight(combat_state.combat_grid, source.position, target_pos):
						combat_state.log.log("🚫 No line of sight")
						return
					damage = resolve_damage(source, monster, effect["amount"])
					combat_state.log.log(f"⚔️ {ability.id} deals {damage} damage to {monster.name}")
					if not monster.stats.is_alive():
						combat_state.log.log(f"💀 {monster.name} is defeated!")
						monsters.remove(monster)
						return
					break
		elif effect["type"] == "charge":
			for monster in monsters:
				if monster.position == target_pos:
					dx = target_pos[0] - source.position[0]
					dy = target_pos[1] - source.position[1]
					if dx != 0:
						dx = dx // abs(dx)
					if dy != 0:
						dy = dy // abs(dy)
					
					charge_pos = (target_pos[0] - dx, target_pos[1] - dy)
					if combat_state.combat_grid.walkable(charge_pos[0], charge_pos[1]):
						combat_state.player.position = charge_pos
						combat_state.log.log(f"💨 Charged to {charge_pos}")
						
						damage = resolve_damage(source, monster, effect["amount"])
						combat_state.log.log(f"⚔️ Charge deals {damage} damage to {monster.name}")
						if not monster.stats.is_alive():
							combat_state.log.log(f"💀 {monster.name} is defeated!")
							monsters.remove(monster)
							return
					else:
						combat_state.log.log(f"💨 Can't charge there - blocked!")
					break
		elif effect["type"] == "push":
			for monster in monsters:
				if monster.position == target_pos:
					dx = target_pos[0] - source.position[0]
					dy = target_pos[1] - source.position[1]
					if dx != 0:
						dx = dx // abs(dx)
					if dy != 0:
						dy = dy // abs(dy)
					distance = max(1, int(effect.get("distance", 1)))
					curr = target_pos
					collided = False
					for _ in range(distance):
						next_pos = (curr[0] + dx, curr[1] + dy)
						if combat_state.combat_grid.walkable(next_pos[0], next_pos[1]):
							curr = next_pos
						else:
							collided = True
							break
					if curr != monster.position:
						monster.position = curr
						combat_state.log.log(f"💨 {monster.name} pushed to {curr}")
					if collided:
						bonus = 10
						dmg = resolve_damage(source, monster, bonus)
						combat_state.log.log(f"💥 Collision! {monster.name} takes {dmg} bonus damage")
						if not monster.stats.is_alive():
							combat_state.log.log(f"💀 {monster.name} is defeated!")
							monsters.remove(monster)
							return
					break
		elif effect["type"] == "buff_ap":
			combat_state.player_ap += effect["amount"]
			combat_state.log.log(f"✨ AP buffed by {effect['amount']}")


def check_combat_trigger(player_pos: Tuple[int, int], monsters: List[Monster]) -> Optional[Monster]:
	for monster in monsters:
		if monster.position == player_pos:
			return monster
	return None


def monster_ai_turn(combat_state: CombatState) -> None:
	if not combat_state.monsters:
		return
	
	monster = combat_state.monsters[0]
	combat_state.log.log("--- Monster's turn ---")
	
	if combat_state.monster_ap >= 3:
		damage = resolve_damage(monster, combat_state.player, monster.stats.atk)
		combat_state.log.log(f"👹 {monster.name} attacks for {damage} damage!")
		combat_state.monster_ap -= 3
	else:
		combat_state.log.log(f"👹 {monster.name} is too tired to attack")
	
	if not combat_state.player.stats.is_alive():
		combat_state.log.log("💀 You have been defeated!")
		combat_state.is_active = False
		return
	
	combat_state.reset_turn()


def end_combat_turn(combat_state: CombatState) -> None:
	if combat_state.current_phase != "player_turn":
		combat_state.log.log("Not your turn!")
		return
	
	combat_state.current_phase = "monster_turn"
	monster_ai_turn(combat_state)


def render_combat_arena(combat_state: CombatState) -> List[str]:
	lines: List[str] = []
	lines.append("╔══════════════════════════════════════════════════════════════╗")
	lines.append("║                        COMBAT ARENA                          ║")
	lines.append("╠══════════════════════════════════════════════════════════════╣")
	
	for y in range(combat_state.combat_grid.height):
		row = "║ "
		for x in range(combat_state.combat_grid.width):
			if (x, y) == combat_state.player.position:
				row += "👤"
			elif any(m.position == (x, y) for m in combat_state.monsters):
				row += "👹"
			elif (x, y) in combat_state.combat_grid.blocked:
				row += "█"
			else:
				row += "·"
		row += " ║"
		lines.append(row)
	
	lines.append("╚══════════════════════════════════════════════════════════════╝")
	return lines


