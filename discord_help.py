from time import sleep


class Unit:
    def __init__(self, name, hp, damage):
        self.name = name
        self.hp = hp
        self.damage = damage
        self.current_target = None

    def attack(self, targets):
        self.set_target(targets)
        print(
            f"{self.name} attacks {self.current_target.name} for {self.damage} damage"
        )
        self.current_target.hp -= self.damage
        if self.current_target.hp <= 0:
            print(f"{self.current_target.name} has died")
            targets.remove(self.current_target)
            self.current_target = None
        sleep(1)

    def set_target(self, targets):
        # always attack the lowest health target
        self.current_target = min(targets, key=lambda x: x.hp)


class Battlefield:
    def __init__(self):
        self.allied_units = []
        self.enemy_units = []

    def summary(self):
        print("Allied units:")
        for unit in self.allied_units:
            print(f"{unit.name} - HP: {unit.hp}")
        print("Enemy units:")
        for unit in self.enemy_units:
            print(f"{unit.name} - HP: {unit.hp}")

    def add_allied_unit(self, unit):
        self.allied_units.append(unit)

    def add_enemy_unit(self, unit):
        self.enemy_units.append(unit)

    def setup_battle(self):
        self.add_allied_unit(Unit("Soldier", 100, 10))
        self.add_allied_unit(Unit("Knight", 200, 20))
        self.add_enemy_unit(Unit("Troll", 300, 12))
        self.add_enemy_unit(Unit("Orc", 150, 8))

    def start_battle(self):
        while self.allied_units and self.enemy_units:

            print("### Allies turn ###")
            for allied_unit in self.allied_units:
                allied_unit.attack(self.enemy_units)
                self.summary()

            print("### Enemies turn ###")

            for enemy_unit in self.enemy_units:
                enemy_unit.attack(self.allied_units)
                self.summary()

        if self.allied_units:
            print("Allied units won")
        else:
            print("Enemy units won")


battlefield = Battlefield()
battlefield.setup_battle()
battlefield.start_battle()
