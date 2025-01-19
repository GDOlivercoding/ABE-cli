from __future__ import annotations

import json
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Self, overload

# import type: output only ->
from effects import (
    Ambush,
    AncestralProtection,
    Counter,
    DamageBuff,
    DamageDebuff,
    Devotion,
    Effect,
    Energize,
    ForceTarget,
    FreezeBarrier,
    GangUp,
    GiantGrownth,
    Healing,
    HealingShield,
    Knock,
    LifeDrain,
    LifeSteal,
    LinkedHeal,
    Mirror,
    Shield,
    ShockShield,
    ThornyPoison,
    ThunderStorm,
    ToxicPoison,
    Weaken,
)
from flags import FLAG
from value_index import VALUE_INDEX

if TYPE_CHECKING:
    from battle import Ally, Enemy, View


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

    def __mod__(self, other) -> Self:
        return type(self)(self.damage, other)


def get_chance(chance: int) -> bool:
    if chance > 100 or chance < 0:
        raise ValueError(
            f"Invalid chance parameter: {chance},"
            " expected an integer in range 0-100 (inclusive)"
        )
    return random.choices([True, False], weights=[chance, 100 - chance])[0]


data_dir = (Path(__file__).parent / "data").resolve()

AD: dict = json.load(data_dir.joinpath("AD.json").open("r"))
HP: dict = json.load(data_dir.joinpath("HP.json").open("r"))
general: dict = json.load(data_dir.joinpath("general.json").open("r"))

xp = general.get("xp", 0)
scale = general.get("level_scale")

if scale is None:
    raise KeyError("level_scale")

level = 0

while True:
    if xp > scale:
        level += 1
        xp -= scale
        scale += int(scale / 2)
        continue
    break

for name, val in HP.items():
    perc = val / 100 * 2
    val += perc * level
    HP[name] = val

for name, val in AD.items():
    perc = val / 100 * 2
    val += perc * level
    AD[name] = val

AD_DICT = {name: PercDmgObject(val) for name, val in AD.items()}

# there should be a better way to do this
red = AD_DICT["red"]
chuck = AD_DICT["chuck"]
matilda = AD_DICT["matilda"]
bomb = AD_DICT["bomb"]
blues = AD_DICT["blues"]

# TODO: make the getattr get the stats fully
# so they can be modified after (to finally be able to send 50% damage)


class AbilityHandlerObject:
    name: str

    def sbm[T: Effect](self, effect: type[T], **kwargs) -> T:
        return effect(name=self.name, **kwargs)


class Ability:
    def __init__(self, ability: Callable) -> None:
        self.ability = ability
        self.name = self.ability.__name__.replace("_", " ").strip()
        self.flags: Sequence[FLAG] = ()

        # container is received upon BirdCollection initiation so be careful!
        self.container: BirdCollection
        # typ is defined by subclasses
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

    def get(self) -> Any:
        birdname = self.container.birdname
        classname = self.container.current_class

        copy = AbilityHandlerObject()

        if self.typ == "chili":
            obj: dict = VALUE_INDEX[birdname][self.typ]
        else:
            obj: dict = VALUE_INDEX[birdname][classname][self.typ]

        for name, val in obj.items():
            setattr(copy, name, val)

        copy.name = self.name

        return copy

    def send(self, new: AbilityHandlerObject, *args) -> None:
        self.ability(new, *args)

    # the following arguments are for type safety, since all of these are always going to be their type
    @overload
    def __getattr__(self, name: Literal["damage"]) -> int: ...

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
            return VALUE_INDEX[birdname][self.typ][name]

        return VALUE_INDEX[birdname][classname][self.typ][name]


class Attack(Ability):
    typ = "attack"
    # if this attack is an "all" attack
    # an attack, which makes all enemies suffer equally
    # usually an attack, which doesn't use its target argument
    supports_ambiguos_use: bool = False

    def __call__(
        self, birdself: Ally, target: Enemy, flags: Sequence[FLAG] = ()
    ) -> Any:
        return super().__call__(birdself, target, flags=flags)

    def send(self, new: AbilityHandlerObject, birdself: View, target: View) -> None:
        return super().send(new, birdself, target)


