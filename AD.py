from dataclasses import dataclass

# AD (attack damage) file, providing the base damage values
# this file will later grab these values from jsons or other files

@dataclass
class PercDmgObject:
    DAMAGE: int

    def __mod__(self, other: int):
        return DamageObject(self.DAMAGE, other)

@dataclass
class DamageObject:
    base: int
    multiplier: int

    @property
    def damage(self):
        return int((self.base / 100) * self.multiplier)

    def __int__(self):
        return self.damage
    
    def __str__(self):
        return str(self.damage)
    
# perc % int is the same as int procent of perc
red = chuck = matilda = bomb = blues = PercDmgObject(20)
