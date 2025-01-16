# ABE-cli
my angry birds epic cli game

run main.py to run
type help for help anywhere

## Files

### battle.py

the module where the main battle happens

declares the major `Battlefield` class
that handles all of the logic

imports classes.py and enemies.py

### classes.py

is where all the ally classes are written

contains a structural system
(of a lot of dataclasses) which also implements
objects wrapping functions to handle their functionality automatically

exports `CLASSES_DICT` 
of type: 

```python
dict[str, BirdCollection]
```

where str is the bird's name

### controls.py

a REPL where you can (almost) fully customize the "controls" (the aliases to actions in game)

type "controls" in the main menu to enter

### effects.py

is where all the status effects are written

supplies a base class to inherit from, and a lot of event calls to use for the effect, read docs from the base class

### enemies.py

not implemented, module for enemies

### flags.py

not implemented, module for ability flags

### help.py

a module with a `help` object (an instance of a custom class)

which provides rich.Table(s) of help for parts of the game

use \_\_getitem__ for attribute accesss

### main.py

the main module

### value_index.py

the file where i store values for allies (AD + percentage)

this should be moved to json in the future