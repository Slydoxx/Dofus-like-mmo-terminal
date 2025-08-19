from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional


class Element(str, Enum):
    F = "F"
    E = "E"
    A = "A"
    T = "T"
    L = "L"
    R = "R"


class Directive(str, Enum):
    HOLD = "hold"
    SKIRMISH = "skirmish"
    ASSAULT = "assault"
    ANCHOR = "anchor"
    SUPPORT = "support"


class Reaction(str, Enum):
    INTERCEPT = "intercept"
    OVERWATCH = "overwatch"
    DISPLACE = "displace"
    COUNTERCAST = "countercast"


class StateKind(str, Enum):
    IGNITE = "ignite"
    SOAK = "soak"
    GUST = "gust"
    ANCHOR = "anchor"
    CHARGED = "charged"
    SILENCED = "silenced"
    EXPOSED = "exposed"
    DAZED = "dazed"


@dataclass
class State:
    kind: StateKind
    duration_beats: int


@dataclass
class UnitStats:
    hp: int
    atk: int
    df: int
    spd: int
    wis: int
    pow: int


@dataclass
class Unit:
    id: str
    name: str
    element: Element
    stats: UnitStats
    position: Tuple[int, int]
    states: List[State] = field(default_factory=list)
    directive: Directive = Directive.HOLD
    focus: int = 0
    ap: int = 0


@dataclass
class TeamPool:
    rp: int = 0
    ct: int = 0
    mom: int = 0


@dataclass
class RoundState:
    beat: int = 1
    initiative_tokens: dict[str, int] = field(default_factory=dict)
    reaction_window_open: bool = False
    log: List[str] = field(default_factory=list)
    team_pool: TeamPool = field(default_factory=TeamPool)
    allies: List[Unit] = field(default_factory=list)
    enemies: List[Unit] = field(default_factory=list)
    grid_size: Tuple[int, int] = (20, 14)

