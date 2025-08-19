from __future__ import annotations

import pygame

from .theme import (
    COLOR_BG,
    COLOR_PANEL,
    COLOR_HEADER,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_SUBTEXT,
    COLOR_HILITE,
)


def draw_inventory_panel(screen: pygame.Surface, state, x: int, y: int, w: int, h: int, inv_tab: int, inv_sel: int, sell_mode: bool) -> None:
    pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(x, y, w, h))
    pygame.draw.rect(screen, COLOR_HEADER, pygame.Rect(x, y, w, 28))
    font = pygame.font.SysFont(None, 22)
    header = pygame.font.SysFont(None, 22)
    tabs = ["Items", "Weapons", "Armor"]
    tab_text = "  ".join([("["+t+"]") if i == inv_tab else t for i, t in enumerate(tabs)])
    if sell_mode:
        tab_text += "   (Sell mode)"
    screen.blit(header.render(tab_text, True, COLOR_TEXT), (x + 10, y + 6))

    cats = {
        0: [it for it in state.player.inventory.items if hasattr(it, 'effect_type')],
        1: [it for it in state.player.inventory.items if hasattr(it, 'weapon_type')],
        2: [it for it in state.player.inventory.items if hasattr(it, 'slot') and not hasattr(it, 'weapon_type')],
    }
    items = cats.get(inv_tab, [])
    list_y = y + 36
    for i, it in enumerate(items[:10]):
        mark = ">" if i == inv_sel else " "
        qty = getattr(it, 'quantity', 1)
        val = getattr(it, 'value', 0)
        if sell_mode:
            sell_price = max(1, val // 2)
            line = f"{mark} {it.name} x{qty}  [{sell_price}g]"
        else:
            line = f"{mark} {it.name} x{qty}"
        screen.blit(font.render(line, True, COLOR_TEXT), (x + 10, list_y))
        list_y += 24

    info_y = y + 36
    info_x = x + 280
    if items and inv_sel < len(items):
        it = items[inv_sel]
        screen.blit(font.render(it.description, True, COLOR_SUBTEXT), (info_x, info_y)); info_y += 24
        screen.blit(font.render(f"Qty {getattr(it,'quantity',1)}", True, COLOR_SUBTEXT), (info_x, info_y)); info_y += 24
        if hasattr(it, 'weapon_type'):
            screen.blit(font.render(f"Type {it.weapon_type} Dmg {it.base_damage}", True, COLOR_SUBTEXT), (info_x, info_y)); info_y += 24
        elif hasattr(it, 'slot'):
            screen.blit(font.render(f"Slot {it.slot}", True, COLOR_SUBTEXT), (info_x, info_y)); info_y += 24
        elif hasattr(it, 'effect_type'):
            screen.blit(font.render(f"{it.effect_type} {it.effect_value}", True, COLOR_SUBTEXT), (info_x, info_y)); info_y += 24
        screen.blit(font.render(f"Weight {it.weight} Value {it.value}", True, COLOR_SUBTEXT), (info_x, info_y)); info_y += 24
        if sell_mode:
            sp = max(1, getattr(it,'value',0)//2)
            screen.blit(font.render(f"Sell: {sp} gold (Enter to sell 1)", True, COLOR_SUBTEXT), (info_x, info_y))
        else:
            screen.blit(font.render("Enter: Use/Equip  Esc: Close", True, COLOR_SUBTEXT), (info_x, info_y))


def draw_profile_panel(screen: pygame.Surface, state, x: int, y: int, w: int, h: int) -> None:
    pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(x, y, w, h))
    pygame.draw.rect(screen, COLOR_HEADER, pygame.Rect(x, y, w, 32))
    title = pygame.font.SysFont(None, 26).render("Profile", True, COLOR_TEXT)
    screen.blit(title, (x + 12, y + 6))

    total = state.player.get_total_stats()
    # Identity & Stats
    sleft_x = x + 16
    sleft_y = y + 44
    f24 = pygame.font.SysFont(None, 24)
    f22 = pygame.font.SysFont(None, 22)
    screen.blit(f24.render(f"Name: {state.player.name}", True, COLOR_TEXT), (sleft_x, sleft_y)); sleft_y += 26
    screen.blit(f24.render(f"Gold: {state.player.gold}", True, COLOR_TEXT), (sleft_x, sleft_y)); sleft_y += 26
    for lab, val in [("HP", f"{total.current_hp}/{total.hp}"), ("AP", total.ap), ("MP", total.mp), ("ATK", total.atk), ("RES", total.res), ("ARMOR", total.armor)]:
        screen.blit(f22.render(f"{lab}: {val}", True, COLOR_SUBTEXT), (sleft_x, sleft_y)); sleft_y += 22

    # Equipment
    mid_x = x + 240
    mid_y = y + 44
    screen.blit(f24.render("Equipment", True, COLOR_TEXT), (mid_x, mid_y)); mid_y += 26
    eq = state.player.equipment
    weapon_name = eq.weapon.name if eq.weapon else "None"
    screen.blit(f22.render(f"Weapon: {weapon_name}", True, COLOR_SUBTEXT), (mid_x, mid_y)); mid_y += 22
    if eq.weapon:
        from ..game_loop import get_abilities_for_weapon
        abs_list = [a.name for a in get_abilities_for_weapon(eq.weapon.weapon_type)][:3]
        screen.blit(pygame.font.SysFont(None, 20).render("Abilities: " + ", ".join(abs_list), True, COLOR_SUBTEXT), (mid_x+10, mid_y)); mid_y += 22
    for slot, item in [("Armor", eq.armor), ("Helmet", eq.helmet), ("Boots", eq.boots)]:
        name = item.name if item else "None"
        screen.blit(f22.render(f"{slot}: {name}", True, COLOR_SUBTEXT), (mid_x, mid_y)); mid_y += 22
    # Drop slot hints
    for slot, yoff in [("weapon", 22), ("armor", 22*3), ("helmet", 22*4), ("boots", 22*5)]:
        r = pygame.Rect(mid_x, (y + 44) + yoff, 220, 20)
        pygame.draw.rect(screen, COLOR_BORDER, r, 1)

    # Weight
    wt = state.player.inventory.total_weight
    wtxt = pygame.font.SysFont(None, 20).render(f"Weight: {wt:.1f}/{state.player.inventory.max_weight}", True, COLOR_SUBTEXT)
    screen.blit(wtxt, (x + 16, y + h - 30))

    # Weapon skills
    right_x = x + 430
    right_y = y + 44
    screen.blit(f24.render("Weapon Skills", True, COLOR_TEXT), (right_x, right_y)); right_y += 30
    ws = state.player.progression.weapon_skills
    bars = [("Melee", ws.melee_damage), ("Ranged", ws.ranged_damage), ("Magic", ws.magic_damage)]
    for label, val in bars:
        bar_w = 200
        pygame.draw.rect(screen, (40,45,60), pygame.Rect(right_x, right_y, bar_w, 16))
        fill = int(min(1.0, val/100.0) * bar_w)
        pygame.draw.rect(screen, COLOR_HILITE, pygame.Rect(right_x, right_y, fill, 16))
        lab = pygame.font.SysFont(None, 20).render(f"{label}: {val}", True, COLOR_SUBTEXT)
        screen.blit(lab, (right_x + bar_w + 10, right_y - 2))
        right_y += 24


def draw_shop_panel(screen: pygame.Surface, state, x: int, y: int, w: int, h: int, shop_sel: int) -> None:
    pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(x, y, w, h))
    font = pygame.font.SysFont(None, 22)
    # Find adjacent merchant
    adj = None
    for m in getattr(state, 'merchants', []):
        if abs(state.player.position[0]-m.position[0]) + abs(state.player.position[1]-m.position[1]) == 1:
            adj = m
            break
    if not adj:
        return
    from ...engine.content import load_shop
    from pathlib import Path
    shop = load_shop(Path(__file__).resolve().parents[2] / 'content' / 'shops' / f"{adj.shop_id}.json")
    screen.blit(font.render(shop.name, True, COLOR_TEXT), (x + 10, y + 8))
    ylist = y + 36
    for i, it in enumerate(shop.items[:10]):
        mark = ">" if i == shop_sel else " "
        line = f"{mark} {it.item_id} - {it.price} gold"
        screen.blit(font.render(line, True, COLOR_TEXT), (x + 10, ylist))
        ylist += 24
    screen.blit(font.render("Enter: Buy  Esc: Close (Tab: Sell soon)", True, COLOR_SUBTEXT), (x + 10, y + h - 28))