class Support(Ability):
    typ = "support"

    def __call__(self, birdself: Ally, target: Ally, flags: Sequence[FLAG] = ()) -> Any:
        return super().__call__(birdself, target, flags=flags)

    def send(self, new: AbilityHandlerObject, birdself: Ally, target: Ally) -> None:
        return super().send(new, birdself, target)


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
        if not classes:
            raise ValueError("Expected at least one BirdClass object")

        for cls in classes:
            cls.attack.container = cls.support.container = self

        self.TOTAL_HP = self.hp = int(HP[birdname])

        self.classes = {cls.classname: cls for cls in classes}
        self.chili = Chili(chili)
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
    damage = red % atk.damage

    damage = PercDmgObject(int(damage)) % (
        100 + (abs(int(self.hp / (self.TOTAL_HP / 100)) - 100) * 2)
    )

    target.deal_damage(damage, self)


# cant make name here
def avenger_support(sprt: Support, self: Ally, target: Enemy):
    target.add_pos_effects(sprt.sbm(Shield, turns=2, effectiveness=20))

    for enemy in self.battle.enemy_units.values():
        enemy.add_neg_effects(sprt.sbm(ForceTarget, turns=2, target=target))


def Holy_Strike(atk: Attack, self: Ally, target: Enemy):
    damage = red % atk.damage
    heal = atk.heal

    _, _, damage, *_ = target.deal_damage(damage, self)

    actual_heal = PercDmgObject(damage) % heal

    if all(unit.hp == unit.TOTAL_HP for unit in self.battle.allied_units.values()):
        self.heal(actual_heal)
    else:
        # fixed: the heal should be based percentage wise
        heal_target = min(
            self.battle.allied_units.values(),
            key=lambda unit: unit.hp / (unit.TOTAL_HP / 100),
        )
        heal_target.heal(actual_heal)


