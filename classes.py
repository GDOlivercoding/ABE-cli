from __future__ import annotations
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
import random

if TYPE_CHECKING:
    from battle import Ally, Enemy

from effects import ForceTarget, Shield, DamageDebuff, ShockShield, Effect
from value_index import TABLE, Target, chuck_chili, red_chili

#
# RED
#

# KNIGHT

def stringify_effects(effects: Sequence[Effect])     -> str:
    """Seq[Effect] -> "Effect1", "Effect2", "Effect3" """
    return ", ".join(f'"{effect.name}"' for effect in effects)

def attack_wrapper(self: Ally, target: Enemy):
    attack = TABLE[self.name][self.clsname]["attack"]
    battle = self.battle

    damage: int = attack["damage"].damage
    targets: Target = attack["targets"]
    effects: Sequence[Effect] = attack["effects"](self, target)
    flags: dict = attack["flags"]

    for effect in self.effects.values():
        self, target, damage, effects = effect.on_attack(self, target, damage, effects)

    match targets:
        case Target.single:

            if "slice" in flags:
                # now we use damage as the sole purpose
                # of telling the user how much damage they dealt in total
                total_damage = 0

                slice = flags["slice"]
                
                for _ in range(slice):

                    sliced = int(damage / slice)

                    for effect in target.effects.values():
                        target, self, sliced, effects = effect.on_hit(
                            target, self, sliced, effects
                        )

                    target.hp -= sliced
                    total_damage += sliced
            else:
                for effect in target.effects.values():
                    target, self, damage, effects = effect.on_hit(
                        target, self, damage, effects
                    )
                target.hp -= damage

            target.add_neg_effects(*effects)

            print(
                f"{self.name} deals {damage}hp to {target.name}"
                f"\n{target.view()} (-{damage})"
            )

            if effects:
                str_effects = stringify_effects(effects)

                print(
                    f"And applies {str_effects} "
                    f"{'effects' if len(effects) > 1 else 'effect'} to {target.name}."
                )

            print()

        case Target.all:
            print()

            if len(battle.enemy_units) == 1:
                print(
                    f"{self.name} deals {damage}hp to {target.name}"
                    f"\n{target.view()} (-{damage})"
                )

                if effects:
                    
                    str_effects = stringify_effects(effects)

                    print(
                        f"And applies {str_effects} {'effects' if len(effects) > 1 else 'effect'} to {target.name}."
                    )

            else:
                for unit in battle.enemy_units.values():
                    for effect in unit.effects.values():
                        target, self, damage, effects = effect.on_hit(
                            target, self, damage, effects
                        )

                    unit.hp -= damage
                    unit.add_neg_effects(*effects)

                    print(f"{unit.name} -{damage}hp")

            print()

        case Target.others:
            
            target_info = flags["target"]
            target_damage = target_info["damage"]
            target_effects = target_info["effects"]

            for effect in target.effects.values():
                target, self, target_damage, target_effects = effect.on_hit(
                    target, self, damage, effects
                )

            target.hp -= target_damage
            target.add_neg_effects(*target_effects)

            
            print(
                f"{self.name} deals {damage}hp to {target.name}"
                f"\n{target.view()} (-{damage})"
                )

            if target_effects:           
                str_effects = stringify_effects(target_effects)

                print(
                    f"And applies {str_effects}"
                    f" {'effects' if len(effects) > 1 else 'effect'} to {target.name}."
                    )

            print()

            DAMAGE = damage

            for unit in battle.enemy_units.values():
                if unit.name == target.name:
                    continue

                damage = DAMAGE

                for effect in unit.effects.values():
                    unit, self, damage, effects = effect.on_hit(
                        unit, self, damage, effects
                    )

                unit.hp -= damage
                unit.add_neg_effects(*effects)

                print(f"{unit.name} -{damage}hp\n")          

def passive_wrapper(self: Ally, target: Ally):
    passive = TABLE[self.name][self.clsname]["passive"]
    battle = self.battle

    # XXX damage?
    damage: int = passive["damage"]

    targets: Target = passive["targets"]
    effects: Sequence[Effect] = passive["effects"](self, target)

    match targets:

        case Target.single:
            target.add_pos_effects(*effects)
            
            if len(effects) == 1:
                effect = effects[0]

                if self == target:
                    print(f"{self.name} gives itself '{effect.name}' for {effect.turns} turns!")
                else:
                    print(f"{self.name} gives {target.name} '{effect.name}' for {effect.turns} turns!")

            else:
                if self == target:
                    print(f"{self.name} gives itself {stringify_effects(effects)} effects!")
                else:
                    print(f"{self.name} gives {stringify_effects(effects)} effects to {target.name}!")

        case Target.all:
            for unit in battle.allied_units.values():
                unit.add_pos_effects(*effects)

            if len(effects) == 1:
                effect = effects[0]
                print(f"{self.name} gives all allies '{effect.name}' for {effect.turns} turns!")
            else:
                print(f"{self.name} gives {stringify_effects(effects)} effects to all allies!")

