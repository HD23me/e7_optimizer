from typing import Dict, List
import pandas as pd
import os
import requests

from optimizer.data_structures import (
    HERO_DATA_URL,
    HERO_DATA_PATH,
    ItemTypes,
    SetTypes,
    StatStick,
)
from optimizer.utils import Item, Hero


def get_raw_hero_data() -> pd.DataFrame:
    """Creates or loads raw hero data"""

    if not os.path.isfile(HERO_DATA_PATH):

        stat_map = {
            "atk": "Attack",
            "hp": "Health",
            "spd": "Speed",
            "def": "Defense",
            "chc": "CriticalHitChancePercent",
            "chd": "CriticalHitDamagePercent",
            "eff": "EffectivenessPercent",
            "efr": "EffectResistancePercent",
        }

        response = requests.get(HERO_DATA_URL)
        data = response.json()

        hero_data_list = {}
        for hero, vals in data.items():

            hero_data_list[hero] = vals["calculatedStatus"][
                "lv60SixStarFullyAwakened"
            ]

        # store as df and rename columns
        df = pd.DataFrame(hero_data_list).T[stat_map.keys()]
        df.columns = list(map(stat_map.get, df.columns))

        # convert fractional values to % - easier for integer based optimization
        for col in [i for i in df.columns if i[-7:] == "Percent"]:
            df[col] = df[col] * 100

        df.index.name = "name"

        # save df to local
        df.to_csv(HERO_DATA_PATH)

    else:
        df = pd.read_csv(HERO_DATA_PATH, index_col="name")

    return df


def get_user_hero_data(data, awaken_levels=[4, 5, 6]) -> List[Dict]:
    """
    Extracts required hero data from user's hero data (base stats).
    Default args only grabs user's heroes that are 4* awakened or higher

    """

    user_hero_data = [
        {"name": i["name"], "id": i["id"]}
        for i in data["heroes"]
        if ("awaken" in i.keys()) and (i["awaken"] in awaken_levels)
    ]

    return user_hero_data


def get_user_item_data(hero_and_gear_data) -> List[Dict]:
    """
    Generates a list of item dictionaries containing required
    item information, including equip status

    Args:
        hero_and_gear_data ([type]): 'raw' json user data on heroes and gear

    Returns:
        [type]: [description]
    """
    user_item_data = [
        {
            "name": i["name"],
            "id": i["id"],
            "ingameEquippedId": i["ingameEquippedId"],
            "mainStatType": i["mainStatType"],
            "mainStatValue": i["mainStatValue"],
            "substats": i["substats"],
            "gear": i["gear"],
            "set": i["set"],
        }
        for i in hero_and_gear_data["items"]
    ]

    return user_item_data


def generate_item_objects_from_list(user_item_data: List[Dict]) -> List[Item]:
    """Parses the fields loaded from the gear file and generates an item object for each item.

    Args:
        user_item_data (List[Dict]): [description]

    Returns:
        List[Item]: [description]
    """

    # look ups for converting naming convention used in gear file to project names
    set_map = {
        "ImmunitySet": SetTypes.IMMUNITY,
        "LifestealSet": SetTypes.LIFESTEAL,
        "HitSet": SetTypes.HIT,
        "CounterSet": SetTypes.COUNTER,
        "RevengeSet": SetTypes.REVENGE,
        "DestructionSet": SetTypes.DESTRUCTION,
        "SpeedSet": SetTypes.SPEED,
        "InjurySet": SetTypes.INJURY,
        "AttackSet": SetTypes.ATTACK,
        "DefenseSet": SetTypes.DEFENSE,
        "PenetrationSet": SetTypes.PENETRATION,
        "CriticalSet": SetTypes.CRIT,
        "RageSet": SetTypes.RAGE,
        "HealthSet": SetTypes.HEALTH,
        "ResistSet": SetTypes.RESIST,
        "UnitySet": SetTypes.UNITY,
    }

    mainstat_map = {
        "acc": "EffectivenessPercent",
        "att": "Attack",
        "att_rate": "AttackPercent",
        "cri": "CriticalHitChancePercent",
        "cri_dmg": "CriticalHitDamagePercent",
        "def": "Defense",
        "def_rate": "DefensePercent",
        "max_hp": "Health",
        "max_hp_rate": "HealthPercent",
        "res": "EffectResistancePercent",
        "speed": "Speed",
    }

    item_objects = []

    for item in user_item_data:

        name = item["name"]
        item_type = item["gear"]
        set_type = item["set"]
        mainstat_type = item["mainStatType"]
        mainstat_value = item["mainStatValue"]
        substats = item["substats"]

        # converting 'rates' into integer percentage values
        if mainstat_type in [
            "att_rate",
            "def_rate",
            "max_hp_rate",
            "cri",
            "acc",
            "cri_dmg",
        ]:
            mainstat_value *= 100

        # convert input into combined dict representation
        combined_stats = {i["type"]: int(i["value"]) for i in substats}
        combined_stats[mainstat_map[mainstat_type]] = int(mainstat_value)

        item_objects.append(
            Item(
                name=name,
                item_type=ItemTypes[item_type.upper()],
                set_type=set_map[set_type],
                stats=StatStick.from_dict(combined_stats),
            )
        )

    return item_objects


