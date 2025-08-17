from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

from ..engine.ability import Ability, REGISTRY, register, create_weapon_abilities, get_abilities_for_weapon, in_range
from ..engine.combat import CombatState, CombatArena, IntentLog, validate_in_bounds_and_log, resolve_ability_effects, check_combat_trigger, end_combat_turn, render_combat_arena, try_move_in_combat, has_line_of_sight
from ..engine.content import MapModel, MonsterModel, SpellModel, AbilityModel, load_map, load_monster, load_spells, load_abilities
from ..engine.entities import Player, Monster, Merchant, Npc
from ..engine.grid import Grid
from ..engine.stats import Stats
from ..engine.progression import Progression, WeaponSkills
from ..engine.inventory import Inventory, EquipmentSlots, get_item_by_id
from ..engine.quests import QuestLog, get_quest_by_id, check_quest_requirements
from ..engine.progression import WeaponSkills


CONTENT_DIR = Path(__file__).resolve().parents[1] / "content"


@dataclass
class GameState:
	grid: Grid
	player: Player
	monsters: List[Monster]
	merchants: List[Merchant]
	map_name: str
	log: IntentLog
	npcs: List[Npc] | None = None
	combat_state: Optional[CombatState] = None
	in_combat: bool = False
	player_world_pos: Optional[Tuple[int, int]] = None


def build_grid_from_map(m: MapModel) -> Grid:
	blocked = {(c.x, c.y) for c in m.blocked}
	return Grid(width=m.width, height=m.height, blocked=set(blocked))


def create_monster_from_model(model: MonsterModel, position: Tuple[int, int]) -> Monster:
	return Monster(
		id=model.id,
		name=model.name,
		stats=Stats(
			hp=model.stats.hp,
			ap=model.stats.ap,
			mp=model.stats.mp,
			atk=model.stats.atk,
			res=model.stats.res
		),
		position=position,
		tags=set(model.tags)
	)


def create_player_with_progression() -> Player:
	progression = Progression(
		weapon_skills=WeaponSkills(),
		equipped_weapon="sword"
	)
	
	player = Player(
		id="player",
		name="Hero",
		stats=Stats(hp=100, ap=6, mp=3, atk=10, res=5),
		position=(2, 2),
		tags={"player"},
		progression=progression,
		inventory=Inventory(),
		equipment=EquipmentSlots(),
		quest_log=QuestLog(),
		gold=100
	)
	
	quest = get_quest_by_id("first_blood")
	if quest:
		player.quest_log.add_quest(quest)
	
	health_potion = get_item_by_id("health_potion")
	if health_potion:
		player.inventory.add_item(health_potion)
	
	iron_sword = get_item_by_id("iron_sword")
	if iron_sword:
		player.inventory.add_item(iron_sword)
	
	wooden_bow = get_item_by_id("wooden_bow")
	if wooden_bow:
		player.inventory.add_item(wooden_bow)
	
	magic_staff = get_item_by_id("magic_staff")
	if magic_staff:
		player.inventory.add_item(magic_staff)
	
	leather_armor = get_item_by_id("leather_armor")
	if leather_armor:
		player.inventory.add_item(leather_armor)
	
	return player


