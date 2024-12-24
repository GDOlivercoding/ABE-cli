from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING
from rich.table import Table
from rich.markup import escape

class TableMaker:
    def __init__(self, *columns: str, title: str | None = None) -> None:
        self.title = title
        self.columns = columns

    def add_rows(self, *rows: Sequence[str]):
        self.rows = rows

    def dump(self) -> Table:
        t = Table(title=self.title)
        for column in self.columns:
            t.add_column(column)

        for row in self.rows:
            t.add_row(*row)

        return t

class _Help:
    
    def iter(self) -> list[str]:
        return [*self.__dict__.keys()]

    def __getitem__(self, item: str):
        return getattr(self, item)
    
    battle_help = TableMaker(  
        "Command Name", "Description", "Arguments",
        title="Main Help\n<> - required\n[] - not required")

    battle_help.add_rows(
        ("battle", "get all battle names, and health bars (and rage chili charge)", "No args"),
        ("turns", "allies who still havent played their turn yet", "No args"),
        ("abort", "abort this battle", "abort <CONFIRM>"),
        ("stat", "view all current statistics of target", "stat <target>"),
        ("attack", "attack target enemy", "attack <ally> [target]"),
        ("passive", "use passive ability on target", "passive <ally> [target]"),
        ("chili", "use rage chili on target", "chili <target>"),
    )

    battle_help = battle_help.dump()

    prebattle_help = TableMaker(
        "Command Name", "Description", "Arguments",
        title="Commands for the prebattle interface\n<> - required\n[] - not required"
        )

    prebattle_help.add_rows(
        ("help", "show this help menu", "No arguments"),
        ("exit", "go back to the world map", "No arguments"),
        ("pick", "pick this ally to play in the battle", escape("pick <target> [class]")),
        ("unpick", "remove this ally from playing in the battle", "unpick <target>"),
        ("picked", "show picked allies", "No arguments"),
        ("choices", "show all pickable allies and their classes", "No arguments"),
        ("start", "start this battle!", "No arguments")
    )

    prebattle_help = prebattle_help.dump()

    controls_interface = TableMaker(
        "Command Name", "Description", "Arguments",
        title="Commands for the controls interface\n<> - required\n[] - not required"
    )

    controls_interface.add_rows(
        ("add", "add an alias for an action", "add <action-name> <new-name>"),
        ("del", "delete an alias for an action", "add <action> <name>"),
        ("show", "show aliases for an action, leave empty to show all", escape("show [default]")),
        ("presets", "show preset action aliases", "No arguments"),
        ("presets set", "'equip' a preset set of aliases", "presets set <name>"),
        ("presets save", "save your current aliases", "presets save <name>"),
        ("presets delete", "delete a user made preset collection", "presets delete <name>"),
        ("defaults", "Show default aliases, unremovable... for a reason.", "No arguments"),
        ("save", "save all current changes", "Only confirmation"),
        ("exit", "exit the controls interface", "Only confirmation")
    )

    controls_interface = controls_interface.dump()

class MainObj:
    def __init__(self) -> None: 
        self.jsons: dict[str, dict]
        self.fp: str
        self.data: Path

help = _Help()