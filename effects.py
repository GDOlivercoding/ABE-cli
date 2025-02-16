from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

# import type: output only

if TYPE_CHECKING:
    from battle import Ally, ConvertibleToInt, View

# a lot of return types for these effects may seems useless
# first, they just mean the specified type without the typevar
# and also they are never gonna be useful
# the reason is, for my squishy little brain, its more readable
# and thats the point of code and types right?


@dataclass
class Effect[V: View, A: View]:
    """
    The base class of effects, subclass, override init and any other methods as events to use for your effect

    parameters:

    `name`: str = the ability that caused this effect, offensive, passive, or chili ability

    `turns`: int = the amount of turns before this effect expires, should not be toyed around with,
    effects automatically expire, and `on_exit` method is called when the effect expires

    attr:

    `wearer`: View = the unit which is currently "wearing" this effect, this is not a parameter
    but passed it before applying, since there is not reason to add this as a parameter, and would
    just hurt the code

    `is_pos`: property[bool] = if this effect is a positive effect, positive effects can be dispelled and
    negative effects can be cleansed, (ex.: shield is positive, weaken is negative)

    """

    name: str  # ability which caused this effect
    turns: int  # turns before it expires

    def __post_init__(self):
        self.wearer: View  # defined during application
        self.is_pos: bool | None  # defined using subclasses
        self.can_attack: bool = True
        self.can_support: bool = True
        self.can_chili: bool = True
        self.can_dispell: bool = True
        self.can_cleanse: bool = True
        self.immune: bool = False

    @property
    def is_knocked(self):
        return not self.can_attack and not self.can_support and not self.can_chili

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:
        """Triggered when unit with this effect takes damage"""
        return victim, attacker, damage, effects

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        """
        Triggered after all on_hit methods were called,
        you CANNOT change the victim, attacker, damage or effects
        this method for effects which do something after getting hit
        for example canoneer's counter effects
        """

    def on_attack(
        self, attacker: A, victim: V, damage: int, effects: Sequence[Effect]
    ) -> tuple[A, V, int, Sequence[Effect]]:
        """Triggered when unit with this effect takes attacks"""
        return attacker, victim, damage, effects

    def allies_end_of_turn(self):
        """Triggered at the end of the allies' turn, same as the the start of the enemies' turn"""

    def enemies_end_of_turn(self):
        """Triggered at the end of the enemies' turn, same as the the start of the allies' turn"""

    def on_enter(self):
        """
        Triggered when this effect gets applies on a unit,
        triggered after it has been added to the effect dictionary
        """

    def on_exit(self):
        """
        Triggered when the effect expires,
        triggered before it gets removed and after it gets marked for deletion
        """

    def on_heal(self, target: View, heal: int) -> int:
        """
        Triggered when a unit gets healed,
        `target` is the unit with the effect, `heal` is the amount to heal
        """
        return heal

    def after_heal(self, target: View, heal: int) -> None:
        """Triggered after the heal count get finalized, cannot return to change healing"""

    def on_cleanse(self):
        """
        Triggered when this effect gets cleansed
        on_exit, but the effect shouldn't do things done on_exit
        like a tick bomb effect from the movie fever 2016
        """
        if self.is_pos:
            raise ValueError(
                f"Cannot cleanse positive effects:"
                f" '{self.__class__.__name__}' effect is positive"
            )

    def on_dispell(self):
        """
        Triggered when this effect gets dispelled
        on_exit, but the effect shouldn't do things done on_exit
        ## This shouldn't do anything ##
        """
        if not self.is_pos:
            raise ValueError(
                f"Cannot dispell negative effects:"
                f" '{self.__class__.__name__}' effect is negative"
            )

    def get_target(self, target: V, attacker: A) -> V | View:
        """For effects that change the victim, such as ForceTarget or Devotion"""
        return target

    def on_chili(self, invoker: Ally) -> None:
        """When the rage chili is used, usually, abilities should perform after"""

    def after_chili(self, invoker: Ally) -> None:
        """For abilities doing things after the rage chili is used, such as bonus attacks and such"""


def get_chance(chance: int) -> bool:
    if chance > 100 or chance < 0:
        raise ValueError(
            f"Invalid chance parameter: {chance},"
            " expected an integer in range 0-100 (inclusive)"
        )

    return random.choices([True, False], weights=[chance, 100 - chance])[0]