def get_item_df(item_objects: List[Item]) -> pd.DataFrame:
    """Generates a dataframe of item information from the list of item objects.
    The main use case is as an input to the optimizer.

    TODO: Maybe add method to Item class to generate a dataframe representation

    Args:
        item_objects (List[Item]): [description]

    Returns:
        pd.DataFrame: [description]
    """

    parsed_items = []

    for item in item_objects:
        info_dict = item.stats.__dict__
        info_dict["name"] = item.name
        info_dict["set_type"] = item.set_type
        info_dict["item_type"] = item.item_type

        parsed_items.append(info_dict)

    item_df = pd.DataFrame(parsed_items)

    return item_df


def generate_hero_objects_from_df(
    all_heroes_base_df: pd.DataFrame,
) -> List[Hero]:
    """
    Takes in the raw hero stats df and creates
    hero objects from the Hero class which are stored in a list
    This defines the base stats for each Hero.

    Args:
        all_heroes_base_df (pd.DataFrame): [description]

    Returns:
        List[Hero]: [description]
    """

    # should use programmatic creation of StatStick but this is fine
    hero_objects = all_heroes_base_df.apply(
        lambda x: Hero(
            name=x.name,
            base_stats=StatStick(
                Attack=x["Attack"],
                Health=x["Health"],
                Defense=x["Defense"],
                AttackPercent=0,
                HealthPercent=0,
                DefensePercent=0,
                CriticalHitChancePercent=x["CriticalHitChancePercent"],
                CriticalHitDamagePercent=x["CriticalHitDamagePercent"],
                Speed=x["Speed"],
                SpeedPercent=0,
                EffectivenessPercent=x["EffectivenessPercent"],
                EffectResistancePercent=x["EffectResistancePercent"],
            ),
        ),
        axis=1,
    ).values

    return hero_objects


def generate_initial_equip_dict(user_hero_data, user_item_data) -> Dict:
    """
    Creates a dictionary of size no_heroes*no_items where the value
    indicates whether the hero has the item equipped or not.
    This structure conforms with the optimizer equip variables,
    and so could be used for initialisation.

    {(hero_id, user_id): 0 or 1 }

    Matches are based on the IDs provided in the user's gear file.


    Args:
        user_hero_data ([type]): [description]
        user_item_data ([type]): [description]

    Returns:
        Dict: [description]
    """

    initial_equip_dict = {}
    for hero_id, hero in enumerate(user_hero_data):
        for item_id, item in enumerate(user_item_data):
            if item["ingameEquippedId"] == "undefined":
                initial_equip_dict[(hero_id, item_id)] = 0
            elif int(item["ingameEquippedId"]) == hero["id"]:
                initial_equip_dict[(hero_id, item_id)] = 1
            else:
                initial_equip_dict[(hero_id, item_id)] = 0

    return initial_equip_dict


def get_equip_lists_from_equip_dict(selected_hero_list, equip_dict):
    """converts an equip_dict of realized variables
    into a list of items for a set of heroes to equip.

    {hero: [item_1, item_2, ...]}

    """

    # initialise equip_lists dictionary
    equip_lists = {hero: [] for hero in selected_hero_list}

    # append item index for each hero
    for hero_item, equip_state in equip_dict.items():
        if equip_state == 1:
            equip_lists[selected_hero_list[hero_item[0]]].append(hero_item[1])

    return equip_lists
