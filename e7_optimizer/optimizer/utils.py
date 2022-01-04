from __future__ import annotations

from collections import Counter
from functools import reduce
from typing import Any, Dict

import pandas as pd

from optimizer.data_structures import (
    ItemTypes,
    SetTypes,
    StatStick,
    StatStickMax,
)

###############
### CLASSES ###
###############


class Item:
    def __init__(
        self,
        name: str,
        item_type: ItemTypes,
        set_type: SetTypes,
        stats: StatStick,
        is_equipped=False,
    ):
        self.name = name
        self.item_type = item_type
        self.set_type = set_type
        self.stats = stats
        self.is_equipped = is_equipped
        self.equipped_to: Any[Hero, None] = None

    @classmethod
    def from_str(cls, a_str):
        return cls(**eval("dict({})".format(a_str)))

    def __repr__(self):
        return f"""
        Item Name: {self.name}
        Item Type: {self.item_type.name}
        Set Type: {self.set_type.name}
        Stats: {repr(self.stats)}
        Equipped To: { (self.equipped_to.name if self.equipped_to else None) }
        """

    def item_equipped(self, hero: Hero):
        """Handles equipping/unequipping on item side"""

        # unequip item from current hero
        if self.equipped_to:
            self.equipped_to.unequip_item(self)

        self.is_equipped = True
        self.equipped_to = hero


