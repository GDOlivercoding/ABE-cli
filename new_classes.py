from __future__ import annotations
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Any, Literal, NoReturn, Self, overload, ForwardRef
from effects import (
    AncestralProtection,
    DamageDebuff,
    Devotion,
    Effect,
    Energize,
    ForceTarget,
    HealingShield,
    Knock,
    Mirror,
    Shield,
    ShockShield,
    ThunderStorm,
    ToxicPoison,
    Weaken,
)
from value_index import VALUE_INDEX
from flags import FLAG
from copy import deepcopy


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


def get_chance(chance: int) -> bool:
    if chance > 100 or chance < 0:
        raise ValueError(
            f"Invalid chance parameter: {chance},"
            " excepted and integer in range (inclusive) 0-100 (inclusive)"
        )
    return random.choices([True, False], weights=[chance, 100 - chance])[0]


D: dict = json.load(Path(__file__).parent.joinpath("data", "AD.json").open("r"))
del D["BASE"]

AD_DICT = {name: PercDmgObject(val) for name, val in D.items()}
red = AD_DICT["red"]
chuck = AD_DICT["chuck"]
matilda = AD_DICT["matilda"]
bomb = AD_DICT["bomb"]
blues = AD_DICT["blues"]

# TODO: make the getattr get the stats fully
# so they can be modified after (to finally be able to send 50% damage)


class Ability:
    def __init__(self, ability: Callable) -> None:
        self.ability = ability
        self.name = self.ability.__name__.replace("_", " ").strip()
        self.flags: Sequence[FLAG] = ()

        # container is received upon BirdCollection initiation so be careful!
        self.container: BirdCollection
        # typ is defined by subclasss
        self.typ: str

    # this function is shared by ALL subclasses
    # i really wanna typehint Effect and also capture args, but only kwargs
    # but in the current type system, thats not possible
    def sbm[T: Effect](self, effect: type[T], **kwargs) -> T:
        return effect(name=self.name, **kwargs)

    # subclasses should override this function (and super() call)
    def __call__(self, birdself: "Ally", *args, flags: Sequence[FLAG] = ()) -> Any:
        self.flags = flags
        self.ability(self, birdself, *args)
        birdself.battle.death_check()

    def get(self) -> Self:
        copy = deepcopy(self)

        birdname = self.container.birdname
        classname = self.container.current_class

        if self.typ == "chili":
            obj: dict = VALUE_INDEX[birdname][self.typ]
        else:
            obj: dict = VALUE_INDEX[birdname][classname][self.typ]

        for name, val in obj.items():
            setattr(copy, name, val)

        return copy

    def send(self, new: Self, *args) -> None:
        self.ability(new, *args)

    # the following arguments are for type safety, since all of these are always going to be their type

    @overload
    def __getattr__(self, name: Literal["effects"]) -> Sequence[Effect]: ...

    @overload
    def __getattr__(self, name: Literal["damage"]) -> int: ...

    @overload
    def __getattr__(self, name: Literal["self"]) -> Ally: ...

    # subclasses should attempt to override this overload
    # nvm, unless youre einstein you cant figure this out
    # maybe, i'll eventually have to do this
    # since you have to copy this overload, then the general type
    # and then the actual implementation with the super() call
    # for the type checker to be happy
    @overload
    def __getattr__(self, name: Literal["target"]) -> Ally | Enemy: ...

    # slice might not always appear but well define it anyways
    @overload
    def __getattr__(self, name: Literal["slice"]) -> int: ...

    @overload
    def __getattr__(self, name: Literal["heal"]) -> int: ...

    @overload
    def __getattr__(self, name: str) -> Any: ...

    def __getattr__(self, name: str) -> Any:
        birdname = self.container.birdname
        classname = self.container.current_class

        if self.typ == "chili":
            VALUE_INDEX[birdname][self.typ][name]

        return VALUE_INDEX[birdname][classname][self.typ][name]
    
    def __setattr__(self, name: str, value: Any) -> None:
        return super().__setattr__(name, value) # big brain type checker move lol


class Attack(Ability):
    typ = "attack"

    def __call__(
        self, birdself: Ally, target: Enemy, flags: Sequence[FLAG] = ()
    ) -> Any:
        return super().__call__(birdself, target, flags=flags)


class Support(Ability):
    typ = "support"

    def __call__(self, birdself: Ally, target: Ally, flags: Sequence[FLAG] = ()) -> Any:
        return super().__call__(birdself, target, flags=flags)


class Chili(Ability):
    typ = "chili"

    def __call__(self, birdself: Ally, flags: Sequence[FLAG] = ()) -> Any:
        return super().__call__(birdself, flags=flags)