def load_content_and_init() -> GameState:
	map_model = load_map(CONTENT_DIR / "maps" / "zone_001.json")
	monster_model = load_monster(CONTENT_DIR / "monsters" / "slime.json")
	
	# Load abilities from JSON if present; fallback to built-ins
	abilities_path = CONTENT_DIR / "abilities" / "weapons.json"
	if abilities_path.exists():
		models = load_abilities(abilities_path)
		from ..engine.ability import Ability, register
		from ..engine.effects import Damage, Push, BuffAp, Charge
		for m in models:
			effects = []
			for e in m.effects:
				if e.type == "damage" and e.amount is not None:
					effects.append(Damage(amount=e.amount))
				elif e.type == "push" and e.distance is not None:
					effects.append(Push(distance=e.distance))
				elif e.type == "buff_ap" and e.amount is not None and e.duration is not None:
					effects.append(BuffAp(amount=e.amount, duration=e.duration))
				elif e.type == "charge" and e.amount is not None:
					effects.append(Charge(amount=e.amount))
			register(Ability(id=m.id, name=m.name, tags=m.tags, cost_ap=m.cost_ap, range_min=m.range_min, range_max=m.range_max, effects=effects, weapon_type=m.weapon_type))
	else:
		create_weapon_abilities()
	
	grid = build_grid_from_map(map_model)
	player = create_player_with_progression()
	
	monsters = [
		create_monster_from_model(monster_model, (10, 10)),
		create_monster_from_model(monster_model, (20, 15)),
		create_monster_from_model(monster_model, (30, 8)),
	]
	
	merchants = [
		Merchant(id="m1", name="Trader", stats=Stats(hp=1, ap=0, mp=0, atk=0, res=0), position=(5, 10), tags={"merchant"}, shop_id="general_store")
	]
	
	npcs = [
		Npc(id="npc1", name="Villager", stats=Stats(hp=1, ap=0, mp=0, atk=0, res=0), position=(3, 2), tags={"npc"}, dialogue_id="greeting_1")
	]
	return GameState(
		grid=grid,
		player=player,
		monsters=monsters,
		merchants=merchants,
		npcs=npcs,
		map_name=map_model.name,
		log=IntentLog(entries=[])
	)


def try_move(state: GameState, dx: int, dy: int) -> None:
	if state.in_combat:
		if state.combat_state:
			try_move_in_combat(state.combat_state, dx, dy)
		return
	
	new_x = state.player.position[0] + dx
	new_y = state.player.position[1] + dy
	if state.grid.walkable(new_x, new_y):
		state.player.position = (new_x, new_y)
		
		triggered_monster = check_combat_trigger(state.player.position, state.monsters)
		if triggered_monster:
			start_combat(state, triggered_monster)


def start_combat(state: GameState, monster: Monster) -> None:
	state.in_combat = True
	state.player_world_pos = state.player.position
	
	arena = CombatArena()
	combat_grid = arena.create_combat_grid()
	
	state.combat_state = CombatState(
		player=state.player,
		monsters=[monster],
		current_turn=1,
		player_ap=state.player.get_total_stats().ap,
		player_mp=state.player.get_total_stats().mp,
		log=state.log,
		arena=arena,
		combat_grid=combat_grid
	)
	
	state.combat_state.start_combat()


def end_combat(state: GameState) -> None:
	state.in_combat = False
	if state.player_world_pos:
		state.player.position = state.player_world_pos
		state.player_world_pos = None
	state.combat_state = None


def handle_monster_defeat(state: GameState, monster: Monster) -> None:
	original_hp = monster.stats.hp
	gold_gain = original_hp // 5 + 5
	
	state.player.add_gold(gold_gain)
	state.player.add_weapon_experience(1)
	
	state.log.log(f"💀 {monster.name} defeated!")
	state.log.log(f"💰 Gained {gold_gain} gold")
	state.log.log(f"⚔️  Weapon experience gained!")
	
	update_quest_progress(state, "kill_monsters", monster.id)
	check_quest_completion(state)


def update_quest_progress(state: GameState, objective_type: str, target: str) -> None:
	for quest_id, quest in state.player.quest_log.active_quests.items():
		for objective in quest.objectives:
			if (objective.objective_type.value == objective_type and 
				(objective.target == target or objective.target == "any")):
				objective.update_progress()
				state.log.log(f"📋 Quest progress: {objective.description}")


