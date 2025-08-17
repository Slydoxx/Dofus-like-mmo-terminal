from __future__ import annotations

import sys
from typing import Optional

from .game_loop import abilities_bar, handle_ability_selection, load_content_and_init, render_ascii, try_move, end_combat_turn


HELP_TEXT = "Controls: w/a/s/d or z/q/s/d to move, 1/2/3 abilities, e end turn, i inventory, h help, q quit"


def clear() -> None:
	print("\x1b[2J\x1b[H", end="")


def draw(state, inventory_mode: bool = False, selected_item: int = 0, selected_tab: int = 0) -> None:
	clear()
	
	if inventory_mode:
		draw_inventory(state, selected_item, selected_tab)
		return
	
	lines = render_ascii(state)
	for line in lines:
		print(line)
	
	if state.in_combat and state.combat_state:
		print(f"\n🎯 COMBAT MODE - Turn {state.combat_state.current_turn}")
		print("=" * 60)
		print(f"👤 YOU:     HP:{state.player.get_total_stats().current_hp:3d}/{state.player.get_total_stats().hp:3d} | AP:{state.combat_state.player_ap:2d} | MP:{state.combat_state.player_mp:2d}")
		if state.combat_state.monsters:
			monster = state.combat_state.monsters[0]
			print(f"👹 ENEMY:   HP:{monster.stats.current_hp:3d}/{monster.stats.hp:3d} | AP:{state.combat_state.monster_ap:2d} | MP:{state.combat_state.monster_mp:2d}")
		print("=" * 60)
		print(f"📋 Phase: {state.combat_state.current_phase.upper()}")
		
		if state.combat_state.current_phase == "player_turn":
			actions = []
			if state.combat_state.player_mp > 0:
				actions.append("MOVE (WASD)")
			if state.combat_state.player_ap > 0:
				actions.append("CAST (1/2/3)")
			actions.append("END TURN (E)")
			print(f"🎮 Actions: {' | '.join(actions)}")
		
		if not state.combat_state.is_active:
			print("💀 COMBAT ENDED")
	else:
		print(f"\n🗺️  WORLD MAP: {state.map_name}")
		print("=" * 60)
		total_stats = state.player.get_total_stats()
		base_stats = state.player.stats
		equipment_bonus = state.player.equipment.get_equipped_stats()
		
		print(f"👤 Hero: HP:{total_stats.current_hp:3d}/{total_stats.hp:3d} | AP:{total_stats.ap:2d} | MP:{total_stats.current_mp:2d}/{total_stats.mp:2d}")
		print(f"⚔️  Weapon: {state.player.progression.equipped_weapon or 'None'}")
		print(f"🎯 Skills: Melee:{state.player.progression.weapon_skills.melee_damage:2d} | Ranged:{state.player.progression.weapon_skills.ranged_damage:2d} | Magic:{state.player.progression.weapon_skills.magic_damage:2d}")
		print(f"💰 Gold: {state.player.gold}")
		print(f"👹 Monsters remaining: {len(state.monsters)}")
		print("=" * 60)
		
		equipped_items = []
		for slot_name, equipment in state.player.equipment.__dict__.items():
			if equipment:
				equipped_items.append(f"{slot_name}: {equipment.name}")
		
		if equipped_items:
			print("⚔️  Equipped:")
			for item in equipped_items:
				print(f"   {item}")
		
		if state.player.inventory.items:
			print("🎒 Inventory:")
			for item in state.player.inventory.items:
				if item.quantity > 1:
					print(f"   {item.name} x{item.quantity}")
				else:
					print(f"   {item.name}")
		
		if state.player.quest_log.active_quests:
			print("📋 Active Quests:")
			for quest_id, quest in state.player.quest_log.active_quests.items():
				progress = state.player.quest_log.get_quest_progress(quest_id)
				if progress:
					print(f"   {progress['name']}: {progress['progress']}")
	
	print(f"\n⚔️  Abilities: {abilities_bar(state)}")
	
	if state.log.entries:
		print("\n📝 Combat Log:")
		last_entries = state.log.entries[-4:]
		for entry in last_entries:
			print(f"   {entry}")
	
	print(f"\n⌨️  {HELP_TEXT}")


def draw_inventory(state, selected_item: int, selected_tab: int = 0) -> None:
	print("╔══════════════════════════════════════════════════════════════╗")
	print("║                        INVENTORY                            ║")
	print("╠══════════════════════════════════════════════════════════════╣")
	
	tabs = ["Items", "Weapons", "Armor"]
	tab_line = "║ "
	for i, tab in enumerate(tabs):
		selector = "▶ " if i == selected_tab else "  "
		tab_line += f"{selector}{tab}  "
	tab_line = tab_line.ljust(58) + " ║"
	print(tab_line)
	
	print("╠══════════════════════════════════════════════════════════════╣")
	
	categorized_items = {
		0: [item for item in state.player.inventory.items if hasattr(item, 'effect_type')],  # Items (Consumables)
		1: [item for item in state.player.inventory.items if hasattr(item, 'weapon_type')],  # Weapons
		2: [item for item in state.player.inventory.items if hasattr(item, 'slot') and not hasattr(item, 'weapon_type')]  # Armor
	}
	
	current_items = categorized_items.get(selected_tab, [])
	
	if not current_items:
		print("║                    No items in this category                ║")
	else:
		for i, item in enumerate(current_items):
			selector = "▶ " if i == selected_item else "  "
			if item.quantity > 1:
				line = f"║ {selector}{item.name} x{item.quantity}"
			else:
				line = f"║ {selector}{item.name}"
			
			line = line.ljust(58) + " ║"
			print(line)
			
			if i == selected_item:
				desc_line = f"║    {item.description}".ljust(58) + " ║"
				print(desc_line)
				
				if hasattr(item, 'weapon_type'):
					type_line = f"║    Type: {item.weapon_type} | Damage: {item.base_damage}".ljust(58) + " ║"
					print(type_line)
					abilities_line = f"║    Abilities: {', '.join(item.abilities)}".ljust(58) + " ║"
					print(abilities_line)
				elif hasattr(item, 'slot'):
					slot_line = f"║    Slot: {item.slot}".ljust(58) + " ║"
					print(slot_line)
				elif hasattr(item, 'effect_type'):
					effect_line = f"║    Effect: {item.effect_type} ({item.effect_value})".ljust(58) + " ║"
					print(effect_line)
				
				weight_line = f"║    Weight: {item.weight}kg | Value: {item.value} gold".ljust(58) + " ║"
				print(weight_line)
	
	print("╠══════════════════════════════════════════════════════════════╣")
	print("║ Controls: ←/→ Tabs | ↑/↓ Navigate | ENTER Use/Equip | ESC Exit ║")
	print("╚══════════════════════════════════════════════════════════════╝")


