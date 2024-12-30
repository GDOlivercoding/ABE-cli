from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, TYPE_CHECKING
from collections.abc import Sequence

if TYPE_CHECKING:
    from battle import View, Battlefield, Ally, Enemy

__all__ = [
    "Shield",
    "ForceTarget",
    "ShockShield",
    "ThornyShield",
    "DamageBuff",
    "DamageDebuff",
    "Mimic",
    "GooeyPoison",
    "ThornyPoison",
    "ToxicPoison",
    "Healing",
    "Knock",
    "Freeze",
    "Devotion",
    "HealingShield",
    "Immunity",
]

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

    event methods:

        on_hit(victim: V, attacker: A, damage: int, effects: Sequence[Effect])

        manually triggered when the unit wearing this effects gets attacked
        this is after `on_attack`, this should usually trigger effects only
        when the unit actually gets hurt, for example, shield, counter..

        on_attack(attacker: A, victim: V, damage: int, effects: Sequence[Effect])

        triggered when this unit attacks, still in development because im dum

    """

    name: str  # ability which caused this effect
    turns: int  # turns before it expires

    def __post_init__(self):
        self.wearer: View  # defined during application
        self.is_pos: bool | None  # defined using subclasses
        self.can_attack: bool = True
        self.can_passive: bool = True
        self.can_chili: bool = True
        self.can_dispell: bool = True
        self.can_cleanse: bool = True
        self.immune: bool = False

    @property
    def is_knocked(self):
        return self.can_attack and self.can_passive and self.can_chili

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

    def on_heal(self, heal: int):
        """
        Triggered when the unit with this effect gets healed,
        `target` is the unit with the effect, `heal` is the amount to heal
        """
        return heal

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


# subclassing because lazy


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
        eff = self.effectiveness
        damage = int((damage / 100) * eff)
        return victim, attacker, damage, effects


@dataclass
class ForceTarget[T: View](UndefEffect):
    """
    Force the wearer of the effect to target an enemy unit,
    can be both positive and negative, usually wore by enemies
    source: red(knight), marine knight
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

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:

        attacker.deal_damage(self.damage, self.wearer)
        return victim, attacker, damage, effects


@dataclass
class ThornyShield[V: View, A: View](PosEffect):
    """Attacker loses fixed health on attack, source: blues(rogues), enemy: cactus knight"""

    percentage: int

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:

        reflect = int((damage / 100) * self.percentage)
        attacker.deal_damage(reflect, self.wearer)
        return victim, attacker, damage, effects


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


class Poison(NegEffect):
    """A Poison base, if you aren't familiar with poison, it is damage overtime"""

    damage: int

    def enemies_end_of_turn(self):
        if not self.wearer.is_ally:
            return

        self.wearer.deal_damage(self.damage, self.wearer)

    def allies_end_of_turn(self):
        if self.wearer.is_ally:
            return

        self.wearer.deal_damage(self.damage, self.wearer)


class ToxicPoison(Poison):
    """source: rainbird, matey"""


class ThornyPoison(Poison):
    """source: druid, valetine's knight? its rose knight -_-"""


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
        self.can_attack = self.can_passive = self.can_chili = False


class Knock(Stun):
    """source: bard, bird catcher"""


class Freeze(Stun):
    """source: frost savage, ice fighter"""


del Stun


@dataclass
class Devotion[T: View, P: View](PosEffect):
    """
    `protector` will take attacks instead of the wearer and the wearer will get a `shield`% shield for turns
    source: paladin, clockwork knight
    """

    protector: P
    shield: int = 0

    # XXX post init, might want to rethink effects combined with another effect
    def __post_init__(self):
        if self.shield:
            self.wearer.add_pos_effects(Shield(self.name, self.turns, self.shield))

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
            int(damage + ((damage / 100) * self.effectiveness)),
            effects,
        )


@dataclass
class ChiliBlock(NegEffect):
    """
    block the chili on a bird for a period of time
    source: ice / freeze pig ?
    """

    def __post_init__(self):
        self.can_chili = False


@dataclass
class Ambush[A: Ally](PosEffect):
    """
    used by marksmen blues class
    when ambusher is about to get attacked, wearer takes the hit instead
    if the wearer ever gets hit, the ambusher attacks with 50% damage
    """

    ambusher: A

    # i know that the return type just means "-> View", b-but its more weadable !!
    def get_target[T: View](self, target: T, attacker: View) -> View | T:

        if target.is_same(self.ambusher):
            return self.wearer

        return target

    def after_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ) -> None:
        if victim.is_same(self.wearer) and isinstance(attacker, Enemy):
            # XXX the ambusher only deals 50% damage
            self.ambusher.attack(attacker)


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