def draw_npc_dialog(screen: pygame.Surface, text: str, screen_w: int, screen_h: int) -> None:
    panel_w, panel_h = 520, 160
    panel_x, panel_y = screen_w//2 - panel_w//2, screen_h - panel_h - 60
    pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(panel_x, panel_y, panel_w, panel_h))
    speaker = pygame.font.SysFont(None, 24).render("NPC:", True, COLOR_TEXT)
    # Simple word wrap
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    font24 = pygame.font.SysFont(None, 24)
    for w in words:
        test = (cur + " " + w).strip()
        if font24.size(test)[0] > panel_w - 24:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    screen.blit(speaker, (panel_x + 12, panel_y + 12))
    y_text = panel_y + 44
    for ln in lines[:4]:
        surf = font24.render(ln, True, COLOR_TEXT)
        screen.blit(surf, (panel_x + 12, y_text))
        y_text += 26
    hint = pygame.font.SysFont(None, 20).render("Enter/Esc to close", True, COLOR_SUBTEXT)
    screen.blit(hint, (panel_x + panel_w - 180, panel_y + panel_h - 28))


def draw_merchant_dialog(screen: pygame.Surface, text: str, stage: str, sel: int, screen_w: int, screen_h: int) -> None:
    panel_w, panel_h = 520, 180
    panel_x, panel_y = screen_w//2 - panel_w//2, screen_h - panel_h - 60
    pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(panel_x, panel_y, panel_w, panel_h))
    speaker = pygame.font.SysFont(None, 24).render("Merchant:", True, COLOR_TEXT)
    msg = pygame.font.SysFont(None, 24).render(text, True, COLOR_TEXT)
    screen.blit(speaker, (panel_x + 12, panel_y + 12))
    screen.blit(msg, (panel_x + 12, panel_y + 44))
    if stage == "greet":
        hint = pygame.font.SysFont(None, 20).render("Enter: Continue  Esc: Close", True, COLOR_SUBTEXT)
        screen.blit(hint, (panel_x + panel_w - 200, panel_y + panel_h - 28))
    else:
        opts = ["Buy", "Sell", "Leave"]
        for i, label in enumerate(opts):
            col = COLOR_TEXT if i == sel else COLOR_SUBTEXT
            surf = pygame.font.SysFont(None, 24).render(label, True, col)
            screen.blit(surf, (panel_x + 24, panel_y + 80 + i*26))


def draw_portal_dialog(screen: pygame.Surface, screen_w: int, screen_h: int) -> None:
    panel_w, panel_h = 520, 140
    panel_x, panel_y = screen_w//2 - panel_w//2, screen_h - panel_h - 60
    pygame.draw.rect(screen, COLOR_PANEL, pygame.Rect(panel_x, panel_y, panel_w, panel_h))
    title = pygame.font.SysFont(None, 24).render("Portal", True, COLOR_TEXT)
    msg = pygame.font.SysFont(None, 24).render("Enter to open portal menu (WIP)", True, COLOR_TEXT)
    screen.blit(title, (panel_x + 12, panel_y + 12))
    screen.blit(msg, (panel_x + 12, panel_y + 48))
    hint = pygame.font.SysFont(None, 20).render("Enter/Esc to close", True, COLOR_SUBTEXT)
    screen.blit(hint, (panel_x + panel_w - 180, panel_y + panel_h - 28))