def _Devotion(sprt: Support, self: Ally, target: Ally):
    target.add_pos_effects(
        sprt.sbm(Devotion, turns=3, protector=self, effectiveness=40)
    )


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
        enemy.deal_damage(
            damage,
            self,
            effects=(atk.sbm(ToxicPoison, turns=3, damage=poison),),
            direct=True,
        )


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
        raise SystemError(
            "In Chuck Wizard Chain_Lightning: based on if checks,"
            " expected at least 3 enemies on the battlefield"
            f"actual amount of enemies={len(self.battle.enemy_units)}"
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
            stun_duration=3,
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
    target.add_pos_effects(
        sprt.sbm(Mirror, attack_damage_perc=sprt.super_atk_damage, turns=3)
    )


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


def Thorny_Vine(atk: Attack, self: Ally, target: Enemy):
    damage = matilda % atk.damage
    poison = matilda % atk.poison

    target.deal_damage(
        damage, self, effects=(atk.sbm(ThornyPoison, damage=poison, turns=3),)
    )


def Regrownth(sprt: Support, self: Ally, target: Ally):
    main = PercDmgObject(self.TOTAL_HP) % sprt.heal
    others = PercDmgObject(self.TOTAL_HP) % sprt.others

    target.heal(main)

    for ally in self.battle.allied_units.values():
        if not ally.is_same(target):
            ally.heal(others)


def Royal_Order(atk: Attack, self: Ally, target: Enemy):
    damage = matilda % atk.damage

    target.deal_damage(damage, self)

    for enemy in self.battle.enemy_units.values():
        enemy.add_neg_effects(
            atk.sbm(
                ForceTarget,
                target=max(self.battle.allied_units.values(), key=lambda ally: ally.hp),
                turns=3,
            )
        )


def Royal_Aid(sprt: Support, self: Ally, target: Ally):
    heal = PercDmgObject(self.TOTAL_HP) % sprt.heal

    target.cleanse()
    target.heal(heal)


def Angelic_Touch(atk: Attack, self: Ally, target: Enemy):
    damage = matilda % atk.damage
    slice = atk.slice
    heal = atk.heal

    def drain(ally, enemy, damage):
        return int((ally.TOTAL_HP / 100) * heal)

    for _ in range(slice):
        target.deal_damage(
            damage, self, effects=(atk.sbm(LifeDrain, turns=3, drain=drain),)
        )


def Spirit_Link(sprt: Support, self: Ally, target: Ally):
    effect = sprt.sbm(LinkedHeal, turns=3)

    if self.is_same(target):
        return  # pro self use fr

    self.add_pos_effects(effect)
    target.add_pos_effects(effect)


def Heavy_Metal(atk: Attack, self: Ally, target: Enemy):
    damage = matilda % atk.damage
    stun_chance = atk.stun_chance

    effects = []
    if get_chance(stun_chance):
        effects.append(atk.sbm(Knock, turns=1))

    target.deal_damage(damage, self, effects)


def Soothing_Song(sprt: Support, self: Ally, target: Ally):
    main_heal = PercDmgObject(self.TOTAL_HP) % sprt.main_heal
    side_heal = PercDmgObject(self.TOTAL_HP) % sprt.side_heal

    for ally in self.battle.allied_units.values():
        if ally.is_same(target):
            ally.add_pos_effects(sprt.sbm(Healing, healing=main_heal, turns=3))
            continue

        ally.add_pos_effects(sprt.sbm(Healing, healing=side_heal, turns=3))


def Sinister_Smite(atk: Attack, self: Ally, target: Enemy):
    damage = matilda % atk.damage

    effects = [
        atk.sbm(
            LifeSteal,
            steal_target=self,
            damage=lambda ally, enemy: damage % 15,
            heal=lambda ally, enemy, damage: damage,
        )
    ]

    target.deal_damage(damage, self, effects)


def Giant_Growth(sprt: Support, self: Ally, target: Ally):
    attack_boost = sprt.attack
    health_boost = sprt.health

    target.add_pos_effects(
        sprt.sbm(GiantGrownth, effectiveness=attack_boost, health_boost=health_boost)
    )


# quick bomb


def Pummel(atk: Attack, self: Ally, target: Enemy):
    target.deal_damage(bomb % atk.damage, self)


def pirate_support(sprt: Support, self: Ally, target: Ally):
    buff = sprt.buff
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(sprt.sbm(DamageBuff, effectiveness=buff))


def Cover_Fire(atk: Attack, self: Ally, target: Enemy):
    damage = bomb % atk.damage
    slice = atk.slice
    debuff = atk.debuff

    for i in range(slice):
        target.deal_damage(
            damage, self, effects=(atk.sbm(DamageDebuff, effectiveness=debuff, turns=2),)
        )

def _Counter(sprt: Support, self: Ally, target: Ally):
    target.add_pos_effects(sprt.sbm(Counter, turns=3, effectiveness=sprt.eff))

def Enrage(atk: Attack, self: Ally, target: Enemy):
    damage = bomb % atk.damage

    bonus = self.battle.chili * 0.5

    damage = PercDmgObject(int(damage)) % int(100 + bonus)

    target.deal_damage(damage, self)


def Frenzy(sprt: Support, self: Ally, target: Ally):
    damage = PercDmgObject(target.TOTAL_HP) % 15

    # XXX might break things, but its really this direct
    target.hp -= int(damage)

    for enemy in self.battle.enemy_units.values():
        enemy.deal_damage(damage, self, direct=True)

def Raid(atk: Attack, self: Ally, target: Enemy):
    target.dispell()
    target.deal_damage(bomb % atk.damage, self)

def Whip_Up(sprt: Support, self: Ally, target: Ally):
    deplete = PercDmgObject(target.TOTAL_HP) % 10

    target.hp -= int(deplete)
    target.add_pos_effects(sprt.sbm(DamageBuff, turns=3, effectiveness=sprt.buff))

def Hulk_Smash(atk: Attack, self: Ally, target: Enemy):
    damage = int(bomb % atk.damage)

    damage = damage * ((100 - (self.hp / self.TOTAL_HP)))

    target.deal_damage(damage, self)

def Gang_Up(sprt: Support, self: Ally, target: Ally):
    target.add_pos_effects(sprt.sbm(GangUp, turns=2, bonus_attacker=self))

def Frost_Strike(atk: Attack, self: Ally, target: Enemy):
    damage = bomb % atk.damage
    bonus = atk.bonus

    target = target.get_target(self) # type: ignore

    if any(effect.is_knocked for effect in target.effects.values()):
        damage = damage % bonus

    target.deal_damage(damage, self, direct=True)

def Freezing_Barrier(sprt: Support, self: Ally, target: Ally):
    for ally in self.battle.allied_units.values():
        ally.add_pos_effects(sprt.sbm(
            FreezeBarrier, 
            turns=3, 
            freeze_chance=sprt.chance,
            freeze_turns=sprt.turns
        ))

# quick jay jake and jim (?)


def Volley(atk: Attack, self: Ally, target: Enemy):
    damage = blues % atk.damage
    slice = atk.slice
    weaken = atk.weaken

    for _ in range(slice):
        target.deal_damage(
            damage, self, effects=(atk.sbm(Weaken, turns=3, effectiveness=weaken),)
        )


def _Ambush(sprt: Support, self: Ally, target: Ally):
    target.add_pos_effects(
        sprt.sbm(Ambush, ambusher=self, turns=2, damage=lambda damage: int(damage / 2))
    )


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

    ally_dict = {ally.id: ally for ally in battle.allied_units.values()}
    id_list = [*ally_dict]

    c = 0
    for i in range(chili.supers):
        try:
            get = id_list[c]
        except IndexError:
            c = 0
            get = id_list[c]

        unit = ally_dict[get]

        try:
            battle.allied_units[unit.clsname]
        except KeyError:
            return  # once an ally dies, the chili gets cancelled

        unit._attack(
            unit, random.choice([*battle.enemy_units.values()]), flags=(FLAG.super_atk,)
        )
        c += 1


def matilda_chili(chili: Chili, self: Ally):
    battle = self.battle
    heal = chili.heal

    # the reason behind is that
    # we dont want any healing changing effects (negative)
    # to impact this since they dont

    for unit in battle.allied_units.values():
        unit.cleanse()

    for unit in battle.allied_units.values():
        actual = PercDmgObject(unit.TOTAL_HP) % heal

        unit.heal(actual)


def Explode(chili: Chili, self: Ally):
    damage = bomb % chili.damage

    for unit in self.battle.enemy_units.values():
        unit.deal_damage(damage, self)


def Egg_Surprise(chili: Chili, self: Ally):
    battle = self.battle
    damage = blues % chili.damage

    random.choice([*battle.enemy_units.values()]).dispell()
    random.choice([*battle.enemy_units.values()]).deal_damage(damage, self, direct=True)
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
    BirdClass(attack=Revenge, support=avenger_support, classname="avenger"),
    BirdClass(attack=Holy_Strike, support=_Devotion, classname="paladin"),
    BirdClass(
        attack=Feral_Assault, support=Ancestral_Protection, classname="stone-guard"
    ),
    chili=Heroic_Strike,
    birdname="red",
)