def knight_attack(self: Ally, target: Enemy):
    """deals 26 damage to target\ntarget is also forced to attack red for 3 turns"""
    battle = self.battle

    damage = 26
    target = battle.enemy_units[target.name]

    effects = [ForceTarget(target=self, name="Attack", turns=3)]

    for effect in target.effects.values():
        target, self, damage, effects = effect.on_hit(target, self, damage, effects)

    target.hp -= damage
    target.add_neg_effects(*effects)

    print(f"{self.name} deals {damage} hp to {target.name}!")


def knight_passive(self: Ally, target: Ally):
    """target ally gets a 55% damage shield for 2 turns"""

    shield = Shield(effectiveness=55, name="Protect", turns=2)

    target.add_pos_effects(shield)
    print(f"{target.name} gets a 55% shield for 2 turns!")


# GUARDIAN


def guardian_attack(self: Ally, target: Enemy):
    battle = self.battle

    damage = 32
    target = battle.enemy_units[target.name]
    effects = [DamageDebuff(effectiveness=25, name="Overpower", turns=2)]

    for effect in target.effects.values():
        target, self, damage, effects = effect.on_hit(target, self, damage, effects)

    target.hp -= damage
    target.add_neg_effects(*effects)

    print(
        f"{self.name} deals {damage} hp to {target.name}!"
        f" {target.name} deals 25% less damage for 2 turns!"
    )


def guardian_passive(self: Ally, target: Ally):
    battle = self.battle

    for unit in battle.allied_units.values():
        unit.add_pos_effects(Shield(25, "Aura Of Fortitude", 4))

    print("All allies takes 25% less damage for 4 turns!")

# SAMURAI

def samurai_attack(self: Ally, target: Enemy):
    damage = 14

    target.hp -= 3 * damage

    print(f"{self.name} deals {damage * 3} damage to {target.name}!")


def samurai_passive(self: Ally, target: Ally):
    battle = self.battle

    target.add_effects(Shield(50, "Defensive Formation", 1))

    for unit in battle.allied_units.values():
        if unit != target:
            unit.add_effects(Shield(40, "Defensive Formation", 1))

    print(f"{target.name} gets a 50% shield and all other allies 40% for 1 turn!")


# AVENGER


def avenger_attack(self: Ally, target: Enemy):
    battle = self.battle

    damage = 22

    lost_health = self.hp / (self.TOTAL_HP / 100)

    damage = int(bonus := (100 - lost_health * 2) + damage)

    target.hp -= damage

    print(f"{self.name} deals {damage}hp to {target.name} (+{bonus}hp)")


def avenger_passive(self: Ally, target: Ally):
    battle = self.battle

    effect = ForceTarget(target, "I dare you!", 2)

    for unit in battle.enemy_units.values():
        for effect in unit.effects.values():
            if isinstance(effect, ForceTarget):
                # its kind of a set
                # there cannot be 2 of the same kind of effect
                # on a unit, (except for seperate type of same, thorn, acid, goo poison)
                del battle.enemy_units[unit.name].effects[effect.name]
                break

        unit.add_effects(effect)

    target.add_effects(Shield(20, "I dare you!", 2))

    print(
        f"{target.name} gets a 20% shield"
        f" and all enemies must attack {target.name} for 2 turns!"
    )


# chili





#
# CHUCK
#


def mage_attack(self: Ally, target: Enemy):
    battle = self.battle
    damage = 12

    for enemy in battle.enemy_units.values():
        enemy.hp -= damage

    print(f"{self.name} deals {damage} damage to all enemies!")


def mage_passive(self: Ally, target: Ally):

    shock_shield = ShockShield(24, "Shock Shield", 3)

    target.add_effects(shock_shield)

    print(f"{target.name} gets a 24 damage {shock_shield.name} for 3 turns!")





#
#
#
#
#


@dataclass
class BirdClass:
    hp: int

    # Ally is the bird itself, we do this,
    # so the function has access to self
    attack: Callable[[Ally, Enemy], None]

    # same as above
    passive: Callable[[Ally, Ally], None]

    # this is for classes like elite some_class
    # for passives of upgrades of classes
    # so far, i do not know how to implement this
    # and not willing on implementing anytime soon
    class_passive: Any = None

    def __post_init__(self):
        self.TOTAL_HP = self.hp


CLASSES_DICT = {
    "red": {
        "knight": BirdClass(200, knight_attack, knight_passive),
        "guardian": BirdClass(200, guardian_attack, guardian_passive),
        "samurai": BirdClass(200, samurai_attack, samurai_passive),
        "chili": red_chili,
        "doc": str,
    },
    "chuck": {"mage": BirdClass(100, mage_attack, mage_passive), "chili": chuck_chili},
    "matilda": {},
    "bomb": {},
    "blues": {},  # jay, jake and jim
}
