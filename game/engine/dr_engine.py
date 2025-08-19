from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

from .dr_types import RoundState, Unit, Directive, State, StateKind


def allocate_initiative_tokens(state: RoundState) -> None:
    state.initiative_tokens.clear()
    for u in state.allies + state.enemies:
        tokens = 1 + max(0, u.stats.spd // 20)
        state.initiative_tokens[u.id] = tokens


def start_round(state: RoundState) -> None:
    state.beat = 1
    allocate_initiative_tokens(state)
    state.team_pool.rp = min(2, state.team_pool.rp + 1)
    state.team_pool.ct = min(2, state.team_pool.ct + 1)
    state.log.append("Round start")


def begin_beat(state: RoundState) -> None:
    state.reaction_window_open = False
    state.log.append(f"Beat {state.beat} begin")


def end_beat(state: RoundState) -> None:
    state.reaction_window_open = True
    state.log.append(f"Beat {state.beat} reactions")


def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_towards(src: Tuple[int, int], dst: Tuple[int, int]) -> Tuple[int, int]:
    x, y = src
    dx = 0 if x == dst[0] else (1 if dst[0] > x else -1)
    dy = 0 if y == dst[1] else (1 if dst[1] > y else -1)
    if abs(dst[0] - x) >= abs(dst[1] - y):
        return (x + dx, y)
    return (x, y + dy)


def _find_nearest(src: Tuple[int, int], targets: List[Unit]) -> Optional[Unit]:
    if not targets:
        return None
    return min(targets, key=lambda t: _dist(src, t.position))


def _has_los(src: Tuple[int, int], dst: Tuple[int, int]) -> bool:
    return True


def _add_state(u: Unit, kind: StateKind, duration: int) -> None:
    if len(u.states) >= 3:
        return
    u.states.append(State(kind=kind, duration_beats=duration))


def _has_state(u: Unit, kind: StateKind) -> bool:
    return any(s.kind == kind for s in u.states)


def _compute_damage(attacker: Unit, defender: Unit, base: int) -> int:
    raw = int(base * (1 + attacker.stats.pow / 100))
    mitig = int(raw * (1 - defender.stats.df / (100 + defender.stats.df)))
    mod = 0.0
    if _has_state(defender, StateKind.EXPOSED):
        pass
    if _has_state(defender, StateKind.IGNITE):
        pass
    if _has_state(defender, StateKind.SOAK):
        pass
    if _has_state(defender, StateKind.GUST):
        pass
    if _has_state(defender, StateKind.CHARGED):
        pass
    if _has_state(defender, StateKind.SILENCED):
        pass
    if _has_state(defender, StateKind.ANCHOR):
        pass
    if _has_state(defender, StateKind.DAZED):
        pass
    if _has_state(defender, StateKind.EXPOSED):
        mod += 0.3
    if _has_state(defender, StateKind.IGNITE):
        mod += 0.0
    if _has_state(defender, StateKind.SOAK):
        mod += 0.0
    if _has_state(defender, StateKind.CHARGED):
        mod += 0.0
    if _has_state(defender, StateKind.GUST):
        mod += 0.0
    if _has_state(defender, StateKind.ANCHOR):
        mod += 0.0
    if _has_state(defender, StateKind.DAZED):
        mod += 0.0
    mod = max(-0.4, min(0.4, mod))
    total = int(mitig * (1 + mod))
    return max(1, total)


def _attack(state: RoundState, attacker: Unit, defender: Unit, ranged: bool = False) -> None:
    base = attacker.stats.atk
    dmg = _compute_damage(attacker, defender, base)
    defender.stats.hp = max(0, defender.stats.hp - dmg)
    state.log.append(f"{attacker.name} hits {defender.name} for {dmg}")
    if attacker.name.lower().startswith("sharp"):
        _add_state(defender, StateKind.EXPOSED, 1)
        state.log.append(f"{defender.name} is Exposed")
    if defender.stats.hp <= 0:
        state.log.append(f"{defender.name} falls")


def resolve_unit_action(state: RoundState, unit: Unit) -> None:
    if state.initiative_tokens.get(unit.id, 0) <= 0:
        return
    state.initiative_tokens[unit.id] -= 1
    unit.ap = 2
    if unit.directive == Directive.ANCHOR:
        unit.ap = 1
    state.log.append(f"{unit.name} acts ({unit.directive})")
    foes = state.enemies if unit in state.allies else state.allies
    if not foes:
        return
    target = _find_nearest(unit.position, foes)
    if target is None:
        return
    if unit.directive == Directive.ASSAULT:
        if _dist(unit.position, target.position) > 1 and unit.ap > 0:
            unit.position = _step_towards(unit.position, target.position)
            unit.ap -= 1
            state.log.append(f"{unit.name} moves")
        if _dist(unit.position, target.position) == 1 and unit.ap > 0:
            _attack(state, unit, target, ranged=False)
            unit.ap = 0
    elif unit.directive == Directive.SKIRMISH:
        if _has_los(unit.position, target.position) and _dist(unit.position, target.position) <= 4 and unit.ap > 0:
            _attack(state, unit, target, ranged=True)
            unit.ap = 0
        elif unit.ap > 0:
            unit.position = _step_towards(unit.position, target.position)
            unit.ap -= 1
            state.log.append(f"{unit.name} repositions")
    elif unit.directive == Directive.SUPPORT:
        allies = state.allies if unit in state.allies else state.enemies
        weakest = min(allies, key=lambda a: a.stats.hp)
        if weakest.stats.hp < 100 and unit.ap > 0:
            healed = 5 + unit.stats.wis // 2
            weakest.stats.hp = min(weakest.stats.hp + healed, 100)
            state.log.append(f"{unit.name} heals {weakest.name} for {healed}")
            unit.ap = 0
    elif unit.directive == Directive.ANCHOR:
        pass
    else:
        pass


def resolve_beat(state: RoundState) -> None:
    ordered: List[Unit] = sorted(state.allies + state.enemies, key=lambda u: u.stats.spd, reverse=True)
    for u in ordered:
        resolve_unit_action(state, u)
    end_beat(state)
    state.beat += 1


def cleanup(state: RoundState) -> None:
    for u in state.allies + state.enemies:
        new_states: List = []
        for s in u.states:
            if s.duration_beats > 1:
                s.duration_beats -= 1
                new_states.append(s)
        u.states = new_states
    state.log.append("Cleanup")


def run_one_round(state: RoundState) -> None:
    start_round(state)
    for _ in range(3):
        begin_beat(state)
        resolve_beat(state)
    cleanup(state)

