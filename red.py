from typing import Any

battle = Any

def knight_attack(self, target): 
    global battle

    damage = 26

    target = battle.enemy_units[target]
    
    for effect in target.effects:
        if effect.__name__ == "__to_attack__":
            damage = effect(damage)
    
    target.hp -= damage

    print(f"{self.name} deals {damage} hp to {target}!")

def knight_passive(self, target):
    global battle

    target = battle.allied_units[target]

    # TODO: still dont know this
    def __to_attack__(self, damage: int):
        return (damage // 100) * 55
    
    target.effects.append(__to_attack__)
    
def red_chili(self):
    global battle

    # red's chili always attacks the highest current health target
    target = max(battle.enemy_units.values(), key=lambda x: x.hp)
    damage = 26 * 5
    target.hp -= damage

    print(f"{self.name}'s chili deals {damage} damage to {target.name}!")

    if target.hp <= 0:
        print(f"{target.name} dies.")
        del battle.enemy_units[target.name]
    else:
        print(target.view())