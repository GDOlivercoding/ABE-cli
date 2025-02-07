from __future__ import annotations

from enum import Enum, auto

# fmt: off

class ABLTFLAGS(Enum):
    HEALING = auto()
    DAMAGE = auto()
    EFFECTS = auto()
    SUPER = auto()


class Target(Enum):
    # the target is a single unit passed in as a parameter by default
    single = auto()

    # target all allies or enemies with the same effects and damage
    all = auto()

    # info applies to everyone except target
    # effects and damage to target provided in flags
    others = auto()


BIRDS_TABLE: dict[str, list[str]] = {
    "red": ["knight", "guardian", "samurai", "avenger", "paladin", "stone-guard"],
    "chuck": [
        "mage",
        "lightning-bird",
        "rainbird",
        "wizard",
        "thunderbird",
        "illusionist",
    ],
    "matilda": ["cleric", "druid", "princess", "priestess", "bard", "witch"],
    "bomb": ["pirate", "cannoneer", "berserker", "capt'n", "sea dog", "frost savage"],
    "blues": ["trickers", "rogues", "marksmen", "skulkers", "treasure-hunters"],
}

VALUE_INDEX = {
    "red": {
        "knight": {
            "attack": {
                "damage": 115
            },
            "passive": {}
        },
        "guardian": {
            "attack": {
                "damage": 110
            },
            "passive": {}
        },
        "samurai": {
            "attack": {
                "damage": 50,
                "slice": 3
            }
        },
        "avenger": {
            "attack": {
                "damage": 90
            },
            "passive": {}
        },
        "paladin": {
            "attack": {
                "damage": 135,
                "heal": 30
            },
            "passive": {}
        },
        "stone guard": {
            "attack": {
                "damage": 65,
                "slice": 2
            }
        },
        "chili": {
            "damage": 500,
            "arena": 350
        }
    },
    "chuck": {
        "mage": {
            "attack": {
                "damage": 55
            },
            "passive": {
                "damage": 75
            }
        },
        "lightning-bird": {
            "attack": {
                "damage": 45,
                "dispell_chance": 65
            },
            "passive": {}
        },
        "rainbird": {
            "attack": {
                "damage": 20,
                "poison": 35
            },
            "passive": {
                "heal": 20
            }
        },
        "wizard": {
            "attack": {
                "damage": 100,
                "damage1": 67,
                "damage2": 45,
                "damage3": 30
            },
            "passive": {
                "chili_boost": 5,
                "stun_chance": 20
            }
        },
        "thunderbird": {
            "attack": {
                "damage": 50,
                "effectiveness": 25
            },
            "passive": {
                "damage": 45
            }
        },
        "illusionist": {
            "attack": {
                "damage": 100,
                "shared_damage": 35
            },
            "passive": {
                "super_atk_damage": 50
            }
        },
        "chili": {
            "supers": 5,
            "arena": 3
        }
    },
    "matilda": {
        "cleric": {
            "attack": {
                "damage": 110,
                "heal": 25
            },
            "passive": {
                "heal": 15
            }
        },
        "druid": {
            "attack": {
                "damage": 35,
                "poison": 100
            },
            "passive": {
                "heal": 22,
                "others": 10
            }
        },
        "princess": {
            "attack": {
                "damage": 125
            },
            "passive": {
                "heal": 30
            }
        },
        "bard": {
            "attack": {
                "damage": 160,
                "stun_chance": 15
            },
            "passive": {
                "main_heal": 10,
                "side_heal": 5
            }
        },
        "witch": {
            "attack": {
                "damage": 160
            },
            "passive": {
                "attack": 20,
                "health": 20
            }
        },
        "chili": {
            "heal": 35
        }
    },
    "bomb": {
        "chili": {
            "damage": 150
        },
        "pirate": {
            "attack": {
                "damage": 100
            },
            "passive": {
                "buff": 25
            }
        },
        "cannoneer": {
            "attack": {
                "damage": 30,
                "slice": 3,
                "debuff": 20
            },
            "passive": {
                "eff": 80
            }
        },
        "capt'n": {
            "attack": {
                "damage": 90
            },
            "passive": {
                "deplete": 10,
                "buff": 60
            }
        },
        "berserker": {
            "attack": {
                "damage": 105
            },
            "passive": {}
        },
        "sea-dog": {
            "attack": {
                "damage": 125
            },
            "passive": {}
        },
        "frost-savage": {
            "attack": {
                "damage": 90,
                "bonus": 150
            },
            "passive": {
                "chance": 25,
                "turns": 1
            }
        }
    },
    "blues": {
        "chili": {
            "damage": 200
        },
        "marksmen": {
            "attack": {
                "damage": 50,
                "slice": 2,
                "weaken": 35
            },
            "passive": {}
        }
    }
}
