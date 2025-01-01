from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterable, Mapping
from enum import Enum, auto
from typing import Final, Protocol, Self, Sequence, TYPE_CHECKING

from rich.console import Console
from rich import print
from rich.table import Table as RichTable

from value_index import BIRDS_TABLE
from help import help
from new_classes import CLASSES_DICT


class Table(RichTable):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        print(self)


CONSOLE = Console()

if TYPE_CHECKING:
    from battle import View
    from effects import Effect


class ConvertibleToInt(Protocol):
    def __int__(self) -> int: ...


# helper


def process_attack(self: View, target: View, damage: int, effects: Sequence[Effect]):
    for effect in self.effects.values():
        self, target, damage, effects = effect.on_attack(self, target, damage, effects)

    for effect in target.effects.values():
        target, self, damage, effects = effect.on_hit(target, self, damage, effects)

    target.hp -= damage
    target.add_neg_effects(*effects)

    return self, target, damage, effects


weapon_passives = [
    # % chance to deal % extra damage
    "Critical Strike",
    # heal % of dealt damage
    "Hocus Pocus",
    # % chance to deal % damage to another target
    "Chain Attack",
    # % chance to stun target for turns
    "Stun",
    # % chance to immediately remove all helpful effects
    "Dispell",
]

shield_passives = [
    # Take % less damage
    "Vigor"
    # deal % more damage
    "Might"
]

# classes


