from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum, IntEnum, auto, unique
from functools import reduce
from typing import Any, Dict, List, Set, Union
from collections import Counter
import pandas as pd


##########################
### CONSTANT / CONFIGS ###
##########################

MAX_VALUE = 999999999

# attack: 4, critchance: 40 -> one point in crit chance is worth 10 points in attack
# [Attack, Health, Defense, Crit Chance, Crit Damage, Effectiveness, Effect Resistance, Speed]
# current values based on gear stat max values
STAT_NORMALISATION_LIST = [4, 1, 6, 40, 29, 25, 25, 51]

HERO_DATA_URL = (
    "http://e7-optimizer-game-data.s3-accelerate.amazonaws.com/herodata.json?"
)

ARTIFACT_DATA_URL = "http://e7-optimizer-game-data.s3-accelerate.amazonaws.com/artifactdata.json?"

HERO_DATA_PATH = "./data/hero_data.csv"

# GEAR_PATH = "../data/gear.json"


#############
### ENUMS ###
#############


@unique
class SetTypes(IntEnum):
    ATTACK = auto()
    DEFENSE = auto()
    HEALTH = auto()
    SPEED = auto()
    CRIT = auto()
    DESTRUCTION = auto()
    HIT = auto()
    RESIST = auto()
    IMMUNITY = auto()
    RAGE = auto()
    LIFESTEAL = auto()
    UNITY = auto()
    REVENGE = auto()
    PENETRATION = auto()
    COUNTER = auto()
    INJURY = auto()


@unique
class ItemTypes(IntEnum):
    WEAPON = auto()
    HELMET = auto()
    ARMOR = auto()
    NECKLACE = auto()
    RING = auto()
    BOOTS = auto()


###############
### CLASSES ###
###############


@dataclass
class StatStick:
    Attack: int = 0
    AttackPercent: int = 0
    Health: int = 0
    HealthPercent: int = 0
    Defense: int = 0
    DefensePercent: int = 0
    CriticalHitChancePercent: int = 0
    CriticalHitDamagePercent: int = 0
    EffectivenessPercent: int = 0
    EffectResistancePercent: int = 0
    Speed: int = 0
    SpeedPercent: int = 0

    @classmethod
    def from_str(cls, a_str):
        return cls(**eval("dict({})".format(a_str)))

    @classmethod
    def from_dict(cls, a_dict):
        return cls(**a_dict)

    def stat_summation(self):
        return sum(self.__dict__.values())

    def __add__(self, other: StatStick):
        """addition by another statstick or single value"""

        return StatStick(
            *(
                getattr(self, dim.name) + getattr(other, dim.name)
                for dim in fields(self)
            )
        )

    def __mul__(self, other: Any[StatStick, float]):
        """multiplication by another statstick or single value"""

        if type(other) == StatStick:
            return StatStick(
                *(
                    getattr(self, dim.name) * getattr(other, dim.name)
                    for dim in fields(self)
                )
            )
        else:
            return StatStick(
                *(getattr(self, dim.name) * other for dim in fields(self))
            )


# This only exists since I don't know how to set a conditional default value
@dataclass
class StatStickMax(StatStick):
    Attack: int = MAX_VALUE
    AttackPercent: int = MAX_VALUE
    Health: int = MAX_VALUE
    HealthPercent: int = MAX_VALUE
    Defense: int = MAX_VALUE
    DefensePercent: int = MAX_VALUE
    CriticalHitChancePercent: int = MAX_VALUE
    CriticalHitDamagePercent: int = MAX_VALUE
    EffectivenessPercent: int = MAX_VALUE
    EffectResistancePercent: int = MAX_VALUE
    Speed: int = MAX_VALUE
    SpeedPercent: int = MAX_VALUE


############################
### STRUCTURED CONSTANTS ###
############################

SET_TYPE_STATS = {
    SetTypes.ATTACK: {
        "stat": "AttackPercent",
        "stat_bonus": 45,
        "threshold": 4,
    },
    SetTypes.HEALTH: {
        "stat": "HealthPercent",
        "stat_bonus": 20,
        "threshold": 2,
    },
    SetTypes.DEFENSE: {
        "stat": "DefensePercent",
        "stat_bonus": 20,
        "threshold": 2,
    },
    SetTypes.CRIT: {
        "stat": "CriticalHitChancePercent",
        "stat_bonus": 12,
        "threshold": 2,
    },
    SetTypes.DESTRUCTION: {
        "stat": "CriticalHitDamagePercent",
        "stat_bonus": 40,
        "threshold": 4,
    },
    SetTypes.HIT: {
        "stat": "EffectivenessPercent",
        "stat_bonus": 20,
        "threshold": 2,
    },
    SetTypes.RESIST: {
        "stat": "EffectResistancePercent",
        "stat_bonus": 20,
        "threshold": 2,
    },
    SetTypes.REVENGE: {
        "stat": "SpeedPercent",
        "stat_bonus": 12,
        "threshold": 4,
    },
    SetTypes.SPEED: {"stat": "SpeedPercent", "stat_bonus": 25, "threshold": 4},
    SetTypes.IMMUNITY: {"threshold": 2},
    SetTypes.PENETRATION: {"threshold": 2},
    SetTypes.LIFESTEAL: {"threshold": 4},
    SetTypes.RAGE: {"threshold": 4},
    SetTypes.UNITY: {"threshold": 2},
    SetTypes.COUNTER: {"threshold": 4},
}

STAT_LIST = list(StatStick().__dict__.keys())
HIDDEN_STAT_COLS = [
    "AttackPercent",
    "HealthPercent",
    "DefensePercent",
    "SpeedPercent",
]
DISPLAY_STAT_LIST = [i for i in STAT_LIST if i not in HIDDEN_STAT_COLS]

SET_TYPES = list(SetTypes)

STAT_NORMALISATION_DICT = dict(zip(DISPLAY_STAT_LIST, STAT_NORMALISATION_LIST))
