from __future__ import annotations

from game.engine.dr_types import RoundState, Unit, UnitStats, Element, Directive
from game.engine.dr_engine import run_one_round


def main() -> None:
    a1 = Unit(id="a1", name="Vanguard", element=Element.T, stats=UnitStats(hp=100, atk=10, df=15, spd=22, wis=5, pow=5), position=(5, 5), directive=Directive.ASSAULT)
    a2 = Unit(id="a2", name="Sharpshooter", element=Element.L, stats=UnitStats(hp=80, atk=12, df=8, spd=35, wis=6, pow=7), position=(6, 6), directive=Directive.SKIRMISH)
    a3 = Unit(id="a3", name="Arcanist", element=Element.R, stats=UnitStats(hp=70, atk=8, df=7, spd=18, wis=12, pow=10), position=(7, 6), directive=Directive.SUPPORT)

    e1 = Unit(id="e1", name="Brute", element=Element.T, stats=UnitStats(hp=90, atk=11, df=12, spd=15, wis=3, pow=4), position=(12, 6))
    e2 = Unit(id="e2", name="Slinger", element=Element.A, stats=UnitStats(hp=70, atk=9, df=7, spd=28, wis=4, pow=6), position=(12, 8))
    e3 = Unit(id="e3", name="Adept", element=Element.R, stats=UnitStats(hp=75, atk=10, df=8, spd=20, wis=10, pow=11), position=(13, 7))

    st = RoundState(allies=[a1, a2, a3], enemies=[e1, e2, e3])
    run_one_round(st)
    for line in st.log:
        print(line)


if __name__ == "__main__":
    main()


