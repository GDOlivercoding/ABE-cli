from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any
from effects import DamageDebuff, ForceTarget, Knock, Shield

def TYPE_CHECKING() -> bool:
    return False
if TYPE_CHECKING():
    from battle import Ally, Battlefield, Enemy

@dataclass
class PercDmgObject:
    DAMAGE: int

    def __mod__(self, other: int):
        return DamageObject(self.DAMAGE, other)

@dataclass
class DamageObject:
    base: int
    multiplier: int

    @property
    def damage(self):
        return int((self.base / 100) * self.multiplier)

    def __int__(self):
        return self.damage

D: dict = json.load(Path(__file__).parent.joinpath("data", "AD.json").open("r"))
del D["BASE"]

AD_DICT = {name: PercDmgObject(val) for name, val in D.items()}
red = AD_DICT["red"]
chuck = AD_DICT["chuck"]
matilda = AD_DICT["matilda"]
bomb = AD_DICT["bomb"]
blues = AD_DICT["blues"]

@dataclass
class Attack:
    __call__: Callable[[Ally, Enemy], object]
    name: str
   

@dataclass
class Support: 
    __call__: Callable[[Ally, Ally], object]
    name: str

@dataclass
class Chili:
    __call__: Callable[[Ally], object]
    name: str

@dataclass
class BirdClass:
    attack: Attack
    support: Support
    classname: str

class BirdCollection:
    def __init__(self, *classes: BirdClass, chili: Chili, birdname: str) -> None:
        if not len(classes):
            raise ValueError("Expected at least one BirdClass object")
        
        self.classes = {cls.classname: cls for cls in classes}
        self.chili = chili
        self.birdname = birdname

def red_chili(self: Ally):
    battle = self.battle

    chili_damage = red % 500

    # red's chili always attacks the highest current health target
    target = max(battle.enemy_units.values(), key=lambda x: x.hp)
    target.deal_damage(chili_damage, self)

def knight_attack(self: Ally, target: Enemy):
    battle = self.battle

    damage = red % 0  # TODO
    effects = [ForceTarget(target=self, name="Attack", turns=3)]
    target.deal_damage(damage, self, effects)

    print(f"{self.name} deals {damage} hp to {target.name}!")

def knight_support(self: Ally, target: Ally):
    """target ally gets a 55% damage shield for 2 turns"""

    shield = Shield(effectiveness=55, name="Protect", turns=2)

    target.add_pos_effects(shield)
    print(f"{target.name} gets a 55% shield for 2 turns!")

def guardian_attack(self: Ally, target: Enemy):
    damage = red % 110 # TODO

    target.deal_damage(damage, self, [DamageDebuff(name="Overpower", turns=2, effectiveness=25)])

def guardian_support(self: Ally, target: Ally):
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(Shield(name="Aura Of Fortitude", turns=4, effectiveness=25))

Red = BirdCollection(
    BirdClass(
        attack=Attack(knight_attack, name="Attack"),
        support=Support(knight_support, name="Protect"),
        classname="Knight"
    ),
    BirdClass(
        attack=Attack(guardian_attack, name="Overpower"),
        support=Support(guardian_support, name="Aura Of Fortitude"),
        classname="Guardian"
    ),
    chili=Chili(red_chili, name="Heroic Strike"), # XXX i think heroic strike is paladin attack
    birdname="red"
)

def chuck_chili(self: Ally):
    battle = self.battle
    
    c = 0
    for i in range(0, 4):
        units = [*battle.allied_units.values()]
        
        try:
            unit = units[c]
        except ValueError:
            c = 0
            unit = units[c]
        else:
            c += 1
        
        unit.attack(random.choice([*battle.enemy_units.values()]))


def matilda_chili(self: Ally):
    battle = self.battle

    for unit in battle.allied_units.values():
        unit.cleanse()
        unit.heal(PercDmgObject(unit.TOTAL_HP) % 35)


def bomb_chili(self: Ally):
    damage = bomb % 150

    for unit in self.battle.enemy_units.values():
        unit.deal_damage(damage, self)

def blues_chili(self: Ally):
    battle = self.battle
    damage = blues % 200

    random.choice([*battle.enemy_units.values()]).deal_damage(damage, self)
    random.choice([*battle.enemy_units.values()]).dispell()
    random.choice([*battle.enemy_units.values()]).add_neg_effects(Knock("Explode", 1))