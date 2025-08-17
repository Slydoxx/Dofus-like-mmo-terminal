from __future__ import annotations

import sys
from typing import Tuple

import pygame

from .game_loop import load_content_and_init, try_move, handle_ability_selection, end_combat_turn, abilities_bar, cast_ability_at
from ..engine.ability import Ability
from ..engine.content import load_shop
from ..engine.inventory import get_item_by_id
from pathlib import Path
import heapq


TILE_W = 64
TILE_H = 24
SCREEN_W = 1024
SCREEN_H = 768


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
    movement_path: list[tuple[int, int]] = []
    preview_path: list[tuple[int, int]] = []
    last_hover: tuple[int, int] | None = None
    step_timer = 0.0
    step_interval = 0.15
    selected_ability = 1
    main_menu = True
    menu_sel = 0

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
                        elif menu_sel == 1:
                            pass
                        elif menu_sel == 2:
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    continue
                if event.key == pygame.K_ESCAPE:
                    if shop_mode:
                        shop_mode = False
                    elif inventory_mode:
                        inventory_mode = False
                    else:
                        running = False
                elif event.key == pygame.K_MINUS:
                    scale = max(0.6, scale - 0.1)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    scale = min(2.0, scale + 0.1)
                elif event.key == pygame.K_i:
                    if not shop_mode:
                        inventory_mode = not inventory_mode
                        inv_tab = 0
                        inv_sel = 0
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
                    # Inventory navigation
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
                            from .cli import use_item
                            use_item(state, items[inv_sel])
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
                            shop_mode = True
                            shop_sel = 0
            elif event.type == pygame.MOUSEBUTTONDOWN and not (inventory_mode or shop_mode):
                if state.in_combat and event.button == 1:
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
            # ignore mouse up for world movement

        screen.fill((20, 20, 30))

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

        # Draw merchants
        if not state.in_combat:
            for m in getattr(state, 'merchants', []):
                sx, sy = iso_coords_scaled(*m.position, TW, TH)
                sx = int(sx - cam_x + ox)
                sy = int(sy - cam_y + oy)
                pygame.draw.ellipse(screen, (0, 0, 0), pygame.Rect(sx + TW // 2 - 10, sy + TH // 2 + 4, 20, 6))
                pygame.draw.circle(screen, (255, 215, 0), (sx + TW // 2, sy + TH // 2), max(6, int(10 * scale)))
        
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
        hud_h = 20 * (len(hud_lines) + 1)
        pygame.draw.rect(screen, (10, 10, 15), pygame.Rect(0, 0, SCREEN_W, hud_h))
        y = 4
        for line in hud_lines:
            surf = font.render(line, True, (230, 230, 240))
            screen.blit(surf, (8, y))
            y += 20

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

        # Key hints footer
        footer = pygame.font.SysFont(None, 20)
        hints = "WASD move  |  I inventory  |  Enter shop  |  E end turn  |  +/- zoom"
        sh = footer.render(hints, True, (170, 175, 185))
        screen.blit(sh, (SCREEN_W//2 - sh.get_width()//2, SCREEN_H - 24))



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
        # Log (last 5 entries)
        log_lines = state.log.entries[-5:] if hasattr(state, 'log') else []
        ly = SCREEN_H - 20 * (len(log_lines) + 1)
        pygame.draw.rect(screen, (10, 10, 15), pygame.Rect(0, ly - 4, SCREEN_W, SCREEN_H - ly + 4))
        y = ly
        for entry in log_lines:
            surf = font.render(entry, True, (200, 200, 210))
            screen.blit(surf, (8, y))
            y += 20

        # Inventory panel
        if inventory_mode:
            panel_w = 520
            panel_h = 300
            panel_x = SCREEN_W - panel_w - 16
            panel_y = 80
            pygame.draw.rect(screen, (15, 15, 22), pygame.Rect(panel_x, panel_y, panel_w, panel_h))
            tabs = ["Items", "Weapons", "Armor"]
            tab_text = "  ".join([("["+t+"]") if i == inv_tab else t for i, t in enumerate(tabs)])
            screen.blit(font.render(tab_text, True, (220, 220, 230)), (panel_x + 10, panel_y + 8))
            cats = {
                0: [it for it in state.player.inventory.items if hasattr(it, 'effect_type')],
                1: [it for it in state.player.inventory.items if hasattr(it, 'weapon_type')],
                2: [it for it in state.player.inventory.items if hasattr(it, 'slot') and not hasattr(it, 'weapon_type')],
            }
            items = cats.get(inv_tab, [])
            list_y = panel_y + 36
            for i, it in enumerate(items[:10]):
                mark = ">" if i == inv_sel else " "
                qty = getattr(it, 'quantity', 1)
                line = f"{mark} {it.name} x{qty}"
                screen.blit(font.render(line, True, (230, 230, 240)), (panel_x + 10, list_y))
                list_y += 24
            info_y = panel_y + 36
            info_x = panel_x + 280
            if items and inv_sel < len(items):
                it = items[inv_sel]
                screen.blit(font.render(it.description, True, (200, 200, 210)), (info_x, info_y)); info_y += 24
                screen.blit(font.render(f"Qty {getattr(it,'quantity',1)}", True, (200,200,210)), (info_x, info_y)); info_y += 24
                if hasattr(it, 'weapon_type'):
                    screen.blit(font.render(f"Type {it.weapon_type} Dmg {it.base_damage}", True, (200, 200, 210)), (info_x, info_y)); info_y += 24
                elif hasattr(it, 'slot'):
                    screen.blit(font.render(f"Slot {it.slot}", True, (200, 200, 210)), (info_x, info_y)); info_y += 24
                elif hasattr(it, 'effect_type'):
                    screen.blit(font.render(f"{it.effect_type} {it.effect_value}", True, (200, 200, 210)), (info_x, info_y)); info_y += 24
                screen.blit(font.render(f"Weight {it.weight} Value {it.value}", True, (200, 200, 210)), (info_x, info_y)); info_y += 24
                screen.blit(font.render("Enter: Use/Equip  Esc: Close", True, (180, 180, 190)), (info_x, info_y))

        # Shop panel
        if shop_mode:
            panel_w = 420
            panel_h = 260
            panel_x = 16
            panel_y = 80
            pygame.draw.rect(screen, (15, 15, 22), pygame.Rect(panel_x, panel_y, panel_w, panel_h))
            adj = None
            for m in getattr(state, 'merchants', []):
                if abs(state.player.position[0]-m.position[0]) + abs(state.player.position[1]-m.position[1]) == 1:
                    adj = m
                    break
            if adj:
                shop = load_shop(Path(__file__).resolve().parents[1] / 'content' / 'shops' / f"{adj.shop_id}.json")
                screen.blit(font.render(shop.name, True, (230, 230, 240)), (panel_x + 10, panel_y + 8))
                ylist = panel_y + 36
                for i, it in enumerate(shop.items[:10]):
                    mark = ">" if i == shop_sel else " "
                    line = f"{mark} {it.item_id} - {it.price} gold"
                    screen.blit(font.render(line, True, (230, 230, 240)), (panel_x + 10, ylist))
                    ylist += 24
                screen.blit(font.render("Enter: Buy  Esc: Close", True, (180, 180, 190)), (panel_x + 10, panel_y + panel_h - 28))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())


