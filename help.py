from rich.table import Table
from rich.markup import escape

class _Help:
    
    def iter(self) -> list[str]:
        return [*self.__dict__.keys()]

    def __getitem__(self, item: str):
        return getattr(self, item)
    
    main_help = \
"""
Main help

<> - required
[] - not required

battle - get all battle names, and health bars (and rage chili charge)

turns - allies who still havent played their turn yet

abort CONFIRM - abort this battle

stat <target> - get health, name, active effects, attacks, charged attacks and passives of target

attack <ally> <enemy> - use attack ability on enemy

passive <ally> [Ally] - use passive ability of ally on ally, leave second option empty to use on passive on 
the ally itself

chili <ally> - use chili on ally

put -help or -h after any command for help

flag: -p

put "-p" at the end of any command to preview it

ex.:
    >>> attack red pig1 -p

    red would deal 26 to pig1
    remaining pig1 health: 8/108 (from 34/108)
    will survive
    ...
"""

    battle_interface = Table(title="Commands for the prebattle interface")

    battle_interface.add_column("Command name")
    battle_interface.add_column("Description")
    battle_interface.add_column("Arguments")

    battle_interface.add_row("help", "show this help menu", "No arguments")
    battle_interface.add_row("exit", "go back to the world map", "No arguments")
    battle_interface.add_row("pick", "pick this ally to play in the battle", 
                             escape("pick [ally's name] [ally's class]"))
    battle_interface.add_row("unpick", "remove this ally from playing in the battle", 
                             escape("unpick [ally's name]"))
    battle_interface.add_row("picked", "show picked allies", "No arguments")
    battle_interface.add_row("choices", "show all pickable allies and their classes", "No arguments")
    battle_interface.add_row("start", "start this battle!", "No arguments")

help = _Help()