Red.classes["avenger"].support.name = "i dare you!"

Chuck = BirdCollection(
    BirdClass(attack=Storm, support=Shock_Shield, classname="mage"),
    BirdClass(attack=Energy_Drain, support=Lightning_Fast, classname="lightning-bird"),
    BirdClass(attack=Acid_Rain, support=Healing_Rain, classname="rainbird"),
    BirdClass(attack=Chain_Lightning, support=_Energize, classname="wizard"),
    BirdClass(attack=Thunderclap, support=Rage_Of_Thunder, classname="thunderbird"),
    BirdClass(attack=Dancing_Spark, support=Mirror_Image, classname="illusionist"),
    chili=Speed_Of_Light,
    birdname="chuck",
)

Chuck.classes["mage"].attack.supports_ambiguos_use = True
Chuck.classes["lightning-bird"].attack.supports_ambiguos_use = True
Chuck.classes["rainbird"].attack.supports_ambiguos_use = True

Matilda = BirdCollection(
    BirdClass(attack=Healing_Strike, support=Healing_Shield, classname="cleric"),
    BirdClass(attack=Thorny_Vine, support=Regrownth, classname="druid"),
    BirdClass(attack=Royal_Order, support=Royal_Aid, classname="princess"),
    BirdClass(attack=Heavy_Metal, support=Soothing_Song, classname="bard"),
    BirdClass(attack=Sinister_Smite, support=Giant_Growth, classname="witch"),
    birdname="matilda",
    chili=matilda_chili,
)

Matilda.chili.name = "Matilda's Medicine"

Bomb = BirdCollection(
    BirdClass(attack=Pummel, support=pirate_support, classname="pirate"),
    BirdClass(attack=Cover_Fire, support=_Counter, classname="cannoneer"),
    BirdClass(attack=Enrage, support=Frenzy, classname="berserker"),
    BirdClass(attack=Raid, support=Whip_Up, classname="capt'n"),
    BirdClass(attack=Hulk_Smash, support=Gang_Up, classname="sea-dog"),
    BirdClass(attack=Frost_Strike, support=Freezing_Barrier, classname="frost-savage"),
    chili=Explode,
    birdname="bomb",
)

Bomb.classes["pirate"].support.name = "Arrr!"

Blues = BirdCollection(
    BirdClass(attack=Volley, support=_Ambush, classname="marksmen"),
    chili=Egg_Surprise,
    birdname="blues",
)

CLASSES_DICT = {
    "red": Red,
    "chuck": Chuck,
    "matilda": Matilda,
    "bomb": Bomb,
    "blues": Blues,
}
