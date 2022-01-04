import copy
import json

import pandas as pd
import streamlit as st

from optimizer import data_handlers as dh
from optimizer.data_structures import (
    MAX_VALUE,
    STAT_LIST,
    STAT_NORMALISATION_DICT,
    StatStick,
    StatStickMax,
)
from optimizer.optimizer import Optimizer

##################
### APP CONFIG ###
##################

APP_THEME = "streamlit"
GRID_SIZE = 32  # extra pixel count per hero for generating AgGrid tables


###################
### APP HELPERS ###
###################


def set_app_design_configs():
    st.set_page_config(
        page_title="Gear Optimizer",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def generate_derivative_input_data(state, gear_file):
    """Generates all the required derivative data from input if it does not already exist.
    Essentially all the set up after loading the gear file and before any further user interaction.

    Args:
        state ([type]): [description]
        gear_file ([type]): [description]
    """

    if not state["data_initialised"]:

        # 'raw' data
        hero_and_gear_data = json.load(gear_file)

        ##############
        ### HEROES ###
        ##############

        all_heroes_base_df = dh.get_raw_hero_data()

        user_hero_data = dh.get_user_hero_data(hero_and_gear_data)

        # canonical list of user heroes stored in state
        state.user_hero_name_list = [i["name"] for i in user_hero_data]

        # creating baseline Hero objects for every user hero
        state.initial_hero_objects = dh.generate_hero_objects_from_df(
            all_heroes_base_df.loc[state.user_hero_name_list]
        )

        # copy created as they will be unequipped in the optimization process
        # but we want to retain the 'original' equip state, perhaps
        state.optimized_hero_objects = copy.deepcopy(state.initial_hero_objects)

        #############
        ### ITEMS ###
        #############

        # item/gear data
        user_item_data = dh.get_user_item_data(hero_and_gear_data)
        state.initial_item_objects = dh.generate_item_objects_from_list(
            user_item_data
        )

        # copy created as they will be unequipped in the optimization process
        # but we want to retain the 'original' equip state, perhaps
        state.optimized_item_objects = copy.deepcopy(state.initial_item_objects)

        # canonical item input for optimizer
        state.item_df = dh.get_item_df(state.initial_item_objects)

        ############
        ### BOTH ###
        ############

        # initial assignment of items to heroes based on gear file
        initial_equip_dict = dh.generate_initial_equip_dict(
            user_hero_data, user_item_data
        )

        # conversion to make it easier to use
        initial_equip_lists = dh.get_equip_lists_from_equip_dict(
            state.user_hero_name_list, initial_equip_dict
        )

        # equip hero objects with item objects according to the initial assignments
        equip_items_to_heroes(
            state.user_hero_name_list,
            state.initial_hero_objects,
            state.initial_item_objects,
            initial_equip_lists,
        )

        # equip the optimized set as well -> this will be altered later
        equip_items_to_heroes(
            state.user_hero_name_list,
            state.optimized_hero_objects,
            state.optimized_item_objects,
            initial_equip_lists,
        )

        # set flag to indicate that session is initialised
        state["data_initialised"] = True

    else:
        pass


def equip_items_to_heroes(hero_list, hero_objects, item_objects, equip_list):

    for hero_ix, hero in enumerate(hero_list):
        for item_ix in equip_list[hero]:
            hero_objects[hero_ix].equip_item(item_objects[item_ix])


def initialise_selected_hero_state(state, selected_hero):

    # get the index for the selected hero
    selected_hero_index = state.user_hero_name_list.index(selected_hero)

    # initialise a hero info dictionary in state to store info about processed heroes
    if "hero_info" not in state:
        state["hero_info"] = {}

    # initialise hero state each time a new hero is introduced
    if selected_hero not in state["hero_info"]:
        state["hero_info"][selected_hero] = {}

        # shorter alias for saved state of current hero
        hero_state = state["hero_info"][selected_hero]

        hero_state["name"] = selected_hero
        hero_state["index"] = selected_hero_index
        hero_state["initial"] = state.initial_hero_objects[selected_hero_index]
        hero_state["optimized"] = state.optimized_hero_objects[
            selected_hero_index
        ]
        # initial states for additional stats form
        hero_state["imprint_stat_index"] = 0
        hero_state["imprint_stat_value"] = 0
        hero_state["ee_stat_index"] = 0
        hero_state["ee_stat_value"] = 0
        hero_state["artifact_attack"] = 0
        hero_state["artifact_health"] = 0

        # initial states for constraints form
        hero_state["min_constraints_form"] = 0
        hero_state["max_constraints_form"] = MAX_VALUE
        hero_state["stat_weightings_form"] = 1
        hero_state["set_selection_form"] = None
        hero_state["hero_weighting_form"] = 5
    else:

        hero_state = state["hero_info"][selected_hero]

    return hero_state


def submit_additional_stats(hero_state, **kwargs):

    # update the states of the additional stat vars for selected hero
    # based on kwarg names
    for k, v in kwargs.items():
        hero_state[k] = v

    # applying the additional stats to the hero objects in initial and optimized
    # should be a better way of doing this programmatically
    for stage in ["optimized", "initial"]:

        hero_state[stage].apply_additional_stats(
            StatStick.from_dict(
                {
                    STAT_LIST[kwargs.get("imprint_stat_index")]: kwargs.get(
                        "imprint_stat_value"
                    )
                }
            ),
            additional_type="imprint",
        )
        hero_state[stage].apply_additional_stats(
            StatStick.from_dict(
                {
                    STAT_LIST[kwargs.get("ee_stat_index")]: kwargs.get(
                        "ee_stat_value"
                    )
                }
            ),
            additional_type="exclusive_equipment",
        )
        hero_state[stage].apply_additional_stats(
            StatStick(
                Attack=kwargs.get("artifact_attack"),
                Health=kwargs.get("artifact_health"),
            ),
            additional_type="artifact",
        )


def drop_current_hero(state, current_hero):
    """removes the currently selected hero from state tables"""

    if current_hero in state.minimum_constraints.index:

        state.minimum_constraints.drop(index=current_hero, inplace=True)
        state.maximum_constraints.drop(index=current_hero, inplace=True)
        state.base_with_additional_stats.drop(index=current_hero, inplace=True)
        state.base_stats.drop(index=current_hero, inplace=True)
        state.set_type_constraints.drop(index=current_hero, inplace=True)
        state.stat_weightings.drop(index=current_hero, inplace=True)

        return 0

    # handling for bad user input (hero not in current tables)
    return 1


def submit_constraints(
    hero_state, constraints_response, set_type_selection, hero_weight
):

    # set form input states to submitted values
    hero_state["min_constraints_form"] = constraints_response["data"][
        "Minimum"
    ].values
    hero_state["max_constraints_form"] = constraints_response["data"][
        "Maximum"
    ].values
    hero_state["stat_weightings_form"] = constraints_response["data"][
        "Stat_Weighting"
    ].values
    hero_state["set_selection_form"] = list(set_type_selection)
    hero_state["hero_weighting_form"] = hero_weight


def create_or_update_optimization_inputs(
    state, hero_state, constraints_response
):
    """Takes the stats and constraints of the current hero and builds onto
    a set of dataframes containing the same for all heroes considered for optimization

    Args:
        state ([type]): [description]
        hero_state ([type]): [description]
        constraints_response ([type]): [description]
    """

    # generate temporary individual tables for the current hero
    # Maybe a little verbose but it works
    # TODO: Main problem is that I want to present a limited set of form stats
    # but the optimizer needs the full set
    min_df = pd.DataFrame(
        StatStick.from_dict(
            constraints_response["data"].set_index("index")["Minimum"]
        ).__dict__,
        index=[hero_state["name"]],
    )

    max_df = pd.DataFrame(
        StatStickMax.from_dict(
            constraints_response["data"].set_index("index")["Maximum"]
        ).__dict__,
        index=[hero_state["name"]],
    )

    stat_weight_df = (
        pd.DataFrame(
            StatStick.from_dict(
                constraints_response["data"].set_index("index")[
                    "Stat_Weighting"
                ]
            ).__dict__,
            index=[hero_state["name"]],
        )
        * hero_state["hero_weighting_form"]
    )

    # normalise values based on STAT_NORMALISATION_DICT
    stat_weight_df = stat_weight_df.mul(
        pd.Series(STAT_NORMALISATION_DICT), axis=1
    ).fillna(0)

    # convert set type return to dataframe
    set_type_df = pd.DataFrame(
        [[hero_state["set_selection_form"]]],
        columns=["set_type_constraint"],
        index=[hero_state["name"]],
    )

    base_with_additional_stats_df = pd.DataFrame(
        hero_state["optimized"].base_with_additional_stats.__dict__,
        index=[hero_state["name"]],
    )

    base_stats_df = pd.DataFrame(
        hero_state["optimized"].base_stats.__dict__,
        index=[hero_state["name"]],
    )

    # create new state if collection dfs don't exist
    if not "minimum_constraints" in state:
        state.minimum_constraints = min_df
        state.maximum_constraints = max_df
        state.base_with_additional_stats = base_with_additional_stats_df
        state.base_stats = base_stats_df
        state.set_type_constraints = set_type_df
        state.stat_weightings = stat_weight_df
    else:

        # add or update collection dfs for optimizer
        state.minimum_constraints = edit_or_append_df(
            state.minimum_constraints, min_df
        )
        state.maximum_constraints = edit_or_append_df(
            state.maximum_constraints, max_df
        )
        state.base_with_additional_stats = edit_or_append_df(
            state.base_with_additional_stats,
            base_with_additional_stats_df,
        )
        state.base_stats = edit_or_append_df(state.base_stats, base_stats_df)
        state.set_type_constraints = edit_or_append_df(
            state.set_type_constraints, set_type_df
        )
        state.stat_weightings = edit_or_append_df(
            state.stat_weightings, stat_weight_df
        )


def edit_or_append_df(
    collection_df: pd.DataFrame, single_row_df: pd.DataFrame
) -> pd.DataFrame:
    """Adds a single row dataframe to an existing dataframe or edits if the index already exists.
    Assumes that columns are consistent (it may fail otherwise).
    Main use case is for building up hero stats, constraints, etc to use in the optimizer.
    """

    if single_row_df.index[0] in collection_df.index:
        collection_df.loc[single_row_df.index.tolist(), :] = single_row_df
    else:
        collection_df = collection_df.append(
            single_row_df.loc[single_row_df.index]
        )
    return collection_df


@st.experimental_memo
def get_equipment_csv(equipment_df_dict):

    # add the hero name as a column in each dataframe
    for k, v in equipment_df_dict.items():
        v.insert(0, "Hero", k)

    # combine into single dataframe as a csv
    return pd.concat(list(equipment_df_dict.values())).to_csv().encode("utf-8")


def run_optimizer(state, solver_time, worker_count):
    opt = Optimizer(
        item_df=state.item_df,
        hero_base_df=state.base_stats,
        hero_additional_df=state.base_with_additional_stats,
    )
    opt.add_constraints(
        hero_min_df=state.minimum_constraints,
        hero_max_df=state.maximum_constraints,
        set_constraints_df=state.set_type_constraints,
    )
    opt.set_objective_optimisation(stat_weightings_df=state.stat_weightings)
    opt.define_solver(timer=solver_time, worker_count=worker_count)
    state["response_dict"] = opt.run_solver()