class Hero:
    def __init__(
        self,
        name: str,
        base_stats: StatStick,
        min_constraints: StatStick = StatStick(),
        max_constraints: StatStickMax = StatStickMax(),
        additional_stats: StatStick = StatStick(),
        exclusive_equipment: StatStick = StatStick(),
        imprint: StatStick = StatStick(),
        artifact: StatStick = StatStick(),
    ):
        self.name = name
        self.base_stats = base_stats
        self.base_with_additional_stats = base_stats

        # stat constraints for optimization - redundant
        self.min_constraints = min_constraints
        self.max_constraints = max_constraints

        # additional sources of stats
        self.artifact = artifact
        self.exclusive_equipment = exclusive_equipment
        self.imprint = imprint
        self.additional_stats = additional_stats

        # initialise equipment
        self.equipment: Dict[ItemTypes, Item] = {
            item_type: None for item_type in ItemTypes
        }

        # active set bonuses
        self.active_sets: Dict[SetTypes, int] = dict.fromkeys(
            [i for i in SetTypes], 0
        )
        self.equipped_stats: StatStick = base_stats
        self.update_stats()

    def __repr__(self):
        return f"""\
        Hero Name: {self.name}
        Equipped Stats: {self.equipped_stats}
        Equipped Sets: { {k.name:v for k, v in self.active_sets.items() if v > 0} }
        Equipment: { {item_type.name:item.name if item else None for item_type, item in self.equipment.items()} }"""

    def get_equipment_list(self):
        """Returns a list of equipped items in an easy to handle format"""

        # create empty stats in case of no equipment in any slots
        stat_names = list(StatStick().__dict__.keys())
        empty_stats = dict(zip(stat_names, [""] * len(stat_names)))

        equipment_list = []
        for k, v in self.equipment.items():
            if v != None:
                equipment_list.append(
                    {
                        "Slot": k.name,
                        "Name": v.name,
                        "Set": v.set_type.name,
                        **v.stats.__dict__,
                    }
                )
            else:
                equipment_list.append(
                    {"slot": k, "name": "", "set": "", **empty_stats}
                )

        return equipment_list

    def dict_repr(self):

        active_sets_dict = {
            "Active_Sets": [
                k.name for k, v in self.active_sets.items() if v > 0
            ]
        }

        hero_dict = {
            self.name: {
                **self.equipped_stats.__dict__,
                **active_sets_dict,
            }
        }
        return hero_dict

    def dataframe_repr(self):
        # equipped stats, name, etc
        repr_df = pd.DataFrame(self.dict_repr())
        return repr_df

    def apply_additional_stats(
        self, additional_stats: StatStick = None, additional_type=None
    ):
        """Applies additional stats that are separate from standard gear -> artifact, exclusive equipment, imprints, other?"""

        if additional_type == "artifact":
            self.artifact = additional_stats
        elif additional_type == "exclusive_equipment":
            self.exclusive_equipment = additional_stats
        elif additional_type == "imprint":
            self.imprint = additional_stats
        else:
            self.additional_stats = additional_stats

        self.update_stats()

    def apply_stat_multipliers(self, equipped_stats):

        # apply the percentage multipliers for attack, health, and def sets
        equipped_stats.Attack += (
            equipped_stats.AttackPercent * 0.01 * self.base_stats.Attack
        )
        equipped_stats.Health += (
            equipped_stats.HealthPercent * 0.01 * self.base_stats.Health
        )
        equipped_stats.Defense += (
            equipped_stats.DefensePercent * 0.01 * self.base_stats.Defense
        )
        equipped_stats.Speed += (
            equipped_stats.SpeedPercent * 0.01 * self.base_stats.Speed
        )

        return equipped_stats

    def update_sets(self):
        """determines which sets are active so that bonus stats can be applied"""

        # TODO: import this info
        four_piece_bonus = [
            SetTypes.COUNTER,
            SetTypes.ATTACK,
            SetTypes.DESTRUCTION,
            SetTypes.REVENGE,
            SetTypes.SPEED,
            SetTypes.INJURY,
            SetTypes.RAGE,
            SetTypes.LIFESTEAL,
        ]
        two_piece_bonus = [
            SetTypes.IMMUNITY,
            SetTypes.CRIT,
            SetTypes.DEFENSE,
            SetTypes.HEALTH,
            SetTypes.UNITY,
            SetTypes.PENETRATION,
            SetTypes.RESIST,
            SetTypes.HIT,
        ]

        # creating a dictionary of 0 counts for each possible set type
        four_piece_counts = dict.fromkeys(
            [set_type for set_type in four_piece_bonus], 0
        )
        two_piece_counts = dict.fromkeys(
            [set_type for set_type in two_piece_bonus], 0
        )

        active_set = {**two_piece_counts, **four_piece_counts}

        # collect the set types for each equipped item
        sets = [
            item.set_type for item in self.equipment.values() if item != None
        ]

        set_counts = Counter(sets)

        # 4 piece should be 1 at most
        active_four_piece = {
            k: v // 4 for k, v in set_counts.items() if k in four_piece_bonus
        }
        active_two_piece = {
            k: v // 2 for k, v in set_counts.items() if k in two_piece_bonus
        }

        active_set.update({**active_four_piece, **active_two_piece})

        self.active_sets = active_set

    def update_stats(self):
        """
        Updates the hero stats based on the set of equipped items.
        In the case of open slots, the added value is 0
        """

        # add just the additional stats to base stats
        self.base_with_additional_stats = (
            self.base_stats
            + self.additional_stats
            + self.artifact
            + self.exclusive_equipment
            + self.imprint
        )

        # add equipment stats and all additional stats sources
        self.equipped_stats = self.base_with_additional_stats + reduce(
            lambda x, y: x + y,
            [
                item.stats if item != None else StatStick()
                for key, item in self.equipment.items()
                if key != "name"
            ],
        )

        # add set bonuses stats
        # update sets - could be completely separate
        self.update_sets()

        # set bonus statstick

        # TODO: import this info
        bonus_dict = {
            SetTypes.ATTACK: 45,
            SetTypes.HEALTH: 20,
            SetTypes.DEFENSE: 20,
            SetTypes.CRIT: 12,
            SetTypes.DESTRUCTION: 40,
            SetTypes.HIT: 20,
            SetTypes.RESIST: 20,
            SetTypes.REVENGE: 12,
            SetTypes.SPEED: 25,
        }

        # StatStick storing all the stat bonuses according to the active sets
        # speed bonus comes from speed or revenge set
        set_bonus_stats = StatStick(
            AttackPercent=bonus_dict[SetTypes.ATTACK]
            * self.active_sets[SetTypes.ATTACK],
            HealthPercent=bonus_dict[SetTypes.HEALTH]
            * self.active_sets[SetTypes.HEALTH],
            DefensePercent=bonus_dict[SetTypes.DEFENSE]
            * self.active_sets[SetTypes.DEFENSE],
            CriticalHitChancePercent=bonus_dict[SetTypes.CRIT]
            * self.active_sets[SetTypes.CRIT],
            CriticalHitDamagePercent=bonus_dict[SetTypes.DESTRUCTION]
            * self.active_sets[SetTypes.DESTRUCTION],
            EffectivenessPercent=bonus_dict[SetTypes.HIT]
            * self.active_sets[SetTypes.HIT],
            EffectResistancePercent=bonus_dict[SetTypes.RESIST]
            * self.active_sets[SetTypes.RESIST],
            SpeedPercent=(
                bonus_dict[SetTypes.SPEED] * self.active_sets[SetTypes.SPEED]
            )
            + (
                bonus_dict[SetTypes.REVENGE]
                * self.active_sets[SetTypes.REVENGE]
            ),
        )

        # add the set bonuses to the equipped stats
        self.equipped_stats += set_bonus_stats

        # apply the percentage multipliers for attack, health, and def sets (percents are converted to decimal here)
        # TODO: import this info
        self.equipped_stats.Attack += (
            self.equipped_stats.AttackPercent * 0.01 * self.base_stats.Attack
        )
        self.equipped_stats.Health += (
            self.equipped_stats.HealthPercent * 0.01 * self.base_stats.Health
        )
        self.equipped_stats.Defense += (
            self.equipped_stats.DefensePercent * 0.01 * self.base_stats.Defense
        )
        self.equipped_stats.Speed += (
            self.equipped_stats.SpeedPercent * 0.01 * self.base_stats.Speed
        )

    def equip_item(self, item_to_equip: Item):

        if self.equipment[item_to_equip.item_type]:
            item_currently_equipped = self.equipment[item_to_equip.item_type]
            self.unequip_item(item_currently_equipped, stat_update=False)

        # equip the new item to hero and assign hero to the item
        self.equipment[item_to_equip.item_type] = item_to_equip
        item_to_equip.item_equipped(self)

        self.update_stats()

    def unequip_item(self, item_currently_equipped: Item, stat_update=True):
        """
        Unequips a given item based on its slot.
        If called from equip_item method, then the stat update is not run by passing False to the stat_update flag.
        This is because it will be run by equip_item anyway
        """

        if (
            self.equipment[item_currently_equipped.item_type]
            == item_currently_equipped
        ):

            # remove item assignment from hero
            self.equipment[item_currently_equipped.item_type] = None

            # remove hero assignment from item
            item_currently_equipped.equipped_to = None

        else:
            print("Item not equipped.")

        if stat_update:
            self.update_stats()