class View(ABC):
    @abstractmethod
    def __init__(self) -> None:
        # still very experimenting with effects

        # XXX differentiate positive and negative effects due to cleanse and dispell
        # for now, theres no dispell or cleanse
        self.name: str  # assigned during init
        self.battle: Battlefield  # assigned once added to the Battlefield object
        self.is_ally: bool  # assigned with class
        self.neg_effects: dict[str, Effect]  # assigned during init
        self.pos_effects: dict[str, Effect]  # assigned during init
        self.id: int  # assigned once added to the Battlefield object
        self.hp: int
        self.TOTAL_HP: int
        ...

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

    def deal_damage[
        T: View
    ](
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
        target = self if direct else self.get_target(source)

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                target, source, damage, effects = effect.on_hit(
                    self, source, damage, effects
                )

        self.battle.chili += 5
        target.hp -= damage
        effects = list(target.add_neg_effects(*effects))

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                effect.after_hit(target, source, damage, effects)

        return target, source, damage, effects

    def heal(self, heal: ConvertibleToInt):
        heal = int(heal)
        target = self

        for effect_vals in [eff.effects.values() for eff in self.battle.units.values()]:
            for effect in effect_vals:
                heal = effect.on_heal(heal)

        target.hp += heal

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
            effect.is_pos = False # if its an undefined effect

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


class Ally(View):
    def __init__(self, name: str, _class: str) -> None:
        self.name = name
        self.clsname = _class

        self.bird = CLASSES_DICT[name]
        self._class = self.bird.get_class(_class)

        # TODO add hp to classes
        self._hp = self._class.hp
        self.TOTAL_HP = self._class.TOTAL_HP

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


class Enemy(View):
    def __init__(self, name: str, hp: int, damage: int):
        self.name = name.lower()
        self._hp = hp
        self.TOTAL_HP = hp
        self.damage = damage
        self.is_ally: Final = False
        self.neg_effects: dict[str, Effect] = {}
        self.pos_effects: dict[str, Effect] = {}

    def attack(self):
        self.set_target()

        battle = self.battle
        damage = self.damage

        target = self.current_target
        effects = []

        self, target, damage, effects = process_attack(self, target, damage, effects)

        print(f"{self.name} attacks {target.name} for {damage} damage")

        if target.is_dead():
            print(f"{target.name} dies.")
            del battle.allied_units[target.name]
        else:
            print(target.view())

    def set_target(self):
        # always attack the lowest health target
        self.current_target = min(self.battle.allied_units.values(), key=lambda x: x.hp)


class result(Enum):
    lost = auto()
    won = auto()
    game_aborted = auto()
    interface_aborted = auto()
    no_result = auto()


class Battlefield:
    def __init__(self, *waves: list[Enemy], allies: Sequence[Ally], chili=0):
        """
        A battlefield representing an angry birds epic battle

        args:
            *waves, a tuple of lists containing the enemies for each wave
            allies, starting allies
            chili=0, starting chili charge

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

        self.WAVES = waves
        self.wave_int = 1

        # next(self.exhaust_waves) everytime we win a wabe
        self.exhaust_waves = iter(waves)

        self._id = -1

        # split because
        # there isnt a good type
        # for | operation

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
                if unit.is_ally:
                    del self.allied_units[unit.name]
                else:
                    del self.enemy_units[unit.name]

                print(f"{unit.name} dies.")

        if not self.allied_units:
            return result.lost

        if not self.enemy_units:
            return result.won

        return result.no_result

    def start_battle(self) -> result:
        if not self.units:
            raise ValueError(
                f"Missing units on either side,"
                f" allies={len(self.allied_units)},"
                f" enemies={len(self.enemy_units)}"
            )

        while True:
            self.played = []
            self.turn += 1

            for unit in self.allied_units.values():
                for effect in unit.effects.values():
                    effect.enemies_end_of_turn()
                    if (b := self.death_check()) != result.no_result:
                        return b

            print("\nBirds turn!\n")

            to_delete: dict[View, Effect] = {}

            for unit in self.allied_units.values():
                for effect in unit.effects.values():
                    effect.turns -= 1
                    if effect.turns <= 0:
                        to_delete[unit] = effect

            for unit, effect in to_delete.items():
                effect.on_exit()

                if effect.is_pos:
                    del unit.pos_effects[effect.name]
                else:
                    del unit.neg_effects[effect.name]

                print(f"'{effect.name}' effect expired on {unit.name}.")

            for unit in self.allied_units.values():
                if any(effect.is_knocked for effect in unit.effects.values()):
                    self.played.append(unit.name)

            while True:

                if (b := self.death_check()) != result.no_result:
                    return b

                check = [
                    unit
                    for unit in self.allied_units.values()
                    if unit not in self.played
                ]

                # for every bird that hasnt played their turn
                # if they are all knocked that means
                # theyve all played their turn
                for unit in check:
                    if not any(effect.is_knocked for effect in unit.effects.values()):
                        break
                else:  # nobreak
                    break

                # list of strings of allies that have already self.played their turn

                cmd = input("\nbattle> ").lower().strip().split(" ")
                print()

                command = cmd[0]

                if command == "help":
                    print(help["battle_help"])
                    continue

                elif command == "attack":

                    try:
                        attack, ally, target, *args = cmd
                    except ValueError:
                        print("Not enough arguments")
                        continue

                    if "-help" in args or "-h" in args:
                        print(help["attack"])
                        continue

                    if ally not in self.allied_units:
                        print("Ally name doesn't exist")
                        continue

                    ally = self.allied_units[ally]
                    _marker = False

                    for name, effect in ally.effects.items():
                        if not effect.can_attack:
                            print(
                                f"{ally.name} can't attack because of '{name}' effect"
                            )
                            _marker = True

                    if _marker:
                        continue

                    if target not in self.enemy_units:
                        print(f"Enemy name doesn't exist: {target}")
                        continue

                    ally.attack(self.enemy_units[target])
                    self.played.append(ally.name)

                elif command == "passive":
                    try:
                        passive, ally, *args = cmd
                    except ValueError:
                        print("Not enough arguments")
                        continue

                    if len(args) == 0:
                        target = ally
                    else:
                        target = args[0]

                    if "-help" in args or "-h" in args:
                        print(help["passive"])
                        continue

                    if ally not in self.allied_units:
                        print("Ally name doesn't exist")
                        continue

                    ally = self.allied_units[ally]
                    _marker = False

                    for name, effect in ally.effects.items():
                        if not effect.can_passive:
                            print(
                                f"{ally.name} can't use passive ability because of '{name}' effect"
                            )
                            _marker = True

                    if _marker:
                        continue

                    ally.support(self.allied_units[target])
                    self.played.append(ally.name)

                elif command == "chili":
                    try:
                        attack, ally, *args = cmd
                    except ValueError:
                        print("Not enough arguments")
                        continue

                    if "-help" in args or "-h" in args:
                        print(help["chili"])
                        continue

                    if ally not in self.allied_units:
                        print("Ally name doesn't exist")
                        continue

                    ally = self.allied_units[ally]
                    _marker = False

                    for name, effect in ally.effects.items():
                        if not effect.can_chili:
                            print(
                                f"{ally.name} can't use chili because of '{name}' effect"
                            )
                            _marker = True
                            break

                    if _marker:
                        continue

                    if self.chili != 100:
                        print(f"Chili is not charged up to 100%, chili is at {self.chili}%")
                        continue

                    ally.chili()

                    self.chili = 0
                    self.played.append(ally.name)

                elif command == "battle":

                    with Table(title="Allies") as allies:

                        allies.add_column("Name")
                        allies.add_column("Current Health/Total Health")
                        allies.add_column("Effects")

                        for ally in self.allied_units.values():
                            allies.add_row(
                                ally.name,
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

                elif command == "stat":
                    try:
                        stat, target, *args = cmd
                    except ValueError:
                        print("Missing argument 'target' for command stat")
                        continue

                    if target in self.units:
                        target = self.units[target]

                        with Table(title=f"Viewing stats of {target.name}") as table:

                            table.add_column("Name")
                            table.add_column("Current Health/Total Health")
                            table.add_column("Effects")

                            table.add_row(
                                target.name,
                                f"{target.hp}/{target.TOTAL_HP}",
                                (
                                    ", ".join(f'"{name}"' for name in target.effects)
                                    or "No active effects"
                                ),
                            )
                    else:
                        print(f"No unit found for '{target}'")

                elif command == "turns":
                    for unit in self.allied_units.values():
                        if unit.name not in self.played:
                            print(unit.view())

                elif command == "abort":
                    while True:
                        i = input(
                            "Are you sure you want to abort?\nCONFIRM/no\nabort> "
                        )
                        if i == "CONFIRM":
                            return result.game_aborted
                        elif i.lower() == "no":
                            break
                        else:
                            print("Please input CONFIRM or no\n")

                elif not command:
                    continue

            print("\nEnemies' turn!\n")

            to_delete = {}

            for unit in self.enemy_units.values():
                for effect in unit.effects.values():
                    effect.turns -= 1
                    if effect.turns == 0:
                        to_delete[unit] = effect

            for unit, effect in to_delete.items():
                effect.on_exit()

                if effect.is_pos:
                    del unit.pos_effects[effect.name]
                else:
                    del unit.neg_effects[effect.name]

                print(f"{effect.name} expired on {unit.name}.")

            for enemy in self.enemy_units.values():
                enemy.attack()
                if (b := self.death_check()) != result.no_result:
                    if b == result.won and len(list(self.exhaust_waves)):
                        self.new_wave(next(self.exhaust_waves))
                    else:
                        return b

            print("\nEnd of enemies' turn!\n")

    def new_wave(self, wave: list[Enemy]):
        for enemy in wave:
            enemy.id = self.id
            enemy.battle = self

        self.enemy_units = {enemy.name: enemy for enemy in wave}
        self.wave_int += 1


def battle_interface(mainobj) -> result:

    # dict[birdname, list[classname]]
    CHOICES: dict[str, list[str]] = {
        name: [n for n in iter if n.lower() != "chili"]
        for name, iter in BIRDS_TABLE.items()
    }
    PICKED: dict[str, str] = {}

    while True:
        _INPUT = input("battle> ")
        print()

        INPUT = _INPUT.split(" ")[0]

        if INPUT == "help":
            print(help["prebattle_help"])

        elif INPUT == "picked":
            if not PICKED:
                print(
                    "No allies picked, use the pick command to pick some\ntype help for help"
                )
                continue

            with Table(title="Picked allies") as table:
                table.add_column("Name")
                table.add_column("Class")

                for name, cls in PICKED.items():
                    table.add_row(name, cls)

        elif INPUT == "choices":
            table = Table(title="All allies and class choices")

            table.add_column("Name")
            table.add_column("Classes")

            for name, iter in CHOICES.items():
                table.add_row(name, ", ".join(iter))

            print(table)

        elif INPUT == "pick":

            pick, *args = _INPUT.split(" ")

            try:
                name = args[0]
            except IndexError:
                print("'name' is a required argument to command pick")
                continue

            if name not in CHOICES:
                print(f"Ally '{name}' doesn't exist")
                continue

            if len(CHOICES[name]) != 1:
                del args[0]
                cls = " ".join(args)

                if not cls:
                    print(
                        "'cls' is an optional argument to command pick\nunless theres only 1 class\nwhich there isn't"
                    )
                    continue

                for _cls in CHOICES[name]:
                    if _cls == cls:
                        break
                else:
                    print(f"No class named '{cls}' for ally '{name}'")
                    continue
                PICKED[name] = cls
            else:
                cls = CHOICES[name][0]
                PICKED[name] = cls

            print(f"picked '{name}'  with '{cls}' class")

        elif INPUT == "unpick":
            try:
                unpick, name, *cls = _INPUT.split(" ")
            except ValueError:
                print("'name' is a required argument for command unpick")
                continue

            try:
                del PICKED[name]
            except KeyError:
                print(f"Ally '{name}' is not picked, or doesn't exist")
                continue

            print(f"'{name}' unpicked with '{cls}' class")

        elif INPUT == "start":
            if len(PICKED) == 0:
                print("Cannot start with no allies.")
                continue
            else:
                print("Battle started!\n")

                battle = Battlefield(
                    allies=[Ally(name, cls) for name, cls in PICKED.items()]
                )

                battle.add_enemy_unit(Enemy("dummy", 200, 10))
                return battle.start_battle()

        elif INPUT == "exit":
            return result.interface_aborted

        elif not INPUT:
            continue

        else:
            print(f"No command found for '{INPUT}'")