# not a @dataclass because of attr type safety
class BirdClass:
    def __init__(self, attack: Callable, support: Callable, classname: str):
        self.attack = Attack(attack)
        self.support = Support(support)
        self.classname = classname


class BirdCollection:
    def __init__(self, *classes: BirdClass, chili: Callable, birdname: str) -> None:
        if not len(classes):
            raise ValueError("Expected at least one BirdClass object")

        for cls in classes:
            cls.attack.container = cls.support.container = self

        self.classes = {cls.classname: cls for cls in classes}
        self.chili = Chili(chili)
        self.birdname = birdname

        self.chili.container = self

    def get_class(self, classname: str) -> BirdClass:
        try:
            cls = self.classes[classname]
        except KeyError:            raise ValueError(f"classname '{classname}' doesn't exist")

        self.current_class = cls.classname
        return cls


""" 
the following function names violate the convention
as their __name__ is used by `Attack`
if a name collides with another, use as many prefixed underscores as you need
they'll be replaced and ignored

########################

attack abilities should take
(atk: Attack, self: Ally, target: Enemy)

atk: the Attack object wrapping it, note, is passed positionally so name doesnt matter

self: the bird attacking

target: the enemy its attacking

######################

support abilities should take
(sprt: Attack, self: Ally, target: Enemy)

sprt: the Support object wrapping it, note, is passed positionally so name doesnt matter

self: the bird using its support ability

target: the target of the support ability

##########################

chili abilities should take
(chili: Chili, self: Ally)

chili: the Chili object wrapping it, note, is passed positionally so name doesnt matter
self: the bird activating their chili ability
"""


def _Attack(atk: Attack, self: Ally, target: Enemy):
    damage = red % atk.damage

    effects = [atk.sbm(ForceTarget, target=self, turns=3)]

    target.deal_damage(damage, self, effects)

    print(f"{self.name} deals {int(damage)} hp to {target.name}!")


def Protect(sprt: Support, self: Ally, target: Enemy):
    """target ally gets a 55% damage shield for 2 turns"""

    shield = sprt.sbm(Shield, effectiveness=55, turns=2)

    target.add_pos_effects(shield)
    print(f"{target.name} gets a 55% shield for 2 turns!")


def Overpower(atk: Attack, self: Ally, target: Enemy):
    damage = red % atk.damage

    target.deal_damage(damage, self, [atk.sbm(DamageDebuff, turns=2, effectiveness=25)])


def Aura_Of_Fortitude(sprt: Support, self: Ally, target: Enemy):
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(sprt.sbm(Shield, turns=4, effectiveness=25))


def Dragon_Strike(atk: Attack, self: Ally, target: Enemy):
    slice = red % atk.damage

    for i in range(3):
        target.deal_damage(slice, self)


def Defensive_Formation(sprt: Support, self: Ally, target: Enemy):
    for ally in self.battle.allied_units.values():
        if ally.is_same(target):
            ally.add_pos_effects(sprt.sbm(Shield, turns=1, effectiveness=50))
            continue
        ally.add_pos_effects(sprt.sbm(Shield, turns=1, effectiveness=40))


def Revenge(atk: Attack, self: Ally, target: Enemy):
    damage = red % VALUE_INDEX["red"]["avenger"]["attack"]["damage"]

    damage = PercDmgObject(damage) % (
        100 + (abs(int(self.hp / (self.TOTAL_HP / 100)) - 100) * 2)
    )

    target.deal_damage(damage, self)


# cant make name here
def avenger_support(sprt: Support, self: Ally, target: Enemy):
    target.add_pos_effects(sprt.sbm(Shield, turns=2, effectiveness=20))

    for enemy in self.battle.enemy_units.values():
        enemy.add_neg_effects(sprt.sbm(ForceTarget, turns=2, target=target))


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


def _Devotion(sprt: Support, self: Ally, target: Enemy):
    target.add_pos_effects(sprt.sbm(Devotion, turns=3, protector=self, shield=40))


def Feral_Assault(atk: Attack, self: Ally, target: Enemy):
    damage = red % atk.damage
    slice = atk.slice

    for _ in range(slice):  # how find out
        # if target has negative effects
        # if .deal_damage might redirect attack?

        # i just released a fix for this, new method time!

        new = target.get_target(self)

        if new.neg_effects:
            damage = PercDmgObject(int(damage)) % 150

        # XXX i actually think i dont have to use the direct parameter?
        new.deal_damage(damage, self, direct=True)


def Ancestral_Protection(sprt: Support, self: Ally, target: Enemy):
    target.add_pos_effects(
        sprt.sbm(
            AncestralProtection, turns=3, damage_decrease=40, damage_decrease_turns=3
        )
    )


#
#
# CHUCK
#
#

