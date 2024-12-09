from __future__ import annotations
from collections.abc import Callable, Sequence
from enum import Enum, auto
import random

from typing import TypedDict, TYPE_CHECKING
from effects import ForceTarget, Shield, ShockShield, Effect, DamageDebuff, Knock
from AD import red, chuck, matilda, bomb, blues, PercDmgObject

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

class Field(TypedDict):
    name: str
    damage: int
    targets: Target
    effects: Callable[[Ally, View], Sequence[Effect]]
    flags: dict

class ClsDict(TypedDict):
    attack: Field
    passive: Field

def red_chili(self: Ally):
    battle = self.battle

    damage = TABLE[self.name][self.clsname]["attack"]["damage"].damage

    chili_damage = PercDmgObject(damage) % 500

    # red's chili always attacks the highest current health target
    target = max(battle.enemy_units.values(), key=lambda x: x.hp)
    target.hp -= int(chili_damage)

    print(f"{self.name}'s chili deals {chili_damage} damage to {target.name}!")

    if target.hp <= 0:
        print(f"{target.name} dies.")
        del battle.enemy_units[target.name]
    else:
        print(target.view())

def chuck_chili(self: Ally):
    battle = self.battle
    allies = list(battle.allied_units.values())

    c = 0
    for _ in range(5):
        try:
            enemies = list(battle.enemy_units.values())
            if not enemies:
                return

            allies[c].attack(random.choice(enemies))
        except IndexError:
            c = 0

        enemies = list(battle.enemy_units.values())
        allies[c].attack(random.choice(enemies))
        c += 1

        if not battle.enemy_units:
            return

def matilda_chili(self: Ally):
    battle = self.battle

    for unit in battle.allied_units.values():
        unit.cleanse() 
        unit.hp += int(PercDmgObject(unit.TOTAL_HP) % 35)

def bomb_chili(self: Ally):

    damage = bomb % 150

    for unit in self.battle.enemy_units.values():
        unit.hp -= int(damage)

def blues_chili(self: Ally):
    battle = self.battle
    damage = blues % 200

    random.choice([*battle.enemy_units.values()]).hp -= int(damage)
    random.choice([*battle.enemy_units.values()]).dispell()
    random.choice([*battle.enemy_units.values()]).add_neg_effects(Knock("Explode", 1))

TABLE = {
    "red": {
        "knight": {
            "attack": {
                "name": "Attack",
                "damage": red % 115, 
                "targets": Target.single,
                "effects": lambda self, target: [ForceTarget("Attack", 3, self)],
                "flags": {}
            },
            "passive": {
                "name": "Protect",
                "damage": 0,
                "targets": Target.single,
                "effects": lambda self, target: [Shield("Protect", 2, 55)],
                "flags": {}
            }
        },
        "guardian": {
            "attack": {
                "name": "Overpower",
                "damage": red % 115,
                "targets": Target.single,
                "effects": lambda self, target: [DamageDebuff("Overpower", 2, -25)],
                "flags": {}
            },
            "passive": {
                "name": "Aura Of Fortitude",
                "damage": 0,
                "targets": Target.all,  
                "effects": lambda self, target: [Shield("Aura Of Fortitude", 4, 25)],
                "flags": {}
            }
        },
        "samurai": {    
            "attack": {
                "name": "Dragon Strike",
                "damage": red % 150,
                "targets": Target.single,
                "effects": no_effects,
                "flags": {"slice": 3}
            },
            "passive": {
                "name": "Defensive Formation",
                "damage": 0,
                "targets": Target.others,
                "effects": lambda self, target: [Shield("Defensive Formation", 1, 40)],
                "flags": {"target": lambda self, target: Shield("Defensive Formation", 1, 50)}
            }
        },
        "chili": red_chili
    },
    "chuck": {
        "mage": {
            "attack": {
                "name": "Storm",
                "damage": chuck % 55,
                "targets": Target.all,
                "effects": no_effects,
                "flags": {}
            },
            "passive": {
                "name": "Shock Shield",
                "damage": 0,
                "targets": Target.single,
                "effects": lambda self, target: [ShockShield("Shock Shield", 3, (chuck % 75).damage)],
                "flags": {}
            }
        },
        "chili": chuck_chili
    },
    "matilda": {
        "cleric": {
            "attack": {
                "name": "Healing Strike",
                "damage": matilda % 110,
                "targets": Target.single,
                "effects": no_effects,
                "flags": {}
            },
            "passive": {}
        }
    }
}