from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any, Self
from effects import (
    AncestralProtection,
    DamageDebuff,
    Devotion,
    Effect,
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

class Attack:
    def __init__(self, attack: Callable[[Callable, Ally, Enemy], object]) -> None:
        self.attack = attack
        self.name = self.attack.__name__.replace("_", " ").strip()
    
    # i really wanna typehint Effect and also capture args, but only kwargs
    # but in the current type system, thats not possible
    def submit[T: Effect](self, effect: type[T], **kwargs) -> T:  
        return effect(name=self.name, **kwargs) # type: ignore , Effect class always have name field
        
    def __call__(self, birdself: Ally, target: Enemy) -> Any:
        self.attack(self.submit, birdself, target)

@dataclass
class Support:
    def __init__(self, support: Callable[[Callable, Ally, Ally], object]) -> None:
        self.support = support
        self.name = self.support.__name__.replace("_", " ").strip()
    
    # i really wanna typehint Effect and also capture args, but only kwargs
    # but in the current type system, thats not possible
    def submit[T: Effect](self, effect: type[T], **kwargs) -> T:  
        return effect(name=self.name, **kwargs) # type: ignore , Effect class always have name field
        
    def __call__(self, birdself: Ally, target: Enemy) -> Any:
        self.support(self.submit, birdself, target)

class Chili:
    def __init__(self, chili: Callable[[Callable, Ally], object]) -> None:
        self.chili = chili
        self.name = self.chili.__name__.replace("_", " ").strip()
    
    # i really wanna typehint Effect and also capture args, but only kwargs
    # but in the current type system, thats not possible
    def submit[T: Effect](self, effect: type[T], **kwargs) -> T:  
        return effect(name=self.name, **kwargs) # type: ignore , Effect class always have name field
        
    def __call__(self, birdself: Ally) -> Any:
        self.chili(self.submit, birdself)

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



""" 
the following function names violate the convention
as their __name__ is used by `Attack`
if a name collides with another, use as many prefixed underscores as you need
they'll be replaced and ignored

########################

attack abilities should take
(sbm: Callable, self: Ally, target: Enemy)

sbm: a Callable which is something like this:

def submit[T: Effect](self, effect: type[T], **kwargs) -> T:  
    return effect(name=self.name, **kwargs)

use it to create an effect, where the name parameter
is autofilled, due to the name of the function

ex.: sbm(Shield, turns=3, effectiveness=40) -> Shield

self: the bird attacking

target: the enemy its attacking

######################

passive abilities should take
(sbm: Callable, self: Ally, target: Enemy)

sbm: read above
self: the ally using its support ability
target: the ally that is being targeted by this support ability

chili abilities should take
(sbm: Callable, self: Ally)

sbm: read attack info
self: the bird activating their chili ability
"""




def _Attack(sbm: Callable, self: Ally, target: Enemy):

    damage = red % VALUE_INDEX["red"]["knight"]["attack"]["damage"]
    
    effects = [sbm(ForceTarget, target=self, turns=3)]

    target.deal_damage(damage, self, effects)

    print(f"{self.name} deals {damage} hp to {target.name}!")


def Protect(sbm: Callable, self: Ally, target: Enemy):
    """target ally gets a 55% damage shield for 2 turns"""

    shield = sbm(Shield, effectiveness=55, name="Protect", turns=2)

    target.add_pos_effects(shield)
    print(f"{target.name} gets a 55% shield for 2 turns!")


def Overpower(sbm: Callable, self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["guardian"]["attack"]["damage"]

    target.deal_damage(
        damage, self, [sbm(DamageDebuff, turns=2, effectiveness=25)]
    )


def Aura_Of_Fortitude(sbm: Callable, self: Ally, target: Enemy):
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(
            sbm(Shield, turns=4, effectiveness=25)
        )

def Dragon_Strike(sbm: Callable, self: Ally, target: Enemy):
    slice = red % VALUE_INDEX["red"]["samurai"]["attack"]["damage"]

    for i in range(3):
        target.deal_damage(slice, self)


def Defensive_Formation(sbm: Callable, self: Ally, target: Enemy):
    for ally in self.battle.allied_units.values():
        if ally.is_same(target):
            ally.add_pos_effects(
                sbm(Shield, turns=1, effectiveness=50)
            )
            continue
        ally.add_pos_effects(
            sbm(Shield, turns=1, effectiveness=40)
        )

def Revenge(sbm: Callable, self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["avenger"]["attack"]["damage"]

    damage = PercDmgObject(damage) % (
        100 + (abs(int(self.hp / (self.TOTAL_HP / 100)) - 100) * 2)
    )

    target.deal_damage(damage, self)

# cant make name here
def avenger_support(sbm: Callable, self: Ally, target: Enemy):
    target.add_pos_effects(sbm(Shield, turns=2, effectiveness=20))

    for enemy in self.battle.enemy_units.values():
        enemy.add_neg_effects(sbm(ForceTarget, turns=2, target=target))

avenger_support.__name__ = "I_dare_you!"

def Holy_Strike(sbm: Callable, self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["paladin"]["attack"]["damage"]
    heal = VALUE_INDEX["red"]["paladin"]["attack"]["heal"]

    _, _, damage, *_ = target.deal_damage(damage, self)

    actual_heal = PercDmgObject(damage) % heal

    if all(unit.hp == unit.TOTAL_HP for unit in self.battle.allied_units.values()):
        self.heal(actual_heal)
    else:
        heal_target = min(self.battle.allied_units.values(), key=lambda unit: unit.hp)
        heal_target.heal(actual_heal)


def _Devotion(sbm: Callable, self: Ally, target: Enemy):
    target.add_pos_effects(
        sbm(Devotion, turns=3, protector=self, shield=40)
    )


def Feral_Assault(self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["stone guard"]["attack"]["damage"]
    slice = VALUE_INDEX["red"]["stone guard"]["attack"]["slice"]

    for _ in range(slice):  # how find out
        # if target has negative effects
        # if .deal_damage might redirect attack?
        if target.neg_effects:
            damage = PercDmgObject(int(damage)) % 150
        target.deal_damage(damage, self)

def Ancestral_Protection(sbm: Callable, self: Ally, target: Enemy):
    target.add_pos_effects(
        sbm(AncestralProtection,
            turns=3, 
            damage_decrease=40, 
            damage_decrease_turns=3)
    )


#
#
#
#
#


def Heroic_Strike(sbm: Callable, self: Ally):
    battle = self.battle

    chili_damage = red % VALUE_INDEX["red"]["chili"]["damage"]

    # red's chili always attacks the highest current health target
    target = max(battle.enemy_units.values(), key=lambda x: x.hp)
    target.deal_damage(chili_damage, self)

def Speed_Of_Light(sbm: Callable, self: Ally):
    battle = self.battle

    c = 0
    for i in range(5):
        units = [*battle.allied_units.values()]

        try:
            unit = units[c]
        except ValueError:
            c = 0
            unit = units[c]
        else:
            c += 1

        unit.attack(random.choice([*battle.enemy_units.values()]))

def Matildas_medicine(sbm: Callable, self: Ally):
    battle = self.battle

    for unit in battle.allied_units.values():
        unit.cleanse()
        unit.heal(PercDmgObject(unit.TOTAL_HP) % 35)

Matildas_medicine.__name__ = "Matilda's_medicine"

def Explode(sbm: Callable, self: Ally):
    damage = bomb % 150

    for unit in self.battle.enemy_units.values():
        unit.deal_damage(damage, self)


def Egg_Surprise(sbm: Callable, self: Ally):
    battle = self.battle
    damage = blues % 200

    # XXX blues' chili is not dodgable
    random.choice([*battle.enemy_units.values()]).deal_damage(damage, self)
    random.choice([*battle.enemy_units.values()]).dispell()
    random.choice([*battle.enemy_units.values()]).add_neg_effects(sbm(Knock, turns=1))

Red = BirdCollection(
    BirdClass(
        attack=Attack(_Attack),
        support=Support(Protect),
        classname="Knight",
    ),
    BirdClass(
        attack=Attack(Overpower),
        support=Support(Aura_Of_Fortitude),
        classname="Guardian",
    ),
    BirdClass(
        attack=Attack(Dragon_Strike),
        support=Support(Defensive_Formation),
        classname="Samurai"
    ),
    chili=Chili(
        Heroic_Strike
    ),  # XXX i think heroic strike is paladin attack # turns out its not
    birdname="red",
)