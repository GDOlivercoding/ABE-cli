from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Sequence
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Protocol, Self, runtime_checkable

from rich import print
import rich.table

# import type: switch
from help import help
from classes import CLASSES_DICT
from value_index import BIRDS_TABLE


class Table(rich.table.Table):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        print(self)


if TYPE_CHECKING:
    from battle import View
    from effects import Effect
    from main import MainObj


class ConvertibleToInt(Protocol):
    def __int__(self) -> int: ...


# classes


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
        print(
            f"{source.name} tries to attack {self.name}!"
            f"\ndamage={damage}, effects={', '.join(effect.name for effect in effects)}"
        )

        target = self if direct else self.get_target(source)

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                target, source, damage, effects = effect.on_hit(
                    target, source, damage, effects
                )

        print(
            f"new: damage={damage}, effects={', '.join(effect.name for effect in effects)}"
        )

        print(f"old: {self.battle.chili=}, {target.hp=}")
        self.battle.chili += 5
        target.hp -= damage
        print(f"new: {self.battle.chili=}, {target.hp=}")

        effects = list(target.add_neg_effects(*effects))
        print(f"actual effects: {', '.join(effect.name for effect in effects)}\n")

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                effect.after_hit(target, source, damage, effects)

        return target, source, damage, effects

    def heal(self, heal: ConvertibleToInt):
        heal = int(heal)
        print(f"An unknown source tries to heal {self.name}, heal={heal}")
        target = self

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                heal = effect.on_heal(target=target, heal=heal)

        print(f"Actual heal: {heal}")

        print(f"old: {target.hp=}")
        target.hp += heal
        print(f"new: {target.hp=}")

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


# here Ally is going to be a class for ally allies
# and its abilities are specified in attrs

# but enemies are too unique
# so they will be based off subclasses


class Ally(View):
    def __init__(self, name: str, _class: str) -> None:
        self.name = name
        self.clsname = _class

        self.bird = CLASSES_DICT[name]
        self._class = self.bird.get_class(_class)

        self.TOTAL_HP = self._hp = self.bird.TOTAL_HP

        self._attack = self._class.attack
        self._support = self._class.support
        self._chili = self.bird.chili

        self.is_ally: Final = True

        self.neg_effects: dict[str, Effect] = {}
        self.pos_effects: dict[str, Effect] = {}

    # these guys have to be here
    # because the inner method take "2 selfs"

    def attack(self, target: Enemy):
        self._class.attack(self, target)

    def support(self, target: Ally):
        self._class.support(self, target)

    def chili(self):
        self.bird.chili(self)


class Pig:
    can_chili = False
    name = "Pig"

    def __getattr__(self, name: str):
        pass


pig = Pig()


class Enemy(View):
    """
    A baseclass for enemies, or can be used as a class for simple enemies
    it is going to be hard to determinate how simple they should be

    for now ill decide for enemies with a singular attack
    """

    def __init__(self, name: str, hp: int, damage: int, flags={}):
        self.name = name.lower()
        self._hp = hp
        self.TOTAL_HP = hp
        self.damage = damage
        self.is_ally: Final = False
        self.neg_effects: dict[str, Effect] = {}
        self.pos_effects: dict[str, Effect] = {}
        self.passives = {pig.name: pig}  # planned for the future

    def attack(self):
        self.set_target()

        damage = self.damage
        target = self.current_target
        target, self, damage, _ = target.deal_damage(damage, self)

        print(f"{self.name} attacks {target.name} for {damage} damage")

    def set_target(self):
        # always attack the lowest health target
        self.current_target = min(self.battle.allied_units.values(), key=lambda x: x.hp)


class result(Enum):
    lost = auto()
    won = auto()
    game_aborted = auto()
    interface_aborted = auto()
    no_result = auto()


class DummyControlSet:
    def control(self, name: str) -> Iterable[str]:
        return (name,)

@runtime_checkable
class SupportsControl(Protocol):
    def control(self, name: str) -> Iterable[str]: ...


