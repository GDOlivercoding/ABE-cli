from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from battle import Battlefield
    from effects import Effect

class ConvertibleToInt(Protocol):
    def __int__(self) -> int: ...

class View(ABC):
    @abstractmethod
    def __init__(self) -> None:
        self.name: str  # assigned during init
        self.battle: Battlefield  # assigned once added to the Battlefield object
        self.is_ally: bool  # assigned with subclass
        self.neg_effects: dict[str, Effect]  # assigned during init
        self.pos_effects: dict[str, Effect]  # assigned during init
        self.id: int  # assigned once added to the Battlefield object
        self._hp: int
        self.TOTAL_HP: int
        ...

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, setter: ConvertibleToInt):
        self._hp = int(setter)
        if self._hp > self.TOTAL_HP:
            self._hp = self.TOTAL_HP

    def view(self) -> str:  # probably deprecated
        """Obsolete method, formatting is gonna made a different way a i think"""
        return f"{self.name} - {self.hp}/{self.TOTAL_HP}"  # type: ignore

    def is_same(self, target: View) -> bool:
        return self.id == target.id

    @property
    def effects(self):
        return self.pos_effects | self.neg_effects

    def cleanse(self):
        for effect in list(self.neg_effects.values()):
            if not effect.can_cleanse:
                continue
            effect.on_cleanse()
            del self.neg_effects[effect.name]

    def dispell(self):
        for effect in list(self.pos_effects.values()):
            if not effect.can_dispell:
                continue
            effect.on_dispell()
            del self.pos_effects[effect.name]

    def deal_damage[T: View](
        self,
        damage: ConvertibleToInt,
        source: T,
        effects: Sequence[Effect] = (),
        direct: bool = False,
    ) -> tuple[View | Self, T, int, Sequence[Effect]]:
        """
        method to attack a unit,
        this should only be called within bird class attacks, passives and chilies)

        args:
            damage: the amount of damage to deal to self
            source: the attacker which caused this attack
            effects: effects to be applied to self
            direct: if True, dont apply redirecting effects, only use when you used self.get_target() yourself
            or when this attack is not dodgable, like for example, all targeted attacks (chucks attacks)

        NOTE:
            poison damage will be blockable
            gotta work on that
            poison will probably reduce the .hp
            attribute without any events

        returns tuple[
            Self or View if target gets changed

            T[View] the source of the damage, usually the unit attacking (attacker)

            int the totalized finalized damage that the unit took

            Seq[Effect] a list of effects applied to the unit
        ]
        """

        damage = int(damage)
        #print(
        #    f"{source.name} tries to attack {self.name}!"
        #    f"\ndamage={damage}, effects={', '.join(effect.name for effect in effects)}"
        #)

        target = self if direct else self.get_target(source)

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                target, source, damage, effects = effect.on_hit(
                    target, source, damage, effects
                )

        #print(
        #    f"new: damage={damage}, effects={', '.join(effect.name for effect in effects)}"
        #)

        #print(f"old: {self.battle.chili=}, {target.hp=}")
        self.battle.chili += 5
        target.hp -= damage
        #print(f"new: {self.battle.chili=}, {target.hp=}")

        effects = list(target.add_neg_effects(*effects))
        #print(f"actual effects: {', '.join(effect.name for effect in effects)}\n")

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                effect.after_hit(target, source, damage, effects)

        return target, source, damage, effects

    def heal(self, heal: ConvertibleToInt):
        heal = int(heal)
        #print(f"An unknown source tries to heal {self.name}, heal={heal}")
        target = self
        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                heal = effect.on_heal(target=target, heal=heal)

        #print(f"Actual heal: {heal}")

        #print(f"old: {target.hp=}")
        target.hp += heal
        #print(f"new: {target.hp=}")

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                effect.after_heal(target=target, heal=heal)

    def get_target(self, attacker: View) -> Self | View:
        """
        Obtain the target, this method by itself does not cause any damage
        either return the object whose method is called
        or an effect which changed the target
        """
        target = self

        for effect in attacker.effects.values():
            target = effect.get_target(target, attacker)

        # XXX EFFECTS CAN HAVE SAME NAME
        for effect in target.effects.values():
            target = effect.get_target(target, attacker)

        return target

    def add_neg_effects(self, *effects: Effect) -> Generator[Effect, None, None]:
        """
        Add negative effects `effects`
        -> Generator[effects successfully applied, None, None]
        """
        if any(effect.immune for effect in self.effects.values()):
            return  # cannot add neg effects to immune target

        for effect in effects:
            if effect.is_pos:
                raise ValueError(
                    f"Cannot add positive effect '{effect.__class__.__name__}'"
                )

            to_delete = []

            for _effect in self.neg_effects.values():
                if type(effect) is type(_effect):
                    to_delete.append(_effect.name)

            for name in to_delete:
                del self.neg_effects[name]

            effect.wearer = self
            effect.is_pos = False  # if its an undefined effect

            yield effect
            self.neg_effects[effect.name] = effect
            effect.on_enter()

    def add_pos_effects(self, *effects: Effect):
        for effect in effects:
            if not effect.is_pos:
                raise ValueError(
                    f"Cannot add negative effect '{effect.__class__.__name__}'"
                )

            to_delete = []

            for _effect in self.pos_effects.values():
                if type(effect) is type(_effect):
                    to_delete.append(_effect.name)

            for name in to_delete:
                del self.pos_effects[name]

            effect.wearer = self
            effect.is_pos = True  # if its an undefined effect

            self.pos_effects[effect.name] = effect
            effect.on_enter()

    def is_dead(self) -> bool:
        return self.hp <= 0