def read_key() -> str:
	try:
		import msvcrt
		ch = msvcrt.getwch()
		return ch
	except Exception:
		line = input()
		return line[:1] if line else ""


def main(argv: Optional[list[str]] = None) -> int:
	state = load_content_and_init()
	inventory_mode = False
	selected_item = 0
	selected_tab = 0
	
	draw(state, inventory_mode, selected_item, selected_tab)
	while True:
		ch = read_key()
		if ch == "q":
			break
		elif ch == "i":
			inventory_mode = not inventory_mode
			selected_item = 0
			selected_tab = 0
		elif inventory_mode:
			if ch in ("\x00", "\xe0"):  # Arrow key prefix (Windows)
				arrow = read_key()
				if arrow == "H":  # Up arrow
					categorized_items = {
						0: [item for item in state.player.inventory.items if hasattr(item, 'effect_type')],
						1: [item for item in state.player.inventory.items if hasattr(item, 'weapon_type')],
						2: [item for item in state.player.inventory.items if hasattr(item, 'slot') and not hasattr(item, 'weapon_type')]
					}
					current_items = categorized_items.get(selected_tab, [])
					if current_items:
						selected_item = max(0, selected_item - 1)
				elif arrow == "P":  # Down arrow
					categorized_items = {
						0: [item for item in state.player.inventory.items if hasattr(item, 'effect_type')],
						1: [item for item in state.player.inventory.items if hasattr(item, 'weapon_type')],
						2: [item for item in state.player.inventory.items if hasattr(item, 'slot') and not hasattr(item, 'weapon_type')]
					}
					current_items = categorized_items.get(selected_tab, [])
					if current_items:
						selected_item = min(len(current_items) - 1, selected_item + 1)
				elif arrow == "K":  # Left arrow
					selected_tab = max(0, selected_tab - 1)
					selected_item = 0
				elif arrow == "M":  # Right arrow
					selected_tab = min(2, selected_tab + 1)
					selected_item = 0
			elif ch == "\r":  # Enter
				categorized_items = {
					0: [item for item in state.player.inventory.items if hasattr(item, 'effect_type')],
					1: [item for item in state.player.inventory.items if hasattr(item, 'weapon_type')],
					2: [item for item in state.player.inventory.items if hasattr(item, 'slot') and not hasattr(item, 'weapon_type')]
				}
				current_items = categorized_items.get(selected_tab, [])
				if selected_item < len(current_items):
					use_item(state, current_items[selected_item])
			elif ch == "\x1b":  # ESC
				inventory_mode = False
		else:
			if ch in ("w", "z"):
				try_move(state, 0, -1)
			elif ch == "s":
				try_move(state, 0, 1)
			elif ch == "a":
				try_move(state, -1, 0)
			elif ch == "d":
				try_move(state, 1, 0)
			elif ch in ("1", "2", "3"):
				idx = int(ch)
				handle_ability_selection(state, idx)
			elif ch == "e" and state.in_combat and state.combat_state:
				end_combat_turn(state.combat_state)
			elif ch == "h":
				state.log.entries.append("help shown")
		draw(state, inventory_mode, selected_item, selected_tab)
	return 0


def use_item(state, item) -> None:
	if hasattr(item, 'weapon_type'):  # Weapon
		unequipped = state.player.equipment.equip_item(item)
		if unequipped:
			state.player.inventory.add_item(unequipped)
		state.player.inventory.remove_item(item.id, 1)
		state.player.progression.equipped_weapon = item.weapon_type
		state.log.log(f"⚔️  Equipped {item.name} ({item.weapon_type})")
		return
	
	if hasattr(item, 'slot'):  # Equipment
		unequipped = state.player.equipment.equip_item(item)
		if unequipped:
			state.player.inventory.add_item(unequipped)
		state.player.inventory.remove_item(item.id, 1)
		state.log.log(f"⚔️  Equipped {item.name}")
		return
	
	if hasattr(item, 'effect_type'):  # Consumable
		state.log.log(f"🎒 Used {item.name}")
		
		if item.effect_type == "heal":
			healed = state.player.stats.heal(item.effect_value)
			state.log.log(f"❤️  Healed {healed} HP")
		elif item.effect_type == "mana":
			restored = state.player.stats.restore_mana(item.effect_value)
			state.log.log(f"🔮 Restored {restored} MP")
		
		state.player.inventory.remove_item(item.id, 1)


if __name__ == "__main__":
	sys.exit(main())


