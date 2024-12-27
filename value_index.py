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


# these ABiLiTy Flags are for an ai for the enemies
# a potential way to help the ai without having to calculate
class ABLTFLAGS(Enum):
    HEALING = auto()
    DAMAGE = auto()
    EFFECTS = auto()
    SUPER = auto()


class Target(Enum):
    # the target is a single unit passed in as a parameter by default
    single = auto()

    # target all allies or enemies with the same effects and damage
    all = auto()

    # info applies to everyone except target
    # effects and damage to target provided in flags
    others = auto()


BIRDS_TABLE: dict[str, list[str]] = {
    "red": ["knight", "guardian", "samurai", "avenger", "paladin", "stone guard"],
    "chuck": [
        "mage",
        "lightning bird",
        "rainbird",
        "wizard",
        "thunderbird",
        "illusionist",
    ],
    "matilda": ["cleric", "druid", "princess", "priestess", "bard", "witch"],
    "bomb": ["pirate", "cannoneer", "berserker", "capt'n", "sea dog", "frost savage"],
    "blues": ["trickers", "rogues", "marksmen", "skulkers", "treasure hunters"],
}

# we gotta figure out how to do effects
# or if we even want to store them here
# i am leaning towards not

# also how to flag effects
# and when for example, skulkers uses its support ability
# how to send a damage reduction flag

VALUE_INDEX = {
    "red": {
        "knight": {
            "attack": {"damage": 115, "flags": []},
            "passive": {"flags": [ABLTFLAGS.EFFECTS]},
        },
        "guardian": {"attack": {"damage": 110, "flags": []}, "passive": {"flags": []}},
        "samurai": {"attack": {"damage": 50, "slice": 3, "flags": []}},
        "avenger": {"attack": {"damage": 90}, "passive": {}},
        "paladin": {"attack": {"damage": 135, "heal": 30}, "passive": {"flags": []}},
        "stone guard": {
            "attack": {
                "damage": 65,
                "slice": 2,
            }
        },
        "chili": {"damage": 500, "arena": 350, "flags": [ABLTFLAGS.DAMAGE]},
    }
}
