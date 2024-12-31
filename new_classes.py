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
    ForceTarget,
    Knock,
    Shield,
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
        self.flags: list[FLAG] = []

        # container is received upon BirdCollection initiation so be careful!
        self.container: BirdCollection
        # typ is defined by subclasss
        self.typ: str

    # this function is shared by ALL subclasses
    # i really wanna typehint Effect and also capture args, but only kwargs
    # but in the current type system, thats not possible
    def sbm[T: Effect](self, effect: type[T], **kwargs) -> T:
        return effect(name=self.name, **kwargs)  # type: ignore , Effect class always have name field

    # subclasses should override this function (and super() call)
    def __call__(self, *args, flags: list[FLAG]) -> Any:
        self.ability(self, *args)

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


class Attack(Ability):
    typ = "attack"

    def __call__(self, birdself: Ally, target: Enemy) -> Any:
        return super()(birdself, target)

    @overload
    def __getattr__(self, name: Literal["target"]) -> Enemy: ...

    @overload
    def __getattr__(self, name: str) -> Any: ...

    def __getattr__(self, name: str) -> Any:
        return super().__getattr__(name)


class Support(Ability):
    typ = "support"

    def __call__(self, birdself: Ally, target: Ally) -> Any:
        return super()(birdself, target)

    @overload
    def __getattr__(self, name: Literal["target"]) -> Ally: ...

    @overload
    def __getattr__(self, name: str) -> Any: ...

    def __getattr__(self, name: str) -> Any:
        return super().__getattr__(name)


class Chili(Ability):
    typ = "chili"

    def __call__(self, birdself: Ally) -> Any:
        return super()(birdself)

    # target doesnt exist for chilies
    @overload
    def __getattr__(self, name: Literal["target"]) -> NoReturn: ...

    @overload
    def __getattr__(self, name: str) -> Any: ...

    def __getattr__(self, name: str) -> Any:
        return super().__getattr__(name)


@dataclass
class BirdClass:
    attack: Attack
    support: Support
    classname: str


class BirdCollection:
    def __init__(self, *classes: BirdClass, chili: Chili, birdname: str) -> None:
        if not len(classes):
            raise ValueError("Expected at least one BirdClass object")

        for cls in classes:
            cls.attack.container = cls.support.container = self

        self.classes = {cls.classname: cls for cls in classes}
        self.chili = chili
        self.birdname = birdname

        self.chili.container = self

    def get_class(self, classname: str) -> BirdClass:
        try:
            cls = self.classes[classname]
        except KeyError:
            raise ValueError(f"classname '{classname}' doesn't exist")

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

    print(f"{self.name} deals {damage} hp to {target.name}!")


def Protect(sprt: Support, self: Ally, target: Enemy):
    """target ally gets a 55% damage shield for 2 turns"""

    shield = sprt.sbm(Shield, effectiveness=55, name="Protect", turns=2)

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

        target = target.get_target(self)

        if target.neg_effects:
            damage = PercDmgObject(int(damage)) % 150

        # XXX i actually think i dont have to use the direct parameter?
        target.deal_damage(damage, self, direct=True)


def Ancestral_Protection(sprt: Support, self: Ally, target: Enemy):
    target.add_pos_effects(
        sprt.sbm(
            AncestralProtection, turns=3, damage_decrease=40, damage_decrease_turns=3
        )
    )


#
#
#
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
    for i in range(5):
        units = [*battle.allied_units.values()]

        try:
            unit = units[c]
        except ValueError:
            c = 0
            unit = units[c]
        else:
            c += 1

        # XXX we gotta also implement flags, for example, the super attack flag, and the bonus attack flag
        unit.attack(random.choice([*battle.enemy_units.values()]))


def Matildas_medicine(chili: Chili, self: Ally):
    battle = self.battle
    heal = chili.heal

    for unit in battle.allied_units.values():
        unit.cleanse()
        actual = PercDmgObject(unit.TOTAL_HP) % heal

        unit.heal(actual)


Matildas_medicine.__name__ = "Matilda's_medicine"


def Explode(chili: Chili, self: Ally):
    damage = bomb % 150

    for unit in self.battle.enemy_units.values():
        unit.deal_damage(damage, self)


def Egg_Surprise(chili: Chili, self: Ally):
    battle = self.battle
    damage = blues % 200

    random.choice([*battle.enemy_units.values()]).deal_damage(damage, self, direct=True)
    random.choice([*battle.enemy_units.values()]).dispell()
    random.choice([*battle.enemy_units.values()]).add_neg_effects(
        chili.sbm(Knock, turns=1)
    )


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
        classname="Samurai",
    ),
    chili=Chili(Heroic_Strike),
    birdname="red",
)

CLASSES_DICT = {"red": Red}


if __name__ == "__main__":
    Red.get_class("knight")
    Red.chili.name