def check_quest_completion(state: GameState) -> None:
	completed_quests = []
	for quest_id, quest in state.player.quest_log.active_quests.items():
		if all(obj.completed for obj in quest.objectives):
			completed_quests.append(quest_id)
	
	for quest_id in completed_quests:
		rewards = state.player.quest_log.complete_quest(quest_id)
		if rewards:
			state.log.log(f"🎉 Quest completed: {quest_id}!")
			if rewards.gold > 0:
				state.player.add_gold(rewards.gold)
				state.log.log(f"💰 Quest gold: +{rewards.gold}")
			for item_reward in rewards.items:
				item = get_item_by_id(item_reward["id"])
				if item:
					item.quantity = item_reward.get("quantity", 1)
					if state.player.inventory.add_item(item):
						state.log.log(f"🎒 Quest item: {item.name}")


def render_ascii(state: GameState) -> List[str]:
	if state.in_combat and state.combat_state:
		return render_combat_arena(state.combat_state)
	
	lines: List[str] = []
	for y in range(state.grid.height):
		row_chars: List[str] = []
		for x in range(state.grid.width):
			if (x, y) == state.player.position:
				row_chars.append("@")
			elif any(getattr(m, 'position', None) == (x, y) for m in getattr(state, 'merchants', [])):
				row_chars.append("$")
			elif any(m.position == (x, y) for m in state.monsters):
				row_chars.append("M")
			elif (x, y) in state.grid.blocked:
				row_chars.append("#")
			else:
				row_chars.append(".")
		lines.append("".join(row_chars))
	return lines


def abilities_bar(state: GameState) -> str:
	if not state.player.progression.equipped_weapon:
		return "No weapon equipped"
	
	weapon_abilities = get_abilities_for_weapon(state.player.progression.equipped_weapon)
	labels = []
	for idx, ability in enumerate(weapon_abilities[:3], start=1):
		labels.append(f"{idx}:{ability.name}[{ability.cost_ap}]")
	return " ".join(labels)


def handle_ability_selection(state: GameState, index: int) -> None:
	if not state.in_combat or not state.combat_state:
		state.log.log("Not in combat!")
		return
	
	if not state.combat_state.is_active:
		state.log.log("Combat is over!")
		return
	
	if state.combat_state.current_phase != "player_turn":
		state.log.log("Not your turn!")
		return
	
	if not state.player.progression.equipped_weapon:
		state.log.log("No weapon equipped!")
		return
	
	weapon_abilities = get_abilities_for_weapon(state.player.progression.equipped_weapon)
	if index < 1 or index > len(weapon_abilities):
		return
	
	ab = weapon_abilities[index - 1]
	if state.combat_state.player_ap < ab.cost_ap:
		state.log.log(f"Not enough AP! Need {ab.cost_ap}, have {state.combat_state.player_ap}")
		return

	# Instant cast at current enemy
	src = state.player.position
	tgt = state.combat_state.monsters[0].position
	# Optional melee adjacency only for true CQC (range_max<=1)
	if "melee" in ab.tags and ab.range_max <= 1:
		dist = abs(tgt[0] - src[0]) + abs(tgt[1] - src[1])
		if dist != 1:
			state.log.log("Target not adjacent for melee ability")
			return
	if not in_range(ab, src, tgt):
		state.log.log(f"Target out of range! Range: {ab.range_min}-{ab.range_max}")
		return
	if "ranged" in ab.tags and not has_line_of_sight(state.combat_state.combat_grid, src, tgt):
		state.log.log("🚫 No line of sight")
		return

	monster_before = state.combat_state.monsters[0]
	resolve_ability_effects(ab, state.player, tgt, state.combat_state, state.combat_state.monsters)
	if not state.combat_state.monsters:
		handle_monster_defeat(state, monster_before)
		state.log.log("🏆 Victory! All monsters defeated!")
		end_combat(state)
	elif state.combat_state.player_ap <= 0:
		state.log.log("No AP left! Press 'e' to end turn.")
	elif not state.combat_state.is_active:
		state.log.log("💀 Defeat! Combat ended.")
		end_combat(state)