# subclassing


class PosEffect(Effect):
    is_pos = True


class NegEffect(Effect):
    is_pos = False


class UndefEffect(Effect):
    is_pos = None


# effects


@dataclass
class Shield(PosEffect):
    """Reduce the damage taken by `effectiveness`, source: red"""

    effectiveness: int

    def on_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ):
        if victim.is_same(self.wearer):
            eff = self.effectiveness
            damage = int((damage / 100) * (100 - eff))
        return victim, attacker, damage, effects


@dataclass
class ForceTarget[T: View](UndefEffect):
    """
    Force the wearer of the effect to target an enemy unit,
    can be both positive and negative, usually wore by enemies
    source: red(knight), marine knight, rogue leader
    """

    target: T

    def get_target(self, target: T, attacker: View) -> T:
        if attacker.is_same(self.wearer):
            return self.target
        return target


@dataclass
class ShockShield[V: View, A: View](PosEffect):
    """Attacker loses fixed health on attack, source: chuck(mage)"""

    damage: int

    def after_hit(self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]):
        if victim.is_same(self.wearer):
            attacker.deal_damage(self.damage, self.wearer, direct=True)


@dataclass
class ThornyShield[V: View, A: View](PosEffect):
    """Attacker loses fixed health on attack, source: blues(rogues), enemy: cactus knight"""

    percentage: int

    def after_hit(self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]):
        if victim.is_same(self.wearer):
            reflect = int((damage / 100) * self.percentage)
            attacker.deal_damage(reflect, self.wearer)


@dataclass
class DamageBuff[A: View, V: View](PosEffect):
    """Increase damage by `percentage`%, source: trickers, pirate (bomb)"""

    effectiveness: int

    def on_attack(
        self, attacker: A, victim: V, damage: int, effects: Sequence[Effect]
    ) -> tuple[A, V, int, Sequence[Effect]]:
        eff = self.effectiveness
        damage = int((damage / 100) * (100 + eff))
        return attacker, victim, damage, effects


@dataclass
class DamageDebuff[A: View, V: View](NegEffect):
    """Decrease damage by `percentage`%, source: guardian (red), zombie knight"""

    effectiveness: int

    def on_attack(
        self, attacker: A, victim: V, damage: int, effects: Sequence[Effect]
    ) -> tuple[A, V, int, Sequence[Effect]]:
        eff = self.effectiveness
        damage = int((damage / 100) * (100 - eff))
        return attacker, victim, damage, effects


@dataclass
class Mimic[T: View](NegEffect):
    """Steal healing from target onto the ally with the lowest (current) health, source: ice shaman"""

    def on_heal(self, target: T, heal: int) -> Literal[0]:
        battle = self.wearer.battle

        if target.is_ally:
            heal_target = min(battle.enemy_units.values(), key=lambda enemy: enemy.hp)
        else:
            heal_target = min(battle.allied_units.values(), key=lambda ally: ally.hp)

        heal_target.heal(heal)

        return 0


@dataclass
class Poison(NegEffect):
    """A Poison base, if you aren't familiar with poison, it is damage overtime"""

    damage: int

    def enemies_end_of_turn(self):
        if self.wearer.is_ally:
            return

        self.wearer.deal_damage(self.damage, self.wearer, direct=True)

    def allies_end_of_turn(self):
        if not self.wearer.is_ally:
            return

        self.wearer.deal_damage(self.damage, self.wearer, direct=True)


@dataclass
class ToxicPoison(Poison):
    """source: rainbird, matey"""


@dataclass
class ThornyPoison(Poison):
    """source: druid, valetine's knight? its rose knight -_-"""


@dataclass
class GooeyPoison(Poison):
    """source: blues(rogues) Lefty"""


# we dont do the base
del Poison


@dataclass
class Healing(PosEffect):
    """
    Like poison, but it heals you, and theres only 1 type
    source: bard, earth pig
    """

    healing: int

    def enemies_end_of_turn(self):
        if not self.wearer.is_ally:
            return

        self.wearer.heal(self.healing)

    def allies_end_of_turn(self):
        if self.wearer.is_ally:
            return

        self.wearer.heal(self.healing)