class Battlefield:
    def __init__(
        self,
        *waves: list[Enemy],
        allies: Sequence[Ally],
        chili=0,
        control_set: SupportsControl = DummyControlSet(),
        highlighter,
    ):
        """
        A battlefield representing an angry birds epic battle

        args:
            *waves, a tuple of lists containing the enemies for each wave
            allies, starting allies
            chili=0, starting chili charge
            control_set: SupportsControl = dummy_control

            a control set is an object which supports obj.control(str)
            this is basically the names of the command
            you can make your own
            take a string and if you find the name return the all
            the names that match
            if not return the an iterable with the only item being
            the string passed in passed in
            by default a control set without any bindinds is chosen

            this is all asbstract, we are always gonna be using
            mainobj as our control "set", its not the container
            but the english word

        upon instantiation of a Battlefield object
        all View(s) objects (units) will receive a unique
        integer (View.id), this id is unique to a battle
        which means, that there is not other unit
        in multiple battle waves, or summoned unit
        with the same id

        the id starts at 0 going upwards
        use View.is_same to compare units based on their identification attribute

        they also received an instance of self
        all units will get this Battlefield instance saved in their .battle attr

        because this object is mutable
        this is the way to access global Battlefield data

        if you are new to this code or i am returning
        theres a lot of instances of a class instance
        receiving data after being put in a container

        Ally() and Enemy() are free to instantiated
        they will receive their info and all other stuff
        after being added to a Battlefield()

        Effect() and all of its subclasses
        receive their info after being added
        to a unit's effect dictionary via
        View.add_neg_effects() and View.add_pos_effects()
        you are free to instatiate them without any of
        their code automatically being activated

        you are free to instatiate Battlefield()
        without units on either side, but
        Battlefield.start_battle() will raise a
        ValueError if theres no units on either side
        """
        if not waves:
            raise ValueError("No waves")

        self.control_set = control_set
        self.highlighter = highlighter

        self.WAVES = waves
        self.wave_int = 1

        self.exhaust_waves = list(waves)
        del self.exhaust_waves[0]

        self._id = -1

        enemies = {enemy.name: enemy for enemy in waves[0]}
        _allies = {ally.clsname: ally for ally in allies}

        for unit in _allies.values():
            unit.id = self.id

        for unit in enemies.values():
            unit.id = self.id

        self.allied_units = _allies
        self.enemy_units = enemies
        self.turn = 0
        self._chili = chili  # in procents
        self.result = result.no_result

        for unit in self.units.values():
            unit.battle = self

    @property
    def id(self):
        self._id += 1
        return self._id

    @property
    def chili(self):
        return self._chili

    @chili.setter
    def chili(self, setter: int):
        self._chili = setter
        if self.chili > 100:
            self._chili = 100

    @property
    def units(self):
        """return the two unit dictionaries combined/merged"""
        return self.allied_units | self.enemy_units

    def add_allied_unit(self, unit: Ally):
        unit.battle = self
        unit.id = self.id
        self.allied_units[unit.name] = unit

    def add_units_based_on_attr(self, *units: View):
        for unit in units:
            unit.id = self.id
            if isinstance(unit, Ally):
                self.add_allied_unit(unit)
            elif isinstance(unit, Enemy):
                self.add_enemy_unit(unit)
            else:
                raise ValueError

    def add_enemy_unit(self, unit: Enemy):
        unit.battle = self
        unit.id = self.id
        self.enemy_units[unit.name] = unit

    def death_check(self):
        for unit in self.units.values():
            if unit.is_dead():
                if isinstance(unit, Ally):
                    del self.allied_units[unit.clsname]
                else:
                    del self.enemy_units[unit.name]

                print(f"\n{unit.name} dies.")

        if not self.allied_units:
            self.result = result.lost

        if not self.enemy_units:
            if len(self.exhaust_waves):
                self.next_wave()
                print(f"Wave defeated! Incoming wave {self.wave_int}...\n")
            else:
                self.result = result.won

    def start_battle(self) -> result:
        if not self.units:
            raise ValueError(
                f"Missing units on either side,"
                f" allies={len(self.allied_units)},"
                f" enemies={len(self.enemy_units)}"
            )

        control = self.control_set.control

        while True:
            self.played: list[str] = []
            self.turn += 1

            print("\nBirds turn!\n")

            to_delete: dict[View, Effect] = {}

            for unit in self.enemy_units.values():
                for effect in unit.neg_effects.values():
                    effect.turns -= 1
                    if effect.turns == 0:
                        to_delete[unit] = effect

            for unit in self.allied_units.values():
                for effect in unit.pos_effects.values():
                    effect.turns -= 1
                    if effect.turns == 0:
                        to_delete[unit] = effect

            for unit, effect in to_delete.items():
                effect.on_exit()

                if effect.is_pos:
                    del unit.pos_effects[effect.name]
                else:
                    del unit.neg_effects[effect.name]

                print(f"'{effect.name}' effect expired on {unit.name}.")

            for unit in self.units.values():
                for effect in unit.effects.values():
                    effect.enemies_end_of_turn()
                    self.death_check()
                    if self.result != result.no_result:
                        return self.result

            while True:
                self.view_battle()

                check = [
                    unit
                    for unit in self.allied_units.values()
                    if unit.clsname not in self.played
                ]

                temp = [unit.name for unit in check]

                for unit in check:
                    if any(effect.is_knocked for effect in unit.effects.values()):
                        temp.remove(unit.name)

                if not temp:
                    break

                cmd = input("\nbattle> ").lower().strip().split(" ")

                command = cmd[0]

                if command in control("help"):
                    print(help["battle_help"])
                    continue

                elif command in control("attack"):
                    try:
                        attack, ally, *args = cmd
                    except ValueError:
                        print("Not enough arguments")
                        continue

                    target = args[0] if len(args) else None

                    temp = ally
                    ally = self.startswith_ally(ally)

                    if ally is None:
                        print(f"No ally found with name '{temp}'")
                        continue

                    _marker = False
                    effects = []

                    for effect in ally.effects.values():
                        if not effect.can_attack:
                            effects.append(effect.name)
                            _marker = True

                    if _marker:
                        if len(effects) == 1:
                            print(
                                f"'{ally.name}' can't attack because of '{effects[0]}' effect."
                            )
                        else:
                            string_effects = ", ".join(
                                f"'{effect}'" for effect in effects
                            )
                            print(
                                f"'{ally.name}' can't attack because of {string_effects} effects."
                            )

                        continue

                    if target is None and not ally._attack.supports_ambiguos_use:
                        print("Missing target argument.")
                        continue

                    elif target is None:
                        # grab the first enemy, it literally doesnt care
                        enemy = list(self.enemy_units.values())[0]

                    else:
                        temp = enemy
                        enemy = self.startswith_enemy(target)

                        if enemy is None:
                            print(f"Did not find an enemy with name '{temp}'.")
                            continue

                    self.played.append(ally.clsname)
                    ally.attack(self.enemy_units[enemy.name])
                    if self.result != result.no_result:
                        return self.result

                elif command in control("support"):
                    try:
                        passive, ally, *args = cmd
                    except ValueError:
                        print("Not enough arguments")
                        continue

                    if len(args) == 0:
                        target = ally
                    else:
                        target = args[0]

                    ally = self.startswith_ally(ally)

                    if ally is None:
                        continue

                    _marker = False
                    effects = []

                    for effect in ally.effects.values():
                        if not effect.can_support:
                            effects.append(effect.name)
                            _marker = True

                    if _marker:
                        if len(effects) == 1:
                            print(
                                f"'{ally.name}' can't use support because of '{effects[0]}' effect."
                            )
                        else:
                            string_effects = ", ".join(
                                f"'{effect}'" for effect in effects
                            )
                            print(
                                f"'{ally.name}' can't use support because of {string_effects} effects."
                            )

                        continue

                    target = self.startswith_ally(target)

                    if target is None:
                        continue

                    self.played.append(ally.clsname)
                    ally.support(self.allied_units[target.clsname])

                    if self.result != result.no_result:
                        return self.result

                elif command in control("chili"):
                    try:
                        attack, ally, *args = cmd
                    except ValueError:
                        print("Not enough arguments")
                        continue

                    if "-help" in args or "-h" in args:
                        print(help["chili"])
                        continue

                    ally = self.startswith_ally(ally)

                    if ally is None:
                        continue

                    _marker = False
                    effects = []

                    for effect in ally.effects.values():
                        if not effect.can_chili:
                            effects.append(effect.name)
                            _marker = True

                    if _marker:
                        if len(effects) == 1:
                            print(
                                f"'{ally.name}' can't use chili because of '{effects[0]}' effect."
                            )
                        else:
                            string_effects = ", ".join(
                                f"'{effect}'" for effect in effects
                            )
                            print(
                                f"'{ally.name}' can't use chili because of {string_effects} effects."
                            )

                        continue

                    if self.chili != 100:
                        print(
                            f"Chili is not charged up to 100%, chili is at {self.chili}%"
                        )
                        continue

                    self.played.append(ally.clsname)
                    ally.chili()
                    self.chili = 0

                    if self.result != result.no_result:
                        return self.result

                elif command in control("stat"):
                    try:
                        stat, target, *args = cmd
                    except ValueError:
                        print("Missing argument 'target' for command stat")
                        continue

                    if target in self.units:
                        target = self.units[target]

                        name = target.clsname if isinstance(target, Ally) else target.name

                        with Table(title=f"Viewing stats of {name}") as table:
                            table.add_column("Name")
                            table.add_column("Current Health/Total Health")
                            table.add_column("Effects")

                            table.add_row(
                                target.name,
                                f"{target.hp}/{target.TOTAL_HP}",
                                (", ".join(target.effects) or "No active effects"),
                            )
                    else:
                        print(f"No unit found for '{target}'")

                elif command in control("turns"):
                    for unit in self.allied_units.values():
                        if unit.clsname not in self.played:
                            print(unit.view())

                elif command in control("abort"):
                    while True:
                        i = input(
                            "Are you sure you want to abort?\nCONFIRM/no\nabort> "
                        )
                        if i == "CONFIRM":
                            return result.game_aborted
                        elif i == "no":
                            break
                        else:
                            print("Please input CONFIRM or no\n")

                elif not command:
                    continue

                else:
                    print(f"No command found for '{command}'\ntype help for help\n")

            print("\nEnemies' turn!\n")

            to_delete = {}

            for unit in self.enemy_units.values():
                for effect in unit.pos_effects.values():
                    effect.turns -= 1
                    if effect.turns == 0:
                        to_delete[unit] = effect

            for unit in self.allied_units.values():
                for effect in unit.neg_effects.values():
                    effect.turns -= 1
                    if effect.turns == 0:
                        to_delete[unit] = effect

            for unit, effect in to_delete.items():
                effect.on_exit()

                if effect.is_pos:
                    del unit.pos_effects[effect.name]
                else:
                    del unit.neg_effects[effect.name]

                print(f"'{effect.name}' effect expired on {unit.name}.")

            for unit in self.units.values():
                for effect in unit.effects.values():
                    effect.allies_end_of_turn()
                    self.death_check()
                    if self.result != result.no_result:
                        return self.result

            for enemy in list(self.enemy_units.values()):
                try:
                    self.enemy_units[enemy.name]
                except KeyError:  # the enemy is dead
                    continue

                enemy.attack()
                self.death_check()
                if self.result != result.no_result:
                    return self.result

            print("\nEnd of enemies' turn!\n")

    def startswith_unit(self, unit: str) -> Ally | Enemy | None:
        if unit in self.units:
            return self.units[unit]

        saved = ""
        for allyname in self.units:
            if allyname.startswith(unit):
                if saved:
                    print(f"There are two or more units starting with '{unit}'!")
                    return None
                saved = allyname

        if not saved:
            print(f"Didnt find a unit matching or starting with '{unit}'!")
            return None

        return self.units[saved]

    def startswith_ally(self, ally: str) -> Ally | None:
        s = self.startswith_unit(ally)
        if isinstance(s, Enemy):
            print(f"Didnt find an ally matching or starting with '{ally}'!")
            s = None

        return s

    def startswith_enemy(self, enemy: str) -> Enemy | None:
        s = self.startswith_unit(enemy)
        if isinstance(s, Ally):
            print(f"Didnt find an enemy matching or starting with '{enemy}'!")
            s = None

        return s

    def view_battle(self):
        with Table(title="Allies") as allies:
            allies.add_column("Name")
            allies.add_column("Current Health/Total Health")
            allies.add_column("Effects")

            for ally in self.allied_units.values():
                should_we_do_it = (
                    self.highlighter.switch == ally.clsname not in self.played
                )

                if should_we_do_it:
                    string = ally.clsname
                    for format in self.highlighter.current.values():
                        string = format(string)
                else:
                    string = ally.clsname

                allies.add_row(
                    string,
                    f"{ally.hp}/{ally.TOTAL_HP}",
                    ", ".join(ally.effects),
                )

        with Table(title="Enemies") as enemies:
            enemies.add_column("Name")
            enemies.add_column("Current Health/Total Health")
            enemies.add_column("Effects")

            for enemy in self.enemy_units.values():
                enemies.add_row(
                    enemy.name,
                    f"{enemy.hp}/{enemy.TOTAL_HP}",
                    ", ".join(enemy.effects),
                )

    def next_wave(self):
        wave = self.exhaust_waves[0]
        del self.exhaust_waves[0]

        for enemy in wave:
            enemy.id = self.id
            enemy.battle = self

        self.enemy_units = {enemy.name: enemy for enemy in wave}
        self.wave_int += 1
        self.played = []


