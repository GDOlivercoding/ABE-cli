from battle import battle_interface, result as res

while True:
    INPUT = input("main menu> ").strip().lower()

    if INPUT == "battle":
        result = battle_interface()
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

    elif not INPUT:
        continue

    else:
        print(f"No command found for '{INPUT}'")