@dataclass
class Stun(NegEffect):
    """
    Prevent target from using their abilities for some turns
    """

    def __post_init__(self):
        self.can_attack = self.can_support = self.can_chili = False


class Knock(Stun):
    """source: bard, bird catcher"""


class Freeze(Stun):
    """source: frost savage, ice fighter"""


del Stun


@dataclass
class Devotion[T: View, P: View](Shield):
    """
    `protector` will take attacks instead of the wearer and the wearer will get a `shield`% shield for turns
    source: paladin, clockwork knight
    """

    protector: P

    def get_target(self, target: T, attacker: View) -> P | T:
        if target.is_same(self.wearer):
            return self.protector

        return target


@dataclass
class Immunity(PosEffect):
    """
    Prevents negative effects from being applied to wearer
    usually present as a passive
    source: aura mist (chuck set), pirates
    """

    def __post_init__(self):
        self.immune = True
        self.can_dispell = False


@dataclass
class HealingShield(PosEffect):
    """heal after taking damage, source: cleric"""

    effectiveness: int

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ):
        if victim.is_same(self.wearer):
            print("Healing shield attempts to heal")
            for unit in self.wearer.battle.allied_units.values():
                unit.heal(int((damage / 100) * self.effectiveness))


@dataclass
class Weaken[A: View, V: View](NegEffect):
    """Target suffers more damage, source: skulkers, prince porky, pilot pig???"""

    effectiveness: int

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:
        return (
            victim,
            attacker,
            int(damage + ((damage / 100) * (100 - self.effectiveness))),
            effects,
        )


@dataclass
class ChiliBlock(NegEffect):
    """
    block the chili on a bird for a period of time
    source: ice / freeze pig ?
    """

    can_chili: Literal[False] = field(init=False, default=False)


@dataclass
class Ambush(PosEffect):
    """
    used by marksmen blues class
    when ambusher is about to get attacked, wearer takes the hit instead
    if the wearer ever gets hit, the ambusher attacks with 50% damage
    """

    # this effect is for strictly meant for ally use
    # will be able to use it in the future for enemies as well
    # once i develop them more
    ambusher: Ally

    # the damage parameter should be a Callable which takes int and returns int
    # it receives the damage and returns the actual damage to deal
    # usually can just be a lambda

    damage: Callable[[int], int]

    # i know that the return type just means "-> View", b-but its more weadable !!
    def get_target[T: View](self, target: T, attacker: View) -> View | T:
        if target.is_same(self.ambusher):
            return self.wearer

        return target

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if victim.is_same(self.wearer):
            # temporary fix, XXX maybe not temporary anymore?
            atk = self.ambusher._attack.get()

            atk.damage = self.damage(atk.damage)

            self.ambusher._attack.send(atk, victim, attacker)


@dataclass
class AncestralProtection(PosEffect):
    """
    Attackers will deal `damage_decrease`% less damage for `damage_decrease_turns` turns
    while i try to make effects as abstract as possible
    i dont think theres anything other than stone guard's support ability
    which uses this effect

    inflicted damage debuff effect will cary the name of this effect
    """

    damage_decrease: int
    damage_decrease_turns: int

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        attacker.add_neg_effects(
            DamageDebuff(
                name=self.name,
                turns=self.damage_decrease_turns,
                effectiveness=self.damage_decrease,
            )
        )


@dataclass
class Energize(PosEffect):
    chili_boost: int
    stun_chance: int
    stun_duration: int

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        victim.battle.chili += self.chili_boost

        if get_chance(self.stun_chance):
            attacker.add_neg_effects(Knock(name=self.name, turns=self.stun_duration))


@dataclass
class Mirror(PosEffect):
    """Ally attacks again after attacking with lower damage, source: illusionist"""

    atk_damage_perc: int

    # XXX counter could attack before mirror gets activated
    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if attacker.is_same(self.wearer) and isinstance(attacker, Ally):
            get = attacker._class.attack.get()

            get.damage = int((get.damage / 100) * self.atk_damage_perc)

            attacker._attack.send(get, attacker, victim)


