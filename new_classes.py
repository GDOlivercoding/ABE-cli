from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any
from effects import (
    AncestralProtection,
    DamageDebuff,
    Devotion,
    ForceTarget,
    Knock,
    Shield,
)
from value_index import VALUE_INDEX


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

    chili_damage = red % VALUE_INDEX["red"]["chili"]["damage"]

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
    damage = red % 110  # TODO

    target.deal_damage(
        damage, self, [DamageDebuff(name="Overpower", turns=2, effectiveness=25)]
    )


def guardian_support(self: Ally, target: Ally):
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(
            Shield(name="Aura Of Fortitude", turns=4, effectiveness=25)
        )


def samurai_attack(self: Ally, target: Enemy):
    slice = red % VALUE_INDEX["red"]["samurai"]["attack"]["damage"]

    for i in range(3):
        target.deal_damage(slice, self)


def samurai_support(self: Ally, target: Ally):
    for ally in self.battle.allied_units.values():
        if ally.is_same(target):
            ally.add_pos_effects(
                Shield(name="Defensive Formation", turns=1, effectiveness=50)
            )
            continue
        ally.add_pos_effects(
            Shield(name="Defensive Formation", turns=1, effectiveness=40)
        )


def avenger_attack(self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["avenger"]["attack"]["damage"]

    damage = PercDmgObject(damage) % (
        100 + (abs(int(self.hp / (self.TOTAL_HP / 100)) - 100) * 2)
    )

    target.deal_damage(damage, self)


def avenger_support(self: Ally, target: Ally):
    target.add_pos_effects(Shield("I dare you!", turns=2, effectiveness=20))

    for enemy in self.battle.enemy_units.values():
        enemy.add_neg_effects(ForceTarget("I dare you!", turns=2, target=target))


def paladin_attack(self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["paladin"]["attack"]["damage"]
    heal = VALUE_INDEX["red"]["paladin"]["attack"]["heal"]

    _, _, damage, *_ = target.deal_damage(damage, self)

    actual_heal = PercDmgObject(damage) % heal

    if all(unit.hp == unit.TOTAL_HP for unit in self.battle.allied_units.values()):
        self.heal(actual_heal)
    else:
        heal_target = min(self.battle.allied_units.values(), key=lambda unit: unit.hp)
        heal_target.heal(actual_heal)


def paladin_support(self: Ally, target: Ally):
    target.add_pos_effects(
        Devotion(name="Devotion", turns=3, protector=self, shield=40)
    )


def stoneguard_attack(self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["stone guard"]["attack"]["damage"]
    slice = VALUE_INDEX["red"]["stone guard"]["attack"]["slice"]

    for _ in range(slice):  # how find out
        # if target has negative effects
        # if .deal_damage might redirect attack?
        if target.neg_effects:
            damage = PercDmgObject(int(damage)) % 150
        target.deal_damage(damage, self)


def stoneguard_support(self: Ally, target: Enemy):
    target.add_pos_effects(
        AncestralProtection(
            name="Ancestral Protection", 
            turns=3, 
            damage_decrease=40, 
            damage_decrease_turns=3)
    )


#
#
#
#
#

Red = BirdCollection(
    BirdClass(
        attack=Attack(knight_attack, name="Attack"),
        support=Support(knight_support, name="Protect"),
        classname="Knight",
    ),
    BirdClass(
        attack=Attack(guardian_attack, name="Overpower"),
        support=Support(guardian_support, name="Aura Of Fortitude"),
        classname="Guardian",
    ),
    chili=Chili(
        red_chili, name="Heroic Strike"
    ),  # XXX i think heroic strike is paladin attack # turns out its not
    birdname="red",
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
