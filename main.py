from __future__ import annotations
import json
from battle import battle_interface, result as res
from controls import controls_interface
from pathlib import Path

class JSON(Path):
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.raw_content = self.read_text()
        self.content: dict = json.loads(self.raw_content)
    
    def save(self, data: dict | None = None):
        if data is None:
            self.write_text(json.dumps(self.content, indent=4))
        else:
            self.write_text(json.dumps(data, indent=4))

class MainObj:
    def __init__(self) -> None:
        self.data = Path(__file__).parent / "data"
        self.jsons: dict[str, JSON] = {}
        self._jsons: dict[str, Path] = {}

        for path in self.data.iterdir():
            self.jsons[path.stem] = JSON(path)

        self.fp = __file__

    def control(self, name: str) -> list[str]:
        return self.jsons["controls"].content.get(name, [name])

mainobj = MainObj()

while True:
    INPUT = input("main menu> ").strip().lower()

    if INPUT == "battle":
        result = battle_interface(mainobj)
        print()

        match result:
            case res.won:
                print("You won! :D")

            case res.lost:
                print("You lost! :C")

            case res.game_aborted:
                print("Game Aborted... :/")

            case res.interface_aborted:
                print("Left prebattle interface... :S")

    elif INPUT == "controls":
        controls_interface(mainobj)

    elif not INPUT:
        continue

    else:
        print(f"No command found for '{INPUT}'")