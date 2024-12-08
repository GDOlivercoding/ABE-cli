from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Optional
from collections.abc import Sequence

if TYPE_CHECKING:
    from battle import View, Battlefield

not_field = lambda: field(init=False)

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
    name: str # ability which caused this effect
    turns: int # turns before it expires
    
    def __post_init__(self):
        self.wearer: View # defined during application
        self.is_pos: bool | None # defined using subclasses
        self.can_attack: bool = True
        self.can_passive: bool = True
        self.can_chili: bool = True
        self.can_dispell: bool = True
        self.can_cleanse: bool = True
        self.immune: bool = False

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:
        """Triggered when unit with this effect takes damage"""
        return victim, attacker, damage, effects

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
        """Triggered when this effect gets applies on a unit, triggered after it has been added to the effect dictionary"""

    def on_exit(self):
        """
        Triggered when the effect expires, 
        triggered before it gets removed and after it gets marked for deletion
        """

    def on_heal(self, target, heal: int):
        """
        Triggered when the unit with this effect gets healed,
        `target` is the unit with the effect, `heal` is the amount to heal
        """
        return target, heal

    def on_cleanse(self):
        """
        Triggered when this effect gets cleansed
        on_exit, but the effect shouldn't do things done on_exit
        like a tick bomb effect from the movie fever 2016
        """
        if self.is_pos:
            raise ValueError(f"Cannot cleanse positive effects:"
                             f" '{self.__class__.__name__}' effect is positive")
        
    def on_dispell(self):
        """
        Triggered when this effect gets dispelled
        on_exit, but the effect shouldn't do things done on_exit
        ## This shouldn't do anything ##
        """
        if not self.is_pos:
            raise ValueError(f"Cannot dispell negative effects:"
                             f" '{self.__class__.__name__}' effect is negative")

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
    """Reduce the damage taken by `effectiveness`"""

    effectiveness: int

    def on_hit(
        self, victim: View, attacker: View, damage: int, effects: Sequence[Effect]
    ):
        eff = self.effectiveness
        damage = int((damage / 100) * eff)
        return victim, attacker, damage, effects

@dataclass
class ForceTarget[T: View, A: View](UndefEffect):
    """Force the wearer of the effect to target an enemy unit, can be both positive and negative, usually wore by enemies"""

    target: T

    def on_attack(
        self, attacker: A, victim: View, damage: int, effects: Sequence[Effect]
    ) -> tuple[A, T, int, Sequence[Effect]]:
        return attacker, self.target, damage, effects

@dataclass
class ShockShield[V: View, A: View](PosEffect):
    """Attacker loses fixed health on attack"""
    damage: int

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:

        attacker.hp -= self.damage
        print(
            f"{attacker.name} takes {self.damage} damage while trying to attack {victim.name}!"
        )
        return victim, attacker, damage, effects

@dataclass
class ThornyShield[V: View, A: View](PosEffect):
    """Attacker loses fixed health on attack"""

    percentage: int

    def on_hit(
        self, victim: V, attacker: A, damage: int, effects: Sequence[Effect]
    ) -> tuple[V, A, int, Sequence[Effect]]:

        reflect = int((damage / 100) * self.percentage)
        attacker.hp -= reflect
        print(
            f"{attacker.name} takes {reflect} damage while trying to attack {victim.name}!"
        )
        return victim, attacker, damage, effects

@dataclass
class DamageBuff[A: View, V: View](PosEffect):
    """Increase damage by `percentage`%"""

    effectiveness: int

    def on_attack(
        self, attacker: A, victim: V, damage: int, effects: Sequence[Effect]
    ) -> tuple[A, V, int, Sequence[Effect]]:
        eff = self.effectiveness
        damage = int((damage / 100) * (100 + eff))
        return attacker, victim, damage, effects

@dataclass
class DamageDebuff[A: View, V: View](NegEffect):
    """Decrease damage by `percentage`%"""
    
    effectiveness: int

    def on_attack(
        self, attacker: A, victim: V, damage: int, effects: Sequence[Effect]
    ) -> tuple[A, V, int, Sequence[Effect]]:
        eff = self.effectiveness
        damage = int((damage / 100) * (100 - eff))
        return attacker, victim, damage, effects

@dataclass
class Mimic[T: View](NegEffect):
    """Steal healing from target onto the ally with the lowest (current) health"""
    def on_heal(self, target: T, heal: int) -> tuple[T, Literal[0]]:
        battle = target.battle

        if target.is_ally:
            heal_target = min(battle.enemy_units.values(), key=lambda enemy: enemy.hp)

            heal_target.hp += heal
        else:
            heal_target = min(battle.allied_units.values(), key=lambda ally: ally.hp)

            heal_target.hp += heal

        return target, 0
    
class Poison(NegEffect):
    """A Poison base, if you aren't familiar with poison, it is damage overtime"""
    damage: int

    def enemies_end_of_turn(self):
        if not self.wearer.is_ally:
            return

        self.wearer.hp -= self.damage

    def allies_end_of_turn(self, wearer: View, battle: Battlefield):
        if wearer.is_ally:
            return

        wearer.hp -= self.damage

class ToxicPoison(Poison): pass
class ThornyPoison(Poison): pass
class GooeyPoison(Poison): pass

# we dont do the base
del Poison

@dataclass
class Healing(PosEffect):
    """Like poison, but it heals you, and theres only 1 type"""
    healing: int

    def enemies_end_of_turn(self):
        if not self.wearer.is_ally:
            return

        self.wearer.hp += self.healing

    def allies_end_of_turn(self):
        if self.wearer.is_ally:
            return

        self.wearer.hp += self.healing

@dataclass
class Stun(NegEffect): 
    """Prevent target from using their abilities for some turns"""
    def __post_init__(self):
        self.can_attack = self.can_passive = self.can_chili = False

class Knock(Stun): pass
class Freeze(Stun): pass

del Stun

@dataclass
class Devotion[T: View, P: View](PosEffect):
    """`protector` will take attacks instead of the wearer and the wearer will get a `shield`% shield for turns"""
    protector: P
    shield: int = 0

    def __post_init__(self):
        if self.shield:
            self.wearer.add_pos_effects(Shield(self.name, self.turns, self.shield))

    def on_hit(self, victim: View, attacker: T, damage: int, effects: Sequence[Effect]
               ) -> tuple[P, T, int, Sequence[Effect]]:
        return self.protector, attacker, damage, effects

@dataclass
class Immunity(PosEffect):
    """
    Prevents negative effects from being applied to wearer
    usually present as a passive
    """
    def __post_init__(self):
        self.immune = True