def Storm(atk: Attack, self: Ally, target: Enemy):
    damage = chuck % atk.damage

    for enemy in self.battle.enemy_units.values():
        enemy.deal_damage(damage, self, direct=True)


def Shock_Shield(sprt: Support, self: Ally, target: Ally):
    damage = chuck % sprt.damage  

    effects = sprt.sbm(ShockShield, turns=3, damage=damage)

    target.add_pos_effects(effects)


def Energy_Drain(atk: Attack, self: Ally, target: Enemy):
    damage = chuck % atk.damage  
    chance = atk.dispell_chance  

    for enemy in self.battle.enemy_units.values():

        if get_chance(chance):
            enemy.dispell()

        enemy.deal_damage(damage, self, direct=True)


def Lightning_Fast(sprt: Support, self: Ally, target: Ally):
    target._class.attack(
        target,
        random.choice((*self.battle.enemy_units.values(),)),
        flags=[FLAG.super_atk],
    )


def Acid_Rain(atk: Attack, self: Ally, target: Enemy):
    damage = chuck % atk.damage
    poison = chuck % atk.poison

    # XXX mutability issues may occur
    # mutability issues did infact occur i love myself im so silly :3

    for enemy in self.battle.enemy_units.values():
        enemy.deal_damage(damage, self, effects=(atk.sbm(ToxicPoison, turns=3, damage=poison),), direct=True)


def Healing_Rain(sprt: Support, self: Ally, target: Ally):
    heal = PercDmgObject(self.TOTAL_HP) % sprt.heal

    target.cleanse()

    for ally in self.battle.allied_units.values():
        ally.heal(heal)


# this is one of the hardest functions to write
def Chain_Lightning(atk: Attack, self: Ally, target: Enemy):
    damage0 = chuck % atk.damage
    damage1 = chuck % atk.damage1
    damage2 = chuck % atk.damage2
    damage3 = chuck % atk.damage3

    # this is gonna be a little harder
    # what im i gonna do is
    # create an indexed dictionary
    # and deal damage somehow randomly and close to the target

    indexed_dict = {
        i: enemy for i, enemy in enumerate(self.battle.enemy_units.values())
    }
    reverse_dict = {enemy: i for i, enemy in indexed_dict.items()}

    target_index = None

    for enemy in reverse_dict:
        if target.is_same(enemy):
            target_index = reverse_dict[target]

    assert target_index is not None

    # lets do a couple if else checks first to make it easier for us

    if len(indexed_dict) == 1:
        indexed_dict[0].deal_damage(damage0, self, direct=True)
        return

    elif target_index == 0:
        try:
            for i in range(4):
                damage = locals()[f"damage{i}"]

                indexed_dict[i].deal_damage(damage, self, direct=True)
        except (IndexError, KeyError):
            return
        return

    elif target_index == max(indexed_dict):
        try:
            for i in range(target_index, target_index - 4, -1):

                damage = locals()[f"damage{i}"]

                indexed_dict[i].deal_damage(damage, self, direct=True)

        except (IndexError, KeyError):
            return
        return

    # no more guessing

    # here we know that the target isnt alone
    # and that the index isnt the highest or lowest
    # which means that we can attack at least 3 targets

    try:
        target.deal_damage(damage0, self, direct=True)

        target = indexed_dict[target_index + 1]
        target.deal_damage(damage1, self, direct=True)

        target = indexed_dict[target_index - 1]
        target.deal_damage(damage2, self, direct=True)
    except KeyError:
        raise SystemError("In Chuck Wizard Chain_Lightning: based on if checks,"
                          " expected at least 3 enemies on the battlefield"
                          "actual amount of enemies={enemies}".format(enemies=len(self.battle.enemy_units))
                          ) from None

    # dirty little boilerplate checking
    try:
        target = indexed_dict[target_index + 2]
        target.deal_damage(damage3, self, direct=True)
    except KeyError:
        try:
            target = indexed_dict[target_index - 2]
            target.deal_damage(damage3, self, direct=True)
        except KeyError:
            # in this case there are only 3 enemies on the battlefield
            pass

def _Energize(sprt: Support, self: Ally, target: Ally):
    target.add_pos_effects(
        sprt.sbm(
            Energize, 
            turns=3,
            chili_boost=sprt.chili_boost,
            stun_chance=sprt.stun_chance,
            stun_duration=3
        )
    )

def Thunderclap(atk: Attack, self: Ally, target: Enemy):
    damage = chuck % atk.damage

    effect = atk.sbm(Weaken, effectiveness=atk.effectiveness, turns=3)

    for enemy in self.battle.enemy_units.values():
        if target.is_same(enemy):
            enemy.deal_damage(damage, self, effects=(effect,), direct=True)
            continue

        enemy.deal_damage(damage, self, direct=True)

