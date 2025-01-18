# cannot write this module yet
# Enemy cannot inherit from View
# update: View has its own module now

from typing import Final

from effects import Effect
from view import View

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

class Brute(Enemy):
    """A category with high health, damage and charging """