def cast_ability_at(state: GameState, index: int, target: Tuple[int, int]) -> None:
	if not state.in_combat or not state.combat_state:
		return
	weapon_abilities = get_abilities_for_weapon(state.player.progression.equipped_weapon) if state.player.progression.equipped_weapon else []
	if index < 1 or index > len(weapon_abilities):
		return
	ab = weapon_abilities[index - 1]
	if state.combat_state.player_ap < ab.cost_ap:
		state.log.log(f"Not enough AP! Need {ab.cost_ap}, have {state.combat_state.player_ap}")
		return
	src = state.player.position
	# True melee adjacency only when range_max<=1
	if "melee" in ab.tags and ab.range_max <= 1:
		dist = abs(target[0] - src[0]) + abs(target[1] - src[1])
		if dist != 1:
			state.log.log("Target not adjacent for melee ability")
			return
	if not in_range(ab, src, target):
		state.log.log(f"Target out of range! Range: {ab.range_min}-{ab.range_max}")
		return
	if "ranged" in ab.tags and not has_line_of_sight(state.combat_state.combat_grid, src, target):
		state.log.log("🚫 No line of sight")
		return
	monster_before = state.combat_state.monsters[0] if state.combat_state.monsters else None
	resolve_ability_effects(ab, state.player, target, state.combat_state, state.combat_state.monsters)
	if not state.combat_state.monsters and monster_before is not None:
		handle_monster_defeat(state, monster_before)
		state.log.log("🏆 Victory! All monsters defeated!")
		end_combat(state)
	elif state.combat_state.player_ap <= 0:
		state.combat_state.log.log("No AP left! Press 'e' to end turn.")
	elif not state.combat_state.is_active:
		state.combat_state.log.log("💀 Defeat! Combat ended.")
		end_combat(state)


def begin_targeting(state: GameState, ability: Ability) -> None:
	state.targeting_mode = True
	state.target_cursor = state.combat_state.monsters[0].position if state.combat_state and state.combat_state.monsters else state.player.position
	state.pending_ability = ability


def move_target_cursor(state: GameState, dx: int, dy: int) -> None:
	if not state.combat_state or state.target_cursor is None:
		return
	x, y = state.target_cursor
	x = max(1, min(state.combat_state.combat_grid.width - 2, x + dx))
	y = max(1, min(state.combat_state.combat_grid.height - 2, y + dy))
	state.target_cursor = (x, y)


def confirm_target_and_cast(state: GameState) -> None:
	if not state.combat_state or not state.pending_ability:
		state.targeting_mode = False
		return
	ab = state.pending_ability
	src = state.player.position
	tgt = state.target_cursor or src
	if not in_range(ab, src, tgt):
		state.combat_state.log.log(f"Target out of range! Range: {ab.range_min}-{ab.range_max}")
		return
	if "ranged" in ab.tags and not has_line_of_sight(state.combat_state.combat_grid, src, tgt):
		state.combat_state.log.log("🚫 No line of sight")
		return
	monster_before = state.combat_state.monsters[0] if state.combat_state.monsters else None
	resolve_ability_effects(ab, state.player, tgt, state.combat_state, state.combat_state.monsters)
	if not state.combat_state.monsters and monster_before is not None:
		handle_monster_defeat(state, monster_before)
		state.combat_state.log.log("🏆 Victory! All monsters defeated!")
		end_combat(state)
	elif state.combat_state.player_ap <= 0:
		state.combat_state.log.log("No AP left! Press 'e' to end turn.")
	elif not state.combat_state.is_active:
		state.combat_state.log.log("💀 Defeat! Combat ended.")
		end_combat(state)
	state.targeting_mode = False
	state.pending_ability = None
	
	if not state.combat_state.monsters:
		handle_monster_defeat(state, monster_before)
		state.log.log("🏆 Victory! All monsters defeated!")
		end_combat(state)
	elif state.combat_state.player_ap <= 0:
		state.log.log("No AP left! Press 'e' to end turn.")
	elif not state.combat_state.is_active:
		state.log.log("💀 Defeat! Combat ended.")
		end_combat(state)