def Rage_Of_Thunder(sprt: Support, self: Ally, target: Ally):
    damage = chuck % sprt.damage
    
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(sprt.sbm(ShockShield, turns=3, damage=damage))

def Dancing_Spark(atk: Attack, self: Ally, target: Enemy):
    damage = chuck % atk.damage

    effect = atk.sbm(ThunderStorm, shared_damage_perc=atk.shared_damage, turns=3)

    target.deal_damage(damage, self, effects=(effect,))

def Mirror_Image(sprt: Support, self: Ally, target: Ally):
    target.add_pos_effects(sprt.sbm(Mirror, attack_damage_perc=sprt.super_atk_damage, turns=3))

# thats it for chuck

# 
# 
# MATILDA 
# 
#

def Healing_Strike(atk: Attack, self: Ally, target: Enemy):
    damage = matilda % atk.damage
    heal = atk.heal

    _, _, damage, _ = target.deal_damage(damage, self)

    actual_heal = PercDmgObject(damage) % heal

    for ally in self.battle.allied_units.values():
        ally.heal(actual_heal)

def Healing_Shield(sprt: Support, self: Ally, target: Ally):
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(sprt.sbm(HealingShield, turns=3, effectiveness=sprt.heal))

#
#
# CHILIES
#
#


def Heroic_Strike(chili: Chili, self: Ally):
    battle = self.battle

    chili_damage = red % chili.damage

    # red's chili always attacks the highest current health target
    target = max(battle.enemy_units.values(), key=lambda x: x.hp)
    target.deal_damage(chili_damage, self)


def Speed_Of_Light(chili: Chili, self: Ally):
    battle = self.battle

    c = 0
    for i in range(chili.supers):
        units = [*battle.allied_units.values()]

        try:
            unit = units[c]
        except ValueError:
            c = 0
            unit = units[c]
        else:
            c += 1

        unit._class.attack(
            unit, random.choice([*battle.enemy_units.values()]), flags=(FLAG.super_atk,)
        )


def Matildas_medicine(chili: Chili, self: Ally):
    battle = self.battle
    heal = chili.heal

    for unit in battle.allied_units.values():
        unit.cleanse()
        actual = PercDmgObject(unit.TOTAL_HP) % heal

        unit.heal(actual)


Matildas_medicine.__name__ = "Matilda's_medicine"

def Explode(chili: Chili, self: Ally):
    damage = bomb % chili.damage

    for unit in self.battle.enemy_units.values():
        unit.deal_damage(damage, self)

def Egg_Surprise(chili: Chili, self: Ally):
    battle = self.battle
    damage = blues % chili.damage

    random.choice([*battle.enemy_units.values()]).deal_damage(damage, self, direct=True)
    random.choice([*battle.enemy_units.values()]).dispell()
    random.choice([*battle.enemy_units.values()]).add_neg_effects(
        chili.sbm(Knock, turns=1)
    )


Red = BirdCollection(
    BirdClass(
        attack=_Attack,
        support=Protect,
        classname="knight",
    ),
    BirdClass(
        attack=Overpower,
        support=Aura_Of_Fortitude,
        classname="guardian",
    ),
    BirdClass(
        attack=Dragon_Strike,
        support=Defensive_Formation,
        classname="samurai",
    ),
    BirdClass(
        attack=Revenge,
        support=avenger_support,
        classname="avenger"
    ),
    BirdClass(
        attack=Holy_Strike,
        support=_Devotion,
        classname="paladin"
    ),
    BirdClass(
        attack=Feral_Assault,
        support=Ancestral_Protection,
        classname="stone-guard"
    ),

    chili=Heroic_Strike,
    birdname="red",
)

Chuck = BirdCollection(
    BirdClass(
        attack=Storm,
        support=Shock_Shield,
        classname="mage"
    ),
    BirdClass(
        attack=Energy_Drain,
        support=Lightning_Fast,
        classname="lightning-bird"
    ),
    BirdClass(
        attack=Acid_Rain,
        support=Healing_Rain,
        classname="rainbird"
    ),
    BirdClass(
        attack=Chain_Lightning,
        support=_Energize,
        classname="wizard"
    ),
    BirdClass(
        attack=Thunderclap,
        support=Rage_Of_Thunder,
        classname="thunderbird"
    ),
    BirdClass(
        attack=Dancing_Spark,
        support=Mirror_Image,
        classname="illusionist"
    ),
    
    chili=Speed_Of_Light,
    birdname="chuck"
)

Matilda = BirdCollection(
    BirdClass(
        attack=Healing_Strike,
        support=Healing_Shield,
        classname="cleric"
    ),
    birdname="matilda",
    chili=Matildas_medicine
)

CLASSES_DICT = {
    "red": Red,
    "chuck": Chuck,
    "matilda": Matilda
}
