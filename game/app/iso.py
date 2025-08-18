from __future__ import annotations

import sys
from typing import Tuple

import pygame

from .game_loop import load_content_and_init, try_move, handle_ability_selection, end_combat_turn, abilities_bar, cast_ability_at
from .ui.panels import (
    draw_inventory_panel,
    draw_profile_panel,
    draw_shop_panel,
    draw_npc_dialog,
    draw_merchant_dialog,
)
from ..engine.ability import Ability
from ..engine.content import load_shop
from ..engine.inventory import get_item_by_id
from pathlib import Path
import heapq


TILE_W = 64
TILE_H = 24
SCREEN_W = 1920
SCREEN_H = 1080

# UI colors
COLOR_BG = (20, 20, 30)
COLOR_PANEL = (15, 15, 22)
COLOR_HEADER = (22, 22, 30)
COLOR_BORDER = (35, 40, 60)
COLOR_TEXT = (230, 230, 240)
COLOR_SUBTEXT = (180, 180, 190)
COLOR_HILITE = (90, 160, 230)


def iso_coords_scaled(x: int, y: int, tw: int, th: int) -> Tuple[int, int]:
    sx = (x - y) * (tw // 2)
    sy = (x + y) * (th // 2)
    return sx, sy


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Terminaldofus - Iso Preview")
    clock = pygame.time.Clock()

    state = load_content_and_init()
    cam_x, cam_y = 0.0, 0.0
    scale = 1.2
    shake_timer = 0.0
    last_log_len = 0
    player_fx = float(state.player.position[0])
    player_fy = float(state.player.position[1])
    inventory_mode = False
    inv_tab = 0
    inv_sel = 0
    shop_mode = False
    shop_sel = 0
    shop_dialog = False
    shop_dialog_sel = 0  # 0 Buy, 1 Sell, 2 Leave
    sell_mode = False
    npc_dialog = False
    npc_dialog_text = ""
    merchant_dialog = False
    merchant_dialog_sel = 0
    merchant_dialog_text = ""
    merchant_stage = "greet"
    show_log = False
    profile_mode = False
    dragging_item = None
    dragging_mouse = (0, 0)
    # Draggable panel state
    inv_panel_w, inv_panel_h = 520, 300
    inv_panel_x, inv_panel_y = SCREEN_W - inv_panel_w - 16, 80
    inv_dragging = False
    inv_drag_offset = (0, 0)
    prof_panel_w, prof_panel_h = 680, 360
    prof_panel_x, prof_panel_y = SCREEN_W//2 - prof_panel_w//2, SCREEN_H//2 - prof_panel_h//2
    prof_dragging = False
    prof_drag_offset = (0, 0)
    movement_path: list[tuple[int, int]] = []
    preview_path: list[tuple[int, int]] = []
    last_hover: tuple[int, int] | None = None
    step_timer = 0.0
    step_interval = 0.15
    selected_ability = 1
    main_menu = True
    menu_sel = 0
    has_started = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if main_menu:
                    if event.key == pygame.K_UP:
                        menu_sel = (menu_sel - 1) % 3
                    elif event.key == pygame.K_DOWN:
                        menu_sel = (menu_sel + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if menu_sel == 0:
                            main_menu = False
                            has_started = True
                        elif menu_sel == 1:
                            pass
                        elif menu_sel == 2:
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        if has_started:
                            main_menu = False
                        else:
                            running = False
                    continue
                # When an NPC dialog is open, block all input except closing keys
                if npc_dialog:
                    if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        npc_dialog = False
                    continue
                if event.key == pygame.K_ESCAPE:
                    if npc_dialog:
                        npc_dialog = False
                        continue
                    if shop_mode:
                        shop_mode = False
                    elif inventory_mode:
                        inventory_mode = False
                    else:
                        # Toggle pause menu instead of quitting
                        if main_menu:
                            main_menu = False
                        else:
                            main_menu = True
                            menu_sel = 0
                        continue
                elif event.key == pygame.K_MINUS:
                    scale = max(0.6, scale - 0.1)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    scale = min(2.0, scale + 0.1)
                elif event.key == pygame.K_i:
                    if not shop_mode:
                        inventory_mode = not inventory_mode
                        inv_tab = 0
                        inv_sel = 0
                        sell_mode = False
                elif event.key == pygame.K_p:
                    if not (shop_mode or shop_dialog or npc_dialog or merchant_dialog):
                        profile_mode = not profile_mode
                elif event.key == pygame.K_h:
                    show_log = not show_log
                elif shop_dialog:
                    if event.key == pygame.K_UP:
                        shop_dialog_sel = (shop_dialog_sel - 1) % 3
                    elif event.key == pygame.K_DOWN:
                        shop_dialog_sel = (shop_dialog_sel + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if shop_dialog_sel == 0:
                            shop_dialog = False
                            shop_mode = True
                            shop_sel = 0
                        elif shop_dialog_sel == 1:
                            shop_dialog = False
                            # Enter sell mode (inventory overlay)
                            sell_mode = True
                            inventory_mode = True
                            inv_tab = 0
                            inv_sel = 0
                        else:
                            shop_dialog = False
                    elif event.key == pygame.K_ESCAPE:
                        shop_dialog = False
                        sell_mode = False
                elif merchant_dialog:
                    # Merchant dialogue with inline choices after greet
                    if merchant_stage == "greet":
                        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                            if event.key == pygame.K_RETURN:
                                merchant_stage = "choose"
                            else:
                                merchant_dialog = False
                        continue
                    elif merchant_stage == "choose":
                        if event.key == pygame.K_UP:
                            merchant_dialog_sel = (merchant_dialog_sel - 1) % 3
                        elif event.key == pygame.K_DOWN:
                            merchant_dialog_sel = (merchant_dialog_sel + 1) % 3
                        elif event.key == pygame.K_RETURN:
                            if merchant_dialog_sel == 0:
                                merchant_dialog = False
                                shop_mode = True
                                shop_sel = 0
                                merchant_stage = "greet"
                            elif merchant_dialog_sel == 1:
                                merchant_dialog = False
                                sell_mode = True
                                inventory_mode = True
                                inv_tab = 0
                                inv_sel = 0
                                merchant_stage = "greet"
                            else:
                                merchant_dialog = False
                                merchant_stage = "greet"
                        elif event.key == pygame.K_ESCAPE:
                            merchant_dialog = False
                            merchant_stage = "greet"
                        continue
                elif shop_mode:
                    # Shop navigation
                    # Find adjacent merchant
                    adj = None
                    for m in getattr(state, 'merchants', []):
                        if abs(state.player.position[0]-m.position[0]) + abs(state.player.position[1]-m.position[1]) == 1:
                            adj = m
                            break
                    if not adj:
                        shop_mode = False
                    else:
                        shop = load_shop(Path(__file__).resolve().parents[1] / 'content' / 'shops' / f"{adj.shop_id}.json")
                        if event.key == pygame.K_UP:
                            shop_sel = max(0, shop_sel - 1)
                        elif event.key == pygame.K_DOWN:
                            shop_sel = min(len(shop.items)-1, shop_sel + 1)
                        elif event.key == pygame.K_RETURN:
                            item_model = shop.items[shop_sel]
                            item = get_item_by_id(item_model.item_id)
                            if item and state.player.can_afford(item_model.price):
                                state.player.gold -= item_model.price
                                state.player.inventory.add_item(item)
                                state.log.entries.append(f"Bought {item.name} for {item_model.price}")
                elif inventory_mode:
                    # Inventory navigation (supports sell_mode)
                    cats = {
                        0: [it for it in state.player.inventory.items if hasattr(it, 'effect_type')],
                        1: [it for it in state.player.inventory.items if hasattr(it, 'weapon_type')],
                        2: [it for it in state.player.inventory.items if hasattr(it, 'slot') and not hasattr(it, 'weapon_type')],
                    }
                    if event.key == pygame.K_LEFT:
                        inv_tab = max(0, inv_tab - 1)
                        inv_sel = 0
                    elif event.key == pygame.K_RIGHT:
                        inv_tab = min(2, inv_tab + 1)
                        inv_sel = 0
                    elif event.key == pygame.K_UP:
                        items = cats.get(inv_tab, [])
                        if items:
                            inv_sel = max(0, inv_sel - 1)
                    elif event.key == pygame.K_DOWN:
                        items = cats.get(inv_tab, [])
                        if items:
                            inv_sel = min(len(items)-1, inv_sel + 1)
                    elif event.key == pygame.K_RETURN:
                        items = cats.get(inv_tab, [])
                        if inv_sel < len(items):
                            it = items[inv_sel]
                            if sell_mode:
                                # Sell one unit of selected item
                                price = max(1, getattr(it, 'value', 1) // 2)
                                state.player.add_gold(price)
                                state.player.inventory.remove_item(it.id, 1)
                                state.log.entries.append(f"Sold {it.name} for {price} gold")
                                # Refresh selection bounds
                                items = cats.get(inv_tab, [])
                                if inv_sel >= len(items):
                                    inv_sel = max(0, len(items) - 1)
                            else:
                                from .cli import use_item
                                use_item(state, it)
                    elif event.key == pygame.K_ESCAPE:
                        if sell_mode:
                            sell_mode = False
                            inventory_mode = False
                        else:
                            inventory_mode = False
                else:
                    # Isometric-friendly WASD mapping
                    # W: up (screen) => (-1, -1), S: down => (+1, +1)
                    # A: left => (-1, +1), D: right => (+1, -1)
                    if event.key in (pygame.K_w, pygame.K_z):
                        try_move(state, -1, -1)
                    elif event.key == pygame.K_s:
                        try_move(state, 1, 1)
                    elif event.key == pygame.K_a:
                        try_move(state, -1, 1)
                    elif event.key == pygame.K_d:
                        try_move(state, 1, -1)
                    elif event.key == pygame.K_1:
                        handle_ability_selection(state, 1)
                    elif event.key == pygame.K_2:
                        handle_ability_selection(state, 2)
                    elif event.key == pygame.K_3:
                        handle_ability_selection(state, 3)
                    elif event.key == pygame.K_e and state.in_combat and state.combat_state:
                        end_combat_turn(state.combat_state)
                    elif event.key == pygame.K_RETURN and not state.in_combat:
                        # Open shop if adjacent
                        adj = None
                        for m in getattr(state, 'merchants', []):
                            if abs(state.player.position[0]-m.position[0]) + abs(state.player.position[1]-m.position[1]) == 1:
                                adj = m
                                break
                        if adj:
                            merchant_dialog = True
                            merchant_dialog_text = "Welcome! Looking to trade?"
                            merchant_dialog_sel = 0
                            continue
                        if npc_dialog:
                            npc_dialog = False
                            continue
                        else:
                            # NPC dialogue if adjacent
                            near = None
                            for n in getattr(state, 'npcs', []) or []:
                                if abs(state.player.position[0]-n.position[0]) + abs(state.player.position[1]-n.position[1]) == 1:
                                    near = n
                                    break
                            if near:
                                npc_dialog = True
                                npc_dialog_text = "Hello, traveler. The dungeon awaits!"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                # Ability bar clicks removed per request
                if main_menu and event.button == 1:
                    col_x = SCREEN_W//2 - 100
                    col_w = 200
                    for i in range(3):
                        ry = 240 + i*36
                        rect = pygame.Rect(col_x, ry, col_w, 32)
                        if rect.collidepoint(mx, my):
                            menu_sel = i
                            if menu_sel == 0:
                                main_menu = False
                                if not has_started:
                                    has_started = True
                            elif menu_sel == 1:
                                pass
                            elif menu_sel == 2:
                                running = False
                            break
                if inventory_mode and event.button == 1:
                    inv_header = pygame.Rect(inv_panel_x, inv_panel_y, inv_panel_w, 28)
                    clicked_tab = False
                    if inv_header.collidepoint(mx, my):
                        font_tab = pygame.font.SysFont(None, 22)
                        tabs = ["Items", "Weapons", "Armor"]
                        xcur = inv_panel_x + 10
                        space_w = font_tab.size("  ")[0]
                        for i, t in enumerate(tabs):
                            label = f"[{t}]" if i == inv_tab else t
                            tw = font_tab.size(label)[0]
                            rect = pygame.Rect(xcur, inv_panel_y + 6, tw, 20)
                            if rect.collidepoint(mx, my):
                                inv_tab = i
                                inv_sel = 0
                                clicked_tab = True
                                break
                            xcur += tw + space_w
                    if inv_header.collidepoint(mx, my) and not clicked_tab:
                        inv_dragging = True
                        inv_drag_offset = (mx - inv_panel_x, my - inv_panel_y)
                    # Begin dragging item from list
                    list_y = inv_panel_y + 36
                    idx = (my - list_y) // 24
                    cats = {
                        0: [it for it in state.player.inventory.items if hasattr(it, 'effect_type')],
                        1: [it for it in state.player.inventory.items if hasattr(it, 'weapon_type')],
                        2: [it for it in state.player.inventory.items if hasattr(it, 'slot') and not hasattr(it, 'weapon_type')],
                    }
                    items = cats.get(inv_tab, [])
                    if 0 <= idx < len(items):
                        inv_sel = idx
                        dragging_item = items[idx]
                        dragging_mouse = (mx, my)
                if profile_mode and event.button == 1:
                    # Profile header drag
                    prof_header = pygame.Rect(prof_panel_x, prof_panel_y, prof_panel_w, 32)
                    if prof_header.collidepoint(mx, my):
                        prof_dragging = True
                        prof_drag_offset = (mx - prof_panel_x, my - prof_panel_y)
                if shop_mode and not shop_dialog and event.button == 1:
                    panel_w = 420
                    panel_h = 260
                    panel_x = 16
                    panel_y = 80
                    if pygame.Rect(panel_x, panel_y, panel_w, panel_h).collidepoint(mx, my):
                        list_y = panel_y + 36
                        idx = (my - list_y) // 24
                        if idx >= 0:
                            shop_sel = idx
                # World/combat click handling
                if state.in_combat and event.button == 1 and not (inventory_mode or profile_mode or shop_mode or npc_dialog):
                    mx, my = pygame.mouse.get_pos()
                    TW = max(16, int(TILE_W * scale))
                    TH = max(8, int(TILE_H * scale))
                    gx = int((my + cam_y - oy) / (TH / 2.0) + (mx + cam_x - ox) / (TW / 2.0)) // 2
                    gy = int((my + cam_y - oy) / (TH / 2.0) - (mx + cam_x - ox) / (TW / 2.0)) // 2
                    active_grid = state.combat_state.combat_grid if (state.in_combat and state.combat_state) else state.grid
                    if 0 <= gx < active_grid.width and 0 <= gy < active_grid.height and active_grid.walkable(gx, gy):
                        # Simple pathfinding to clicked tile
                        def h(a: tuple[int,int], b: tuple[int,int]) -> int:
                            return abs(a[0]-b[0]) + abs(a[1]-b[1])
                        start = state.player.position
                        goal = (gx, gy)
                        openq: list[tuple[int, tuple[int,int]]] = []
                        heapq.heappush(openq, (0, start))
                        came: dict[tuple[int,int], tuple[int,int] | None] = {start: None}
                        g: dict[tuple[int,int], int] = {start: 0}
                        occupied = set(m.position for m in (state.combat_state.monsters if (state.in_combat and state.combat_state) else []))
                        while openq:
                            _, cur = heapq.heappop(openq)
                            if cur == goal:
                                break
                            cx, cy = cur
                            for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                                if 0 <= nx < active_grid.width and 0 <= ny < active_grid.height and active_grid.walkable(nx, ny) and (nx, ny) not in occupied:
                                    ng = g[cur] + 1
                                    if (nx, ny) not in g or ng < g[(nx, ny)]:
                                        g[(nx, ny)] = ng
                                        pr = ng + h((nx, ny), goal)
                                        heapq.heappush(openq, (pr, (nx, ny)))
                                        came[(nx, ny)] = cur
                        if goal in came:
                            path: list[tuple[int,int]] = []
                            cur = goal
                            while cur != start:
                                path.append(cur)
                                cur = came[cur]  # type: ignore[index]
                            path.reverse()
                            if state.in_combat and state.combat_state:
                                mp_left = max(0, int(state.combat_state.player_mp))
                                movement_path = path[:mp_left] if mp_left > 0 else []
                            else:
                                movement_path = path
                            step_timer = 0.0
            # Mouse up: drop drag to equipment slots if profile open
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # stop panel drags
                inv_dragging = False
                prof_dragging = False
                # Handle drop to equip
                if dragging_item is not None and profile_mode:
                    mx, my = pygame.mouse.get_pos()
                    mid_x = prof_panel_x + 240
                    mid_y = prof_panel_y + 44
                    slot_rects = {
                        'weapon': pygame.Rect(mid_x, mid_y + 22, 220, 20),
                        'armor': pygame.Rect(mid_x, mid_y + 22*3, 220, 20),
                        'helmet': pygame.Rect(mid_x, mid_y + 22*4, 220, 20),
                        'boots': pygame.Rect(mid_x, mid_y + 22*5, 220, 20),
                    }
                    for slot, rect in slot_rects.items():
                        if rect.collidepoint(mx, my):
                            # Equip and manage inventory swap
                            if slot == 'weapon' and hasattr(dragging_item, 'weapon_type'):
                                prev = state.player.equipment.equip_item(dragging_item)
                                state.player.inventory.remove_item(dragging_item.id, 1)
                                if prev is not None:
                                    state.player.inventory.add_item(prev)
                                # progression expects weapon_type (e.g., 'staff')
                                state.player.progression.equipped_weapon = dragging_item.weapon_type
                                state.log.entries.append(f"Equipped {dragging_item.name} to Weapon")
                            elif slot in ('armor','helmet','boots') and hasattr(dragging_item, 'slot') and dragging_item.slot == slot:
                                prev = state.player.equipment.equip_item(dragging_item)
                                state.player.inventory.remove_item(dragging_item.id, 1)
                                if prev is not None:
                                    state.player.inventory.add_item(prev)
                                state.log.entries.append(f"Equipped {dragging_item.name} to {slot.title()}")
                            break
                if dragging_item is not None:
                    dragging_item = None
                    dragging_mouse = (0,0)
            if event.type == pygame.MOUSEMOTION:
                if main_menu:
                    mx, my = event.pos
                    col_x = SCREEN_W//2 - 100
                    col_w = 200
                    for i in range(3):
                        ry = 240 + i*36
                        rect = pygame.Rect(col_x, ry, col_w, 32)
                        if rect.collidepoint(mx, my):
                            menu_sel = i
                            break
                if inv_dragging:
                    mx, my = event.pos
                    inv_panel_x = max(0, min(SCREEN_W - inv_panel_w, mx - inv_drag_offset[0]))
                    inv_panel_y = max(0, min(SCREEN_H - inv_panel_h, my - inv_drag_offset[1]))
                if prof_dragging:
                    mx, my = event.pos
                    prof_panel_x = max(0, min(SCREEN_W - prof_panel_w, mx - prof_drag_offset[0]))
                    prof_panel_y = max(0, min(SCREEN_H - prof_panel_h, my - prof_drag_offset[1]))
                if dragging_item is not None:
                    # Update drag preview position
                    dragging_mouse = pygame.mouse.get_pos()

        screen.fill(COLOR_BG)

        if main_menu:
            title_font = pygame.font.SysFont(None, 64)
            small = pygame.font.SysFont(None, 26)
            title = title_font.render("Terminaldofus", True, (230, 230, 245))
            screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 120))
            opts = ["Start", "Settings", "Quit"]
            for i, label in enumerate(opts):
                color = (240, 240, 255) if i == menu_sel else (170, 175, 185)
                surf = small.render(label, True, color)
                screen.blit(surf, (SCREEN_W//2 - 40, 240 + i*36))
            hint = small.render("↑/↓ to navigate, Enter to select", True, (150, 150, 160))
            screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, 240 + 3*36 + 16))
            pygame.display.flip()
            clock.tick(60)
            continue
        
        # NPC dialog bubble will be drawn later without pausing the scene

        if shop_dialog:
            # Dim background
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))
            # Dialog panel
            panel_w, panel_h = 360, 200
            panel_x, panel_y = SCREEN_W//2 - panel_w//2, SCREEN_H//2 - panel_h//2
            pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(panel_x, panel_y, panel_w, panel_h))
            title = pygame.font.SysFont(None, 28).render("Merchant", True, (235, 235, 245))
            screen.blit(title, (panel_x + 12, panel_y + 10))
            opts = ["Buy", "Sell", "Leave"]
            for i, label in enumerate(opts):
                col = (240, 240, 255) if i == shop_dialog_sel else (175, 180, 190)
                surf = pygame.font.SysFont(None, 24).render(label, True, col)
                screen.blit(surf, (panel_x + 24, panel_y + 48 + i*32))
            hint = pygame.font.SysFont(None, 20).render("↑/↓ Select  Enter Confirm  Esc Close", True, (150, 150, 160))
            screen.blit(hint, (panel_x + 24, panel_y + panel_h - 32))
            pygame.display.flip()
            clock.tick(60)
            continue

        # Dynamic tile size with zoom
        TW = max(16, int(TILE_W * scale))
        TH = max(8, int(TILE_H * scale))

        # Smooth camera follow player
        px, py = state.player.position
        pcx, pcy = iso_coords_scaled(px, py, TW, TH)
        target_cam_x = pcx - SCREEN_W / 2
        target_cam_y = pcy - SCREEN_H / 2
        cam_x += (target_cam_x - cam_x) * 0.12
        cam_y += (target_cam_y - cam_y) * 0.12

        # Light screen shake on hit
        if len(state.log.entries) > last_log_len:
            line = state.log.entries[-1]
            if "deals" in line or "defeated" in line or "pushed" in line:
                shake_timer = 0.15
        last_log_len = len(state.log.entries)
        ox = oy = 0
        if shake_timer > 0:
            shake_timer -= 1 / 60
            ox = 3
            oy = -3

        # Draw grid tiles (combat grid in combat, world grid otherwise)
        active_grid = state.combat_state.combat_grid if (state.in_combat and state.combat_state) else state.grid
        for y in range(active_grid.height):
            for x in range(active_grid.width):
                sx, sy = iso_coords_scaled(x, y, TW, TH)
                sx = int(sx - cam_x + ox)
                sy = int(sy - cam_y + oy)
                color = (60, 70, 90)
                if (x, y) in active_grid.blocked:
                    color = (80, 30, 30)
                points = [
                    (sx, sy + TH // 2),
                    (sx + TW // 2, sy),
                    (sx + TW, sy + TH // 2),
                    (sx + TW // 2, sy + TH),
                ]
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (30, 30, 40), points, 1)

        # Tile highlight under mouse + preview path (use combat grid in combat)
        mx, my = pygame.mouse.get_pos()
        gx = int((my + cam_y - oy) / (TH / 2.0) + (mx + cam_x - ox) / (TW / 2.0)) // 2
        gy = int((my + cam_y - oy) / (TH / 2.0) - (mx + cam_x - ox) / (TW / 2.0)) // 2
        
        if 0 <= gx < active_grid.width and 0 <= gy < active_grid.height:
            sx, sy = iso_coords_scaled(gx, gy, TW, TH)
            sx = int(sx - cam_x + ox)
            sy = int(sy - cam_y + oy)
            poly = [
                (sx, sy + TH // 2),
                (sx + TW // 2, sy),
                (sx + TW, sy + TH // 2),
                (sx + TW // 2, sy + TH),
            ]
            pygame.draw.polygon(screen, (120, 120, 160), poly, 2)
            
            # Preview path if in combat, my turn, and have MP
            if (state.in_combat and state.combat_state and 
                state.combat_state.current_phase == "player_turn" and
                state.combat_state.player_mp > 0 and
                active_grid.walkable(gx, gy)):
                
                hover = (gx, gy)
                if hover != last_hover:
                    last_hover = hover
                    # Calculate preview path
                    def h(a: tuple[int,int], b: tuple[int,int]) -> int:
                        return abs(a[0]-b[0]) + abs(a[1]-b[1])
                    
                    start = state.player.position
                    goal = hover
                    openq: list[tuple[int, tuple[int,int]]] = []
                    heapq.heappush(openq, (0, start))
                    came: dict[tuple[int,int], tuple[int,int] | None] = {start: None}
                    g: dict[tuple[int,int], int] = {start: 0}
                    
                    while openq:
                        _, cur = heapq.heappop(openq)
                        if cur == goal:
                            break
                        cx, cy = cur
                        for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                            if 0 <= nx < active_grid.width and 0 <= ny < active_grid.height and active_grid.walkable(nx, ny):
                                ng = g[cur] + 1
                                if (nx, ny) not in g or ng < g[(nx, ny)]:
                                    g[(nx, ny)] = ng
                                    pr = ng + h((nx, ny), goal)
                                    heapq.heappush(openq, (pr, (nx, ny)))
                                    came[(nx, ny)] = cur
                    
                    if goal in came:
                        path: list[tuple[int,int]] = []
                        cur = goal
                        while cur != start:
                            path.append(cur)
                            cur = came[cur]  # type: ignore[index]
                        path.reverse()
                        preview_path = path[:max(0, int(state.combat_state.player_mp))]
                    else:
                        preview_path = []
            else:
                # Clear preview if conditions not met
                preview_path = []
                last_hover = None

        # Draw preview path (light blue, only if valid conditions)
        if (state.in_combat and state.combat_state and 
            state.combat_state.current_phase == "player_turn" and
            state.combat_state.player_mp > 0 and
            preview_path):
            for px, py in preview_path:
                sx, sy = iso_coords_scaled(px, py, TW, TH)
                sx = int(sx - cam_x + ox)
                sy = int(sy - cam_y + oy)
                pygame.draw.circle(screen, (80, 140, 230), (sx + TW // 2, sy + TH // 2), 8)

        # Draw movement path (darker blue dots for execution)
        if movement_path:
            for px, py in movement_path:
                sx, sy = iso_coords_scaled(px, py, TW, TH)
                sx = int(sx - cam_x + ox)
                sy = int(sy - cam_y + oy)
                pygame.draw.circle(screen, (80, 120, 200), (sx + TW // 2, sy + TH // 2), 8)

        # Draw merchants and NPCs (world only)
        if not state.in_combat:
            for m in getattr(state, 'merchants', []):
                sx, sy = iso_coords_scaled(*m.position, TW, TH)
                sx = int(sx - cam_x + ox)
                sy = int(sy - cam_y + oy)
                pygame.draw.ellipse(screen, (0, 0, 0), pygame.Rect(sx + TW // 2 - 10, sy + TH // 2 + 4, 20, 6))
                pygame.draw.circle(screen, (255, 215, 0), (sx + TW // 2, sy + TH // 2), max(6, int(10 * scale)))
            for n in getattr(state, 'npcs', []) or []:
                sx, sy = iso_coords_scaled(*n.position, TW, TH)
                sx = int(sx - cam_x + ox)
                sy = int(sy - cam_y + oy)
                pygame.draw.ellipse(screen, (0, 0, 0), pygame.Rect(sx + TW // 2 - 10, sy + TH // 2 + 4, 20, 6))
                pygame.draw.circle(screen, (80, 200, 80), (sx + TW // 2, sy + TH // 2), max(6, int(10 * scale)))
        
        # Draw monsters
        mons_to_draw = state.combat_state.monsters if (state.in_combat and state.combat_state) else state.monsters
        for mon in mons_to_draw:
            sx, sy = iso_coords_scaled(*mon.position, TW, TH)
            sx = int(sx - cam_x + ox)
            sy = int(sy - cam_y + oy)
            pygame.draw.ellipse(screen, (0, 0, 0), pygame.Rect(sx + TW // 2 - 9, sy + TH // 2 + 4, 18, 6))
            pygame.draw.circle(screen, (200, 60, 60), (sx + TW // 2, sy + TH // 2), max(6, int(10 * scale)))

        # Draw player
        sx, sy = iso_coords_scaled(*state.player.position, TW, TH)
        sx = int(sx - cam_x + ox)
        sy = int(sy - cam_y + oy)
        pygame.draw.ellipse(screen, (0, 0, 0), pygame.Rect(sx + TW // 2 - 10, sy + TH // 2 + 6, 22, 8))
        pygame.draw.circle(screen, (80, 200, 120), (sx + TW // 2, sy + TH // 2), max(8, int(12 * scale)))
        
        # Draw NPC dialog bubble overlay (non-blocking)
        if npc_dialog:
            draw_npc_dialog(screen, npc_dialog_text, SCREEN_W, SCREEN_H)

        # Draw Merchant dialog bubble overlay on top of map too
        if merchant_dialog:
            draw_merchant_dialog(screen, merchant_dialog_text, merchant_stage, merchant_dialog_sel, SCREEN_W, SCREEN_H)

        # HUD overlay with mini-map and quest stub
        font = pygame.font.SysFont(None, 22)
        hud_lines = []
        total = state.player.get_total_stats()
        adj_merch = False
        for m in getattr(state, 'merchants', []):
            if abs(state.player.position[0]-m.position[0]) + abs(state.player.position[1]-m.position[1]) == 1:
                adj_merch = True
                break
        if state.in_combat and state.combat_state and state.combat_state.monsters:
            mon = state.combat_state.monsters[0]
            hud_lines.append(f"COMBAT - Turn {state.combat_state.current_turn} | Phase: {state.combat_state.current_phase.upper()}")
            hud_lines.append(f"YOU HP {total.current_hp}/{total.hp} AP {state.combat_state.player_ap} MP {state.combat_state.player_mp}")
            hud_lines.append(f"ENEMY HP {mon.stats.current_hp}/{mon.stats.hp} AP {state.combat_state.monster_ap} MP {state.combat_state.monster_mp}")
        else:
            world_line = f"WORLD | HP {total.current_hp}/{total.hp} AP {total.ap} MP {total.current_mp}/{total.mp} | Gold {state.player.gold}"
            if adj_merch:
                world_line += " | Enter: Shop"
            hud_lines.append(world_line)
        hud_lines.append(f"Abilities: {abilities_bar(state)}")
        # Draw HUD background
        extra_h = 28
        hud_h = 20 * (len(hud_lines) + 1) + extra_h
        pygame.draw.rect(screen, COLOR_HEADER, pygame.Rect(0, 0, SCREEN_W, hud_h))
        y = 4
        for line in hud_lines:
            surf = font.render(line, True, (230, 230, 240))
            screen.blit(surf, (8, y))
            y += 20

        ap_curr = 0
        ap_max = max(1, total.ap)
        mp_curr = 0
        mp_max = max(1, total.mp)
        if state.in_combat and state.combat_state:
            ap_curr = max(0, int(state.combat_state.player_ap))
            mp_curr = max(0, int(state.combat_state.player_mp))
        else:
            ap_curr = max(0, int(total.ap))
            mp_curr = max(0, int(total.current_mp))
        bar_w = 240
        bar_h = 10
        ap_x = 8
        ap_y = hud_h - extra_h + 6
        mp_x = 8
        mp_y = ap_y + bar_h + 6
        pygame.draw.rect(screen, (30, 35, 50), pygame.Rect(ap_x, ap_y, bar_w, bar_h))
        pygame.draw.rect(screen, COLOR_HILITE, pygame.Rect(ap_x, ap_y, int(bar_w * (ap_curr / ap_max)), bar_h))
        pygame.draw.rect(screen, (30, 35, 50), pygame.Rect(mp_x, mp_y, bar_w, bar_h))
        pygame.draw.rect(screen, (80, 200, 120), pygame.Rect(mp_x, mp_y, int(bar_w * (mp_curr / mp_max)), bar_h))
        ap_label = pygame.font.SysFont(None, 18).render(f"AP {ap_curr}/{ap_max}", True, COLOR_TEXT)
        mp_label = pygame.font.SysFont(None, 18).render(f"MP {mp_curr}/{mp_max}", True, COLOR_TEXT)
        screen.blit(ap_label, (ap_x + bar_w + 10, ap_y - 3))
        screen.blit(mp_label, (mp_x + bar_w + 10, mp_y - 3))

        if state.in_combat and state.combat_state:
            phase = state.combat_state.current_phase
            label = "PLAYER TURN" if phase == "player_turn" else "ENEMY TURN"
            lc = (230, 230, 240) if phase == "player_turn" else (250, 180, 160)
            pill = pygame.font.SysFont(None, 22).render(label, True, lc)
            pad = 10
            pr = pygame.Rect(0, 0, pill.get_width() + pad * 2, pill.get_height() + 8)
            pr.centerx = SCREEN_W // 2
            pr.y = 6
            pygame.draw.rect(screen, (25, 28, 40), pr)
            pygame.draw.rect(screen, (70, 80, 110), pr, 1)
            screen.blit(pill, (pr.x + pad, pr.y + 4))

        # Ability bar removed per request

        # Profile panel (draggable)
        if profile_mode:
            draw_profile_panel(screen, state, prof_panel_x, prof_panel_y, prof_panel_w, prof_panel_h)
        # Draw dragging preview
        if dragging_item is not None:
            mx, my = pygame.mouse.get_pos()
            label = dragging_item.name
            surf = pygame.font.SysFont(None, 20).render(label, True, (230,230,240))
            pygame.draw.rect(screen, (20,20,28), surf.get_rect(center=(mx+1, my+1)))
            screen.blit(surf, (mx+8, my))

        # Mini-map (top-right)
        mm_w, mm_h = 180, 140
        mm_x, mm_y = SCREEN_W - mm_w - 12, 12
        pygame.draw.rect(screen, (14, 14, 22), pygame.Rect(mm_x, mm_y, mm_w, mm_h))
        grid_w, grid_h = active_grid.width, active_grid.height
        sx = max(1, mm_w // max(1, grid_w))
        sy = max(1, mm_h // max(1, grid_h))
        for y0 in range(grid_h):
            for x0 in range(grid_w):
                col = (40, 50, 70)
                if (x0, y0) in active_grid.blocked:
                    col = (70, 40, 40)
                rx = mm_x + x0 * sx
                ry = mm_y + y0 * sy
                pygame.draw.rect(screen, col, pygame.Rect(rx, ry, sx, sy))
        # player dot
        px0, py0 = state.player.position
        pygame.draw.rect(screen, (80, 220, 120), pygame.Rect(mm_x + px0 * sx, mm_y + py0 * sy, max(2, sx), max(2, sy)))
        # merchants on minimap (world only)
        if not state.in_combat:
            for m in getattr(state, 'merchants', []):
                mx0, my0 = m.position
                pygame.draw.rect(screen, (240, 200, 60), pygame.Rect(mm_x + mx0 * sx, mm_y + my0 * sy, max(2, sx), max(2, sy)))
            for n in getattr(state, 'npcs', []) or []:
                nx0, ny0 = n.position
                pygame.draw.rect(screen, (80, 200, 80), pygame.Rect(mm_x + nx0 * sx, mm_y + ny0 * sy, max(2, sx), max(2, sy)))

        



        # Step along movement path over time (combat only)
        dt = clock.get_time() / 1000.0
        step_timer += dt
        if movement_path and step_timer >= step_interval and state.in_combat and state.combat_state:
            if state.combat_state.player_mp > 0:
                step_timer = 0.0
                nx, ny = movement_path.pop(0)
                state.player.position = (nx, ny)
                state.combat_state.player_mp -= 1
                if state.combat_state.player_mp <= 0:
                    movement_path = []
            else:
                movement_path = []

        # No pixel world movement; keyboard moves are tile-based via try_move above
        # Combat always shows the log; otherwise obey toggle
        want_log = state.in_combat or show_log
        if want_log:
            log_lines = state.log.entries[-5:] if hasattr(state, 'log') else []
            ly = SCREEN_H - 20 * (len(log_lines) + 1)
            pygame.draw.rect(screen, (10, 10, 15), pygame.Rect(0, ly - 4, SCREEN_W, SCREEN_H - ly + 4))
            y = ly
            for entry in log_lines:
                surf = font.render(entry, True, (200, 200, 210))
                screen.blit(surf, (8, y))
                y += 20

        # Inventory panel (draggable)
        if inventory_mode:
            draw_inventory_panel(screen, state, inv_panel_x, inv_panel_y, inv_panel_w, inv_panel_h, inv_tab, inv_sel, sell_mode)

        # Shop panel (Buy mode)
        if shop_mode and not shop_dialog:
            draw_shop_panel(screen, state, 16, 80, 420, 260, shop_sel)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())


