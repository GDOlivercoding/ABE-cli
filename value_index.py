from __future__ import annotations
from collections.abc import Callable, Sequence
from enum import Enum, auto
import random

from typing import TypedDict, TYPE_CHECKING
from effects import ForceTarget, Shield, ShockShield, Effect, DamageDebuff, Knock

if TYPE_CHECKING:
    from battle import Ally, View


def no_effects(self, target) -> Sequence[Effect]:
    return []


class Target(Enum):
    # the target is a single unit passed in as a parameter by default
    single = auto()

    # target all allies or enemies with the same effects and damage
    all = auto()

    # info applies to everyone except target
    # effects and damage to target provided in flags
    others = auto()


TABLE = {
    "red": {
        "knight": {
            "attack": {
                "name": "Attack",
                "damage": red % 115,
                "targets": Target.single,
                "effects": lambda self, target: [ForceTarget("Attack", 3, self)],
                "flags": {},
            },
            "passive": {
                "name": "Protect",
                "damage": 0,
                "targets": Target.single,
                "effects": lambda self, target: [Shield("Protect", 2, 55)],
                "flags": {},
            },
        },
        "guardian": {
            "attack": {
                "name": "Overpower",
                "damage": red % 115,
                "targets": Target.single,
                "effects": lambda self, target: [DamageDebuff("Overpower", 2, -25)],
                "flags": {},
            },
            "passive": {
                "name": "Aura Of Fortitude",
                "damage": 0,
                "targets": Target.all,
                "effects": lambda self, target: [Shield("Aura Of Fortitude", 4, 25)],
                "flags": {},
            },
        },
        "samurai": {
            "attack": {
                "name": "Dragon Strike",
                "damage": red % 150,
                "targets": Target.single,
                "effects": no_effects,
                "flags": {"slice": 3},
            },
            "passive": {
                "name": "Defensive Formation",
                "damage": 0,
                "targets": Target.others,
                "effects": lambda self, target: [Shield("Defensive Formation", 1, 40)],
                "flags": {
                    "target": lambda self, target: Shield("Defensive Formation", 1, 50)
                },
            },
        },
        "chili": red_chili,
    },
    "chuck": {
        "mage": {
            "attack": {
                "name": "Storm",
                "damage": chuck % 55,
                "targets": Target.all,
                "effects": no_effects,
                "flags": {},
            },
            "passive": {
                "name": "Shock Shield",
                "damage": 0,
                "targets": Target.single,
                "effects": lambda self, target: [
                    ShockShield("Shock Shield", 3, (chuck % 75).damage)
                ],
                "flags": {},
            },
        },
        "chili": chuck_chili,
    },
    "matilda": {
        "cleric": {
            "attack": {
                "name": "Healing Strike",
                "damage": matilda % 110,
                "targets": Target.single,
                "effects": no_effects,
                "flags": {},
            },
            "passive": {},
        }
    },
}
