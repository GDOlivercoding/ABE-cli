from help import help
from rich import print
from typing import TYPE_CHECKING

# module to change names for actions
# can be found in .\data\controls.jsons
# certain actions are not gonna be aliasable

if TYPE_CHECKING:
    from main import MainObj

def controls_interface(mainobj: "MainObj"):
    controls_file = mainobj.jsons["controls"]
    presets_file = mainobj.jsons["preset-controls"]

    # dict[action, list[aliases]]
    CONTROLS: dict[str, list[str]] = controls_file.content

    # dict[presetname, dict[action, list[aliases]]]
    PRESETS: dict[str, dict[str, list[str]]] = presets_file.content

    # dict[action, list[aliases]]
    DEFAULT_PRESET = PRESETS["DEFAULT"]

    CHANGES_BEEN_MADE = False

    control = mainobj.control

    highlighter = mainobj.highlighter
    highlighters = highlighter.highlighters

    print()
    while True:
        inp = input("controls> ")
        print()

        parts = inp.split(" ")
        command = parts[0]

        if command in control("help"):
            print(help["controls_interface"])

        elif command == "defaults":
            print("defaults:\n")
            print("\n".join(CONTROLS), "\n")

        elif command == "add":
            try:
                add, action, new, *args = parts
            except ValueError:
                print("Missing arguments for command add")
                continue

            if action not in CONTROLS:
                print("Action doesnt exist")
                continue

            if new in CONTROLS[action]:
                print(f"'{new}' alias already exists for action '{action}'")
                continue

            CONTROLS[action].append(new)
            CHANGES_BEEN_MADE = True

            print(f"Added alias '{new}'")

        elif command == "del":
            try:
                delete, action, alias, *args = parts
            except ValueError:
                print("Missing arguments for command del")
                continue

            if action not in CONTROLS:
                print("Action doesnt exist")
                continue

            if alias not in CONTROLS[action]:
                print(f"'{alias}' doesnt exist for action '{action}'")
                continue

            if alias in DEFAULT_PRESET[action]:
                print(f"Cannot remove alias '{alias}' which is a default.")
                continue

            CONTROLS[action].remove(alias)
            CHANGES_BEEN_MADE = True

            print(f"Removed alias '{alias}'")

        elif command == "show":
            show, *args = parts

            if not args:
                print("Current controls:\n")
                for action, aliases in CONTROLS.items():
                    print(f"\n    {action}: {", ".join(aliases)}")
                continue

            action = " ".join(args)

            if action not in CONTROLS:
                print("Action doesnt exist")
                continue

            print(f"Aliases for action '{action}':\n")

            print("\n".join(CONTROLS[action]), "\n")

        elif command == "save":
            if not CHANGES_BEEN_MADE:
                print("No changes to save")
                continue

            print("Are you sure you want to save your changes?")
            while True:
                i = input("y/n> ")

                if i == "y":
                    controls_file.content = CONTROLS
                    controls_file.save()

                    presets_file.content = PRESETS
                    presets_file.save()

                    general = mainobj.jsons["general"]
                    content = general.content
                    content["highlighter"]["types"] = highlighter.current.keys()
                    content["highlighter"]["switch"] = highlighter.switch
                    general.save(content)

                    print("Success")
                    CHANGES_BEEN_MADE = False
                    break

                elif i == "n":
                    print("Cancelled saving")
                    break
                else:
                    print("Invalid input")

        elif command in control("exit"):
            if not CHANGES_BEEN_MADE:
                break

            _exit = False

            print("Are you sure you want to exit? There are unsaved changes")
            while True:
                i = input("exit/cancel/save(and exit)> ")

                if i == "save":
                    controls_file.save(CONTROLS)

                    presets_file.content = PRESETS
                    presets_file.save()

                    print("Success")
                    _exit = True
                    break

                elif i == "cancel":
                    print("Cancelled saving")
                    break

                elif i == "exit":
                    print("Exiting without saving changes...")
                    _exit = True

                else:
                    print("Invalid input")

            if _exit:
                break

        elif command == "presets":
            if len(parts) == 1:  # were dealing with bare presets

                for presetname, iter in PRESETS.items():
                    print(f"\n{presetname}:")

                    for action, aliases in iter.items():
                        print(f"\n    {action}: {", ".join(aliases)}")

                continue

            subcommand = parts[1]

            if subcommand == "set":
                try:
                    presets, set, name, *args = parts
                except ValueError:
                    print("Missing arguments for command presets set")
                    continue

                name = " ".join([name] + args)

                if name not in PRESETS:
                    print(f"preset '{name}' doesnt exist")
                    continue

                CONTROLS = PRESETS[name]
                CHANGES_BEEN_MADE = True

                print("Success")

            elif subcommand == "save":
                try:
                    presets, save, name, *args = parts
                except ValueError:
                    print("Missing arguments for command presets save")
                    continue

                name = " ".join([name] + args)

                if name in PRESETS:
                    print(f"There is already a preset with the name {name}!")
                    continue

                PRESETS[name] = CONTROLS
                CHANGES_BEEN_MADE = True

                print(f"Saved current controls as {name}!")

            elif subcommand == "delete":
                try:
                    presets, delete, name, *args = parts
                except ValueError:
                    print("Missing arguments for command presets save")
                    continue

                name = " ".join([name] + args)

                if name not in PRESETS:
                    print(f"preset '{name}' doesnt exist")
                    continue

                # hehehe i love hard coding
                if name == "DEFAULT":
                    print("Cannot delete default preset")
                    continue

                print(f"Are you sure you want to delete preset '{name}'?\n")
                while True:
                    i = input("y/n> ")

                    if i == "y":
                        del PRESETS[name]
                        print(f"Deleted '{name}'")
                        CHANGES_BEEN_MADE = True
                        break

                    elif i == "n":
                        print("Cancelled deletion")
                        break

                    else:
                        print("Invalid input")

            elif command == "highlighter":
                high, *args = parts

                if not args:
                    print("Missing arguments.")
                    continue

                item, value = args

                if item == "switch":
                    highlighter.switch = True if args[0].capitalize() == "True" else False

                else:
                    if value in highlighters:
                        highlighter.current[item] = highlighters[item]