@dataclass
class ThunderStorm(NegEffect):
    """when target suffers damage all allies suffer less damage"""

    shared_damage_perc: int

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if victim.is_same(self.wearer):
            shared_damage = int((damage / 100) * self.shared_damage_perc)

            if not victim.is_ally:
                for enemy in victim.battle.enemy_units.values():
                    if enemy.is_same(victim):
                        continue

                    enemy.deal_damage(shared_damage, self.wearer, direct=True)

            else:
                for ally in victim.battle.allied_units.values():
                    if ally.is_same(victim):
                        continue

                    ally.deal_damage(shared_damage, self.wearer, direct=True)


@dataclass
class LifeDrain(NegEffect):
    """
    Attackers heal when dealing damage to suffering victim

    param drain should be a Callable which takes
    the victim (self.wearer)
    the attaclker
    and the amount of damage deal

    and return the amount to heal (of type ConvertibleToInt)
    can be int, DamageObject or another custom object
    """

    drain: Callable[[View, View, int], ConvertibleToInt]

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if not victim.is_same(self.wearer):
            return

        heal = self.drain(victim, attacker, damage)

        attacker.heal(heal)


@dataclass
class LinkedHeal(PosEffect):
    def __post_init__(self):
        self._lock = False

    def on_heal(self, target: View, heal: int):
        if self._lock:
            self._lock = False
            return

        if target.is_ally:
            for ally in target.battle.allied_units.values():
                if (any(isinstance(inst, type(self)) for inst in ally.pos_effects.values()) 
                    and not ally.is_same(self.wearer)):
                    self._lock = True
                    ally.heal(heal)

        else:
            for enemy in target.battle.enemy_units.values():
                if (any(isinstance(inst, type(self)) for inst in enemy.pos_effects.values()) 
                    and not enemy.is_same(self.wearer)):
                    self._lock = True
                    enemy.heal(heal)


@dataclass
class LifeSteal(NegEffect):
    steal_target: View
    damage: Callable[[View, View], ConvertibleToInt]
    heal: Callable[[View, View, int], ConvertibleToInt]

    # damage dealt at the end of the inflictor's turn
    def enemies_end_of_turn(self):
        if not self.wearer.is_ally:
            return

        damage = self.damage(self.steal_target, self.wearer)

        _, _, damage, _ = self.wearer.deal_damage(damage, self.wearer, direct=True)

        heal = self.heal(self.steal_target, self.wearer, damage)

        self.steal_target.heal(heal)

    def allies_end_of_turn(self):
        if self.wearer.is_ally:
            return

        damage = self.damage(self.steal_target, self.wearer)

        _, _, damage, _ = self.wearer.deal_damage(damage, self.wearer, direct=True)

        heal = self.heal(self.steal_target, self.wearer, damage)

        self.steal_target.heal(heal)


@dataclass
class GiantGrownth(DamageBuff):
    health_boost: int

    def on_enter(self):
        print("on enter called")
        wearer = self.wearer
        health_boost = self.health_boost
        TOTAL_HP = wearer.TOTAL_HP

        perc1 = TOTAL_HP // 100
        boost = perc1 * health_boost

        self.boost = boost
        print("health before: total={0}, hp={1}".format(wearer.TOTAL_HP, wearer.hp))
        wearer.TOTAL_HP += boost
        wearer.hp += boost
        print("health after: total={0}, hp={1}".format(wearer.TOTAL_HP, wearer.hp))

    def on_exit(self):
        wearer = self.wearer

        wearer.TOTAL_HP -= self.boost
        wearer.hp = wearer.hp 
        # this ensures that the hp doesnt temporarily break the cap

    on_dispell = on_exit


@dataclass
class Counter(PosEffect):
    effectiveness: int

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if not victim.is_same(self.wearer):
            return

        get = victim._attack.get()  # type: ignore
        get.damage = (get.damage // 100) * self.effectiveness
        victim._attack.send(get)  # type: ignore


@dataclass
class GangUp(PosEffect):
    bonus_attacker: View

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if not attacker.is_same(self.wearer):
            return

        self.bonus_attacker.attack(victim)  # type: ignore


@dataclass
class FreezeBarrier(PosEffect):
    freeze_chance: int
    freeze_turns: int

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if not victim.is_same(self.wearer):
            return

        if get_chance(self.freeze_chance):
            attacker.add_neg_effects(Freeze(name=self.name, turns=self.freeze_turns))