def battle_interface(mainobj: "MainObj") -> result:
    fp = mainobj.jsons["picked"]

    control = mainobj.control

    # dict[birdname, list[classname]]
    CHOICES: dict[str, list[str]] = {
        name: [n for n in iter] for name, iter in BIRDS_TABLE.items()
    }
    PICKED: dict[str, str] = fp.content

    CLASSES = {cls: bird for bird, classes in CHOICES.items() for cls in classes}

    if PICKED:
        with Table(title="Currently Picked allies") as table:
            table.add_column("Name")
            table.add_column("Class")

            for name, cls in PICKED.items():
                table.add_row(name, cls)
    else:
        print(
            "\nCurrently, you have no picked allies!"
            "\nuse the pick command to pick some"
            "\nor type help for help\n"
        )

    while True:
        _INPUT = input("battle> ")
        print()

        INPUT = _INPUT.split(" ")[0]

        if INPUT in control("help"):
            print(help["prebattle_help"])

        elif INPUT == "picked":
            if not PICKED:
                print(
                    "No allies picked, use the pick command to pick some\ntype help for help\n"
                )
                continue

            with Table(title="Picked allies") as table:
                table.add_column("Name")
                table.add_column("Class")

                for name, cls in PICKED.items():
                    table.add_row(name, cls)

        elif INPUT == "choices":
            with Table(title="All allies and class choices") as table:
                table.add_column("Name")
                table.add_column("Classes")

                for name, iter in CHOICES.items():
                    table.add_row(name, ", ".join(iter))

        elif INPUT in control("pick"):
            pick, *args = _INPUT.split(" ")

            if not args:
                print("'name' is a required argument to command pick")
                continue

            if len(args) >= 2:
                name, cls, *possibly_unused = args
                if name not in CHOICES:
                    print(f"Ally '{name}' doesn't exist")
                continue
            else:
                cls = args[0]
                if cls not in CLASSES:
                    print(f"Class '{cls}' doesn't exist")
                    continue

                name = CLASSES[cls]

            try:
                CLASSES_DICT[name].get_class(cls)
            except (KeyError, ValueError):
                print(f"class {cls} is unavailable... for now")
                continue

            PICKED[name] = cls

            print(f"picked '{name}' with '{cls}' class")

        elif INPUT in control("unpick"):
            unpick, *args = _INPUT.split(" ")

            if not args:
                print("'name' is a required argument to command unpick")
                continue

            if len(args) >= 2:
                name, cls, *possibly_unused = args
                if name not in CHOICES:
                    print(f"Ally '{name}' doesn't exist")
                continue
            else:
                cls = args[0]
                if cls not in CLASSES:
                    print(f"Class '{name}' doesn't exist")
                    continue

                name = CLASSES[cls]

            if name not in PICKED:
                print(f"Class {cls} is not picked.")
                continue

            del PICKED[name]

            print(f"removed '{name}' with '{cls}' class")

        elif INPUT == "start":
            if len(PICKED) == 0:
                print("Cannot start with no allies.")
                continue

            elif len(PICKED) > mainobj.MAX_ALLIES:
                print(
                    f"Maximum amount of allies exceeded,"
                    f"\nYou may bring at most {mainobj.MAX_ALLIES} allies."
                )
                continue

            else:
                print("Battle started!")
                fp.save(PICKED)

                # dummy testing battle
                battle = Battlefield(
                    [Enemy(name=f"dummy{i}", hp=10, damage=10) for i in range(7)],
                    allies=[Ally(name, cls) for name, cls in PICKED.items()],
                    control_set=mainobj,
                    highlighter=mainobj.highlighter,
                )

                _range = 20

                for i in range(5, 101):
                    mul = i * 10
                    wave = []
                    for _ in range(7):
                        wave.append(
                            Enemy(
                                f"dummy{_}{i}",
                                hp=random.choice(
                                    range(mul - _range, mul + _range + 1, _range)
                                ),
                                damage=random.choice(
                                    range(mul - _range, mul + _range + 1, _range)
                                ),
                            )
                        )
                    battle.exhaust_waves.append(wave)

                return battle.start_battle()

        elif INPUT in control("exit"):
            return result.interface_aborted

        elif not INPUT:
            continue

        else:
            print(f"No command found for '{INPUT}'")
