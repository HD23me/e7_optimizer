import copy
import json
import sys

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit import cli as stcli

import app_helper as helper
from app_helper import APP_THEME, GRID_SIZE
from optimizer import data_handlers as dh
from optimizer.data_structures import (
    DISPLAY_STAT_LIST,
    MAX_VALUE,
    SET_TYPES,
    STAT_LIST,
    STAT_NORMALISATION_DICT,
    StatStick,
    StatStickMax,
)
from optimizer.optimizer import Optimizer


# def generate_derivative_input_data(state, gear_file):
#     """Generates all the required derivative data from input if it does not already exist.
#     Essentially all the set up after loading the gear file and before any further user interaction.

#     Args:
#         state ([type]): [description]
#         gear_file ([type]): [description]
#     """

#     if not state["data_initialised"]:

#         # 'raw' data
#         hero_and_gear_data = json.load(gear_file)

#         ##############
#         ### HEROES ###
#         ##############

#         all_heroes_base_df = dh.get_raw_hero_data()

#         user_hero_data = dh.get_user_hero_data(hero_and_gear_data)

#         # canonical list of user heroes stored in state
#         state.user_hero_name_list = [i["name"] for i in user_hero_data]

#         # creating baseline Hero objects for every user hero
#         state.initial_hero_objects = dh.generate_hero_objects_from_df(
#             all_heroes_base_df.loc[state.user_hero_name_list]
#         )

#         # copy created as they will be unequipped in the optimization process
#         # but we want to retain the 'original' equip state, perhaps
#         state.optimized_hero_objects = copy.deepcopy(state.initial_hero_objects)

#         #############
#         ### ITEMS ###
#         #############

#         # item/gear data
#         user_item_data = dh.get_user_item_data(hero_and_gear_data)
#         state.initial_item_objects = dh.generate_item_objects_from_list(
#             user_item_data
#         )

#         # copy created as they will be unequipped in the optimization process
#         # but we want to retain the 'original' equip state, perhaps
#         state.optimized_item_objects = copy.deepcopy(state.initial_item_objects)

#         # canonical item input for optimizer
#         state.item_df = dh.get_item_df(state.initial_item_objects)

#         ############
#         ### BOTH ###
#         ############

#         # initial assignment of items to heroes based on gear file
#         initial_equip_dict = dh.generate_initial_equip_dict(
#             user_hero_data, user_item_data
#         )

#         # conversion to make it easier to use
#         initial_equip_lists = dh.get_equip_lists_from_equip_dict(
#             state.user_hero_name_list, initial_equip_dict
#         )

#         # equip hero objects with item objects according to the initial assignments
#         equip_items_to_heroes(
#             state.user_hero_name_list,
#             state.initial_hero_objects,
#             state.initial_item_objects,
#             initial_equip_lists,
#         )

#         # equip the optimized set as well -> this will be altered later
#         equip_items_to_heroes(
#             state.user_hero_name_list,
#             state.optimized_hero_objects,
#             state.optimized_item_objects,
#             initial_equip_lists,
#         )

#         # set flag to indicate that session is initialised
#         state["data_initialised"] = True

#     else:
#         pass


# def equip_items_to_heroes(hero_list, hero_objects, item_objects, equip_list):

#     for hero_ix, hero in enumerate(hero_list):
#         for item_ix in equip_list[hero]:
#             hero_objects[hero_ix].equip_item(item_objects[item_ix])


# def initialise_selected_hero_state(state, selected_hero):

#     # get the index for the selected hero
#     selected_hero_index = state.user_hero_name_list.index(selected_hero)

#     # initialise a hero info dictionary in state to store info about processed heroes
#     if "hero_info" not in state:
#         state["hero_info"] = {}

#     # initialise hero state each time a new hero is introduced
#     if selected_hero not in state["hero_info"]:
#         state["hero_info"][selected_hero] = {}

#         # shorter alias for saved state of current hero
#         hero_state = state["hero_info"][selected_hero]

#         hero_state["name"] = selected_hero
#         hero_state["index"] = selected_hero_index
#         hero_state["initial"] = state.initial_hero_objects[selected_hero_index]
#         hero_state["optimized"] = state.optimized_hero_objects[
#             selected_hero_index
#         ]
#         # initial states for additional stats form
#         hero_state["imprint_stat_index"] = 0
#         hero_state["imprint_stat_value"] = 0
#         hero_state["ee_stat_index"] = 0
#         hero_state["ee_stat_value"] = 0
#         hero_state["artifact_attack"] = 0
#         hero_state["artifact_health"] = 0

#         # initial states for constraints form
#         hero_state["min_constraints_form"] = 0
#         hero_state["max_constraints_form"] = MAX_VALUE
#         hero_state["stat_weightings_form"] = 1
#         hero_state["set_selection_form"] = None
#         hero_state["hero_weighting_form"] = 5
#     else:

#         hero_state = state["hero_info"][selected_hero]

#     return hero_state


# def submit_additional_stats(hero_state, **kwargs):

#     # update the states of the additional stat vars for selected hero
#     # based on kwarg names
#     for k, v in kwargs.items():
#         hero_state[k] = v

#     # applying the additional stats to the hero objects in initial and optimized
#     # should be a better way of doing this programmatically
#     for stage in ["optimized", "initial"]:

#         hero_state[stage].apply_additional_stats(
#             StatStick.from_dict(
#                 {
#                     STAT_LIST[kwargs.get("imprint_stat_index")]: kwargs.get(
#                         "imprint_stat_value"
#                     )
#                 }
#             ),
#             additional_type="imprint",
#         )
#         hero_state[stage].apply_additional_stats(
#             StatStick.from_dict(
#                 {
#                     STAT_LIST[kwargs.get("ee_stat_index")]: kwargs.get(
#                         "ee_stat_value"
#                     )
#                 }
#             ),
#             additional_type="exclusive_equipment",
#         )
#         hero_state[stage].apply_additional_stats(
#             StatStick(
#                 Attack=kwargs.get("artifact_attack"),
#                 Health=kwargs.get("artifact_health"),
#             ),
#             additional_type="artifact",
#         )


# def drop_current_hero(state, current_hero):
#     """removes the currently selected hero from state tables"""

#     if current_hero in state.minimum_constraints.index:

#         state.minimum_constraints.drop(index=current_hero, inplace=True)
#         state.maximum_constraints.drop(index=current_hero, inplace=True)
#         state.base_with_additional_stats.drop(index=current_hero, inplace=True)
#         state.base_stats.drop(index=current_hero, inplace=True)
#         state.set_type_constraints.drop(index=current_hero, inplace=True)
#         state.stat_weightings.drop(index=current_hero, inplace=True)

#         return 0

#     # handling for bad user input (hero not in current tables)
#     return 1


# def submit_constraints(
#     hero_state, constraints_response, set_type_selection, hero_weight
# ):

#     # set form input states to submitted values
#     hero_state["min_constraints_form"] = constraints_response["data"][
#         "Minimum"
#     ].values
#     hero_state["max_constraints_form"] = constraints_response["data"][
#         "Maximum"
#     ].values
#     hero_state["stat_weightings_form"] = constraints_response["data"][
#         "Stat_Weighting"
#     ].values
#     hero_state["set_selection_form"] = list(set_type_selection)
#     hero_state["hero_weighting_form"] = hero_weight


# def create_or_update_optimization_inputs(
#     state, hero_state, constraints_response
# ):
#     """Takes the stats and constraints of the current hero and builds onto
#     a set of dataframes containing the same for all heroes considered for optimization

#     Args:
#         state ([type]): [description]
#         hero_state ([type]): [description]
#         constraints_response ([type]): [description]
#     """

#     # generate temporary individual tables for the current hero
#     # Maybe a little verbose but it works
#     # TODO: Main problem is that I want to present a limited set of form stats
#     # but the optimizer needs the full set
#     min_df = pd.DataFrame(
#         StatStick.from_dict(
#             constraints_response["data"].set_index("index")["Minimum"]
#         ).__dict__,
#         index=[hero_state["name"]],
#     )

#     max_df = pd.DataFrame(
#         StatStickMax.from_dict(
#             constraints_response["data"].set_index("index")["Maximum"]
#         ).__dict__,
#         index=[hero_state["name"]],
#     )

#     stat_weight_df = (
#         pd.DataFrame(
#             StatStick.from_dict(
#                 constraints_response["data"].set_index("index")[
#                     "Stat_Weighting"
#                 ]
#             ).__dict__,
#             index=[hero_state["name"]],
#         )
#         * hero_state["hero_weighting_form"]
#     )

#     # normalise values based on STAT_NORMALISATION_DICT
#     stat_weight_df = stat_weight_df.mul(
#         pd.Series(STAT_NORMALISATION_DICT), axis=1
#     ).fillna(0)

#     # convert set type return to dataframe
#     set_type_df = pd.DataFrame(
#         [[hero_state["set_selection_form"]]],
#         columns=["set_type_constraint"],
#         index=[hero_state["name"]],
#     )

#     base_with_additional_stats_df = pd.DataFrame(
#         hero_state["optimized"].base_with_additional_stats.__dict__,
#         index=[hero_state["name"]],
#     )

#     base_stats_df = pd.DataFrame(
#         hero_state["optimized"].base_stats.__dict__,
#         index=[hero_state["name"]],
#     )

#     # create new state if collection dfs don't exist
#     if not "minimum_constraints" in state:
#         state.minimum_constraints = min_df
#         state.maximum_constraints = max_df
#         state.base_with_additional_stats = base_with_additional_stats_df
#         state.base_stats = base_stats_df
#         state.set_type_constraints = set_type_df
#         state.stat_weightings = stat_weight_df
#     else:

#         # add or update collection dfs for optimizer
#         state.minimum_constraints = edit_or_append_df(
#             state.minimum_constraints, min_df
#         )
#         state.maximum_constraints = edit_or_append_df(
#             state.maximum_constraints, max_df
#         )
#         state.base_with_additional_stats = edit_or_append_df(
#             state.base_with_additional_stats,
#             base_with_additional_stats_df,
#         )
#         state.base_stats = edit_or_append_df(state.base_stats, base_stats_df)
#         state.set_type_constraints = edit_or_append_df(
#             state.set_type_constraints, set_type_df
#         )
#         state.stat_weightings = edit_or_append_df(
#             state.stat_weightings, stat_weight_df
#         )


# def edit_or_append_df(
#     collection_df: pd.DataFrame, single_row_df: pd.DataFrame
# ) -> pd.DataFrame:
#     """Adds a single row dataframe to an existing dataframe or edits if the index already exists.
#     Assumes that columns are consistent (it may fail otherwise).
#     Main use case is for building up hero stats, constraints, etc to use in the optimizer.
#     """

#     if single_row_df.index[0] in collection_df.index:
#         collection_df.loc[single_row_df.index.tolist(), :] = single_row_df
#     else:
#         collection_df = collection_df.append(
#             single_row_df.loc[single_row_df.index]
#         )
#     return collection_df


# @st.experimental_memo
# def get_equipment_csv(equipment_df_dict):

#     # add the hero name as a column in each dataframe
#     for k, v in equipment_df_dict.items():
#         v.insert(0, "Hero", k)

#     # combine into single dataframe as a csv
#     return pd.concat(list(equipment_df_dict.values())).to_csv().encode("utf-8")


# def run_optimizer(state, solver_time, worker_count):
#     opt = Optimizer(
#         item_df=state.item_df,
#         hero_base_df=state.base_stats,
#         hero_additional_df=state.base_with_additional_stats,
#     )
#     opt.add_constraints(
#         hero_min_df=state.minimum_constraints,
#         hero_max_df=state.maximum_constraints,
#         set_constraints_df=state.set_type_constraints,
#     )
#     opt.set_objective_optimisation(stat_weightings_df=state.stat_weightings)
#     opt.define_solver(timer=solver_time, worker_count=worker_count)
#     state["response_dict"] = opt.run_solver()


def main():

    # alias for session_state since it's too long
    state = st.session_state

    # create flag to determine whether data should be re-initialised - False on first run
    if "data_initialised" not in state:
        state["data_initialised"] = False

    helper.set_app_design_configs()

    ##############################
    ### LOADING AND PROCESSING ###
    ##############################

    # file uploader widget
    gear_file = st.sidebar.file_uploader("Please load in a gear file")

    # stop -> if data has not been loaded
    if not gear_file:
        st.stop()

    # generate derivative data with required outputs being stored in session_state
    helper.generate_derivative_input_data(state, gear_file)

    ########################
    ### SIDEBAR ELEMENTS ###
    ########################

    st.sidebar.header("Options")

    ### Select at least one character before progressing
    selected_hero = st.sidebar.selectbox(
        "Select a hero", state.user_hero_name_list
    )

    hero_state = helper.initialise_selected_hero_state(state, selected_hero)

    #############################
    ### ADDITIONAL STATS FORM ###
    #############################

    with st.sidebar.form(f"additional_stats", clear_on_submit=False):
        imprint_stat = st.selectbox(
            "Select imprint stat",
            STAT_LIST,
            key=f"{hero_state['name']}_i_key",
            index=hero_state["imprint_stat_index"],
        )
        imprint_stat_value = st.number_input(
            "Select stat value",
            key=f"{hero_state['name']}_i_val",
            value=hero_state["imprint_stat_value"],
        )
        ee_stat = st.selectbox(
            "Select exclusive equipment stat",
            STAT_LIST,
            key=f"{hero_state['name']}_ee_key",
            index=hero_state["ee_stat_index"],
        )
        ee_stat_value = st.number_input(
            "Select stat value",
            key=f"{hero_state['name']}_ee_val",
            value=hero_state["ee_stat_value"],
        )
        artifact_attack = st.number_input(
            "Select artifact attack value",
            key=f"{hero_state['name']}_aa_val",
            value=hero_state["artifact_attack"],
        )
        artifact_health = st.number_input(
            "Select artifact health value",
            key=f"{hero_state['name']}_ah_val",
            value=hero_state["artifact_health"],
        )

        with st.expander("Misc Stats"):
            st.write("Coming Soon!")

        stat_submit_button = st.form_submit_button("Apply Additional Stats")

    # on additional stats form submission
    if stat_submit_button:

        # allow subsequent constraint form table to be edited
        refresh_table_setting = True

        helper.submit_additional_stats(
            hero_state,
            imprint_stat_index=STAT_LIST.index(imprint_stat),
            imprint_stat_value=imprint_stat_value,
            ee_stat_index=STAT_LIST.index(ee_stat),
            ee_stat_value=ee_stat_value,
            artifact_attack=artifact_attack,
            artifact_health=artifact_health,
        )

    else:
        refresh_table_setting = False

    #####################
    #### MAIN WINDOW ####
    #####################

    st.header(f"Selected Hero: {hero_state['name']}")
    with st.expander("Guide"):
        st.caption(
            """
                Configure constraints and optimization objectives here for the selected hero. Enter values on the cells for the 
                Minimum, Maximum, and Stat_Weighting column. Minimum and maximum represent hard constraints which if not met will result in 
                an unsuccessful optimization attempt, so it's best not too be too strict with these. 
                
                The stat_weighting column allows for each stat to be prioritised to different degrees. The default values are 
                all set to 1 (each stat value has equal weighting), 
                though for the majority of cases you'll want to weigh them with respect to the selected hero.
                Stat weights are already hard code normalized loosely based on a general gear score (e.g. 1 speed = 2% Attack), 
                so if you do adjust the values you don't have to mentally account for this.

                Unless you really want to prioritise a given stat, it's probably best to just leave needed stats at 1 and set everything
                else to 0. Please try to keep everything as integer values as the optimizer rounds all values anyway.

                The set type constraint is another hard constraint and so again, fails if it can't be met. In the majority of cases, 
                unless you want to have a set that offers a benefit other than a stat boost (e.g. life steal and speed respectively), 
                it's best to just leave it blank and let the optimizer find the best combination of pieces to meet the requirements.
                
                The hero weighting is used in conjunction with the stat_weights to determine the overall optimization priority. 
                If a hero's weighting is set to 0, besides meeting the hard constraints, the optimizer won't try to maximise stats 
                in any other way. This allows you to both weigh stats against one another per hero, and then weigh heroes against one another 
                on a separate basis. 
                
                You'll see the net weights given in the 'Weightings' table once you add the hero to the optimizer. You can interpret these 
                values directly (e.g. a hero/stat combination with a weight of 50 is valued 10x greater than another with a weight of 5).
                
                Overall the optimizer just attempts to maximise the total score, e.g.
                ```
                obj = hero1_weight*(hero1_Attack*hero1_AttackWeight*Attack_norm + hero1_Defense*hero1_DefenseWeight*Defense_norm + ...) + hero2_weight*(hero2_Attack*hero2_AttackWeight*Attack_norm + ...)
                ```
                while adhering to the hard constraints.
                """
        )

    #######################
    ### CONSTRAINT FORM ###
    #######################

    with st.expander("Set Constraints", expanded=True):

        with st.form(
            clear_on_submit=False,
            key=f"{hero_state['name']}_constraints_form",
        ):

            # Create 'editable' dataframe showing:
            # initial equipped stats, minimum constraints, maximum constraints, stat weighting
            constraint_df = (
                hero_state["initial"].dataframe_repr().T[DISPLAY_STAT_LIST]
            )
            constraint_df.index = ["Current_Stats"]
            constraint_df = constraint_df.T.reset_index()

            constraint_df["Minimum"] = hero_state["min_constraints_form"]
            constraint_df["Maximum"] = hero_state["max_constraints_form"]
            constraint_df["Stat_Weighting"] = hero_state["stat_weightings_form"]

            # separate columns for widgets
            col_1, col_2 = st.columns([2, 2])

            with col_1:

                constraints_response = AgGrid(
                    constraint_df,
                    editable=True,
                    theme=APP_THEME,
                    fit_columns_on_grid_load=True,
                    reload_data=refresh_table_setting,
                    key=f"{hero_state['name']}_constraint",
                    height=GRID_SIZE * (1 + constraint_df.shape[0]),
                )

            # sets the table refresh back to false
            refresh_table_setting = False

            with col_2:

                current_active_sets = {
                    k.name: v
                    for k, v in hero_state["initial"].active_sets.items()
                    if v > 0
                }

                st.write("Current Active Sets")
                st.write(current_active_sets)

                set_type_selection = st.multiselect(
                    label="Select set type constraints",
                    options=SET_TYPES,
                    key=f"{hero_state['name']}_set_constraint",
                    default=hero_state["set_selection_form"],
                )

                hero_weight = st.slider(
                    "Select hero weighting",
                    min_value=0,
                    max_value=10,
                    value=hero_state["hero_weighting_form"],
                    step=1,
                )

            constraint_submit_cols = st.columns(4)
            constraint_submit = constraint_submit_cols[0].form_submit_button(
                "Add Hero to Optimizer"
            )
            delete_hero = constraint_submit_cols[1].form_submit_button(
                "Remove Hero from Optimizer"
            )

    # delete hero from optimizer
    if delete_hero:

        # check if tables exist already
        if "minimum_constraints" in state:
            # remove hero from all state tables
            if helper.drop_current_hero(
                state=state, current_hero=hero_state["name"]
            ):
                st.error(f"{hero_state['name']} does not exist in optimizer")
            else:
                st.info(f"{hero_state['name']} removed from optimizer!")
        else:
            st.error("No tables exist")

    # submit form
    if constraint_submit:

        helper.submit_constraints(
            hero_state, constraints_response, set_type_selection, hero_weight
        )

        helper.create_or_update_optimization_inputs(
            state, hero_state, constraints_response
        )

    # don't progress if the subsequent tables don't exist or are empty
    if "minimum_constraints" not in state:
        st.stop()

    if state.minimum_constraints.empty:
        st.stop()

    ######################################
    ### HERO OPTIMIZATION SETTINGS VIZ ###
    ######################################

    # Visualisation of collection dfs
    with st.expander("Constraint Lists", expanded=True):

        st.markdown("#### Minimum Constraint Collection")
        AgGrid(
            state.minimum_constraints[DISPLAY_STAT_LIST].reset_index(),
            fit_columns_on_grid_load=True,
            reload_data=True,
            height=GRID_SIZE * (1 + state.minimum_constraints.shape[0]),
            theme=APP_THEME,
            key="min_collection",
        )
        st.markdown("#### Maximum Constraint Collection")
        AgGrid(
            state.maximum_constraints[DISPLAY_STAT_LIST].reset_index(),
            fit_columns_on_grid_load=True,
            reload_data=True,
            height=GRID_SIZE * (1 + state.maximum_constraints.shape[0]),
            theme=APP_THEME,
            key="max_collection",
        )
        st.markdown("#### Weightings")
        AgGrid(
            state.stat_weightings[DISPLAY_STAT_LIST].reset_index(),
            fit_columns_on_grid_load=True,
            reload_data=True,
            height=GRID_SIZE * (1 + state.stat_weightings.shape[0]),
            theme=APP_THEME,
            key="weight_collection",
        )
        st.markdown("#### Set Type Constraint Collection")
        AgGrid(
            state.set_type_constraints.reset_index(),
            fit_columns_on_grid_load=True,
            reload_data=True,
            height=GRID_SIZE * (1 + state.set_type_constraints.shape[0]),
            theme=APP_THEME,
            key="set_collection",
        )

    ####################################
    ### OPTIMIZATION SOLVER SETTINGS ###
    ####################################

    with st.form("Optimization"):

        col_1_opt, col_2_opt = st.columns([1, 1])

        solver_time = col_1_opt.number_input(
            "Select maximum solver waiting time (seconds)",
            min_value=1,
            max_value=1000,
            value=60,
        )
        worker_count = col_2_opt.slider(
            "Select number of workers",
            min_value=1,
            max_value=10,
            value=8,
            step=1,
        )

        optimizer_button = st.form_submit_button("Optimize")

    if optimizer_button:
        with st.spinner("Optimizing..."):

            helper.run_optimizer(state, solver_time, worker_count)
            st.info(state.response_dict["message"])

    # don't progress if optimization is unsuccessful or hasn't been run
    if "response_dict" not in state:
        st.stop()

    ############################
    ### OPTIMIZATION RESULTS ###
    ############################

    if state.response_dict["status"] not in ["OPTIMAL", "FEASIBLE"]:
        st.stop()

    # equip gear to optimization heroes
    state.optimized_selected_hero_list = list(
        state.response_dict["stats_table"].index
    )
    state.optimized_selected_hero_objects = [
        state["hero_info"][hero]["optimized"]
        for hero in state.optimized_selected_hero_list
    ]

    # get equip lists
    optimized_equip_lists = dh.get_equip_lists_from_equip_dict(
        selected_hero_list=state.optimized_selected_hero_list,
        equip_dict=state.response_dict["equip_dict"],
    )

    helper.equip_items_to_heroes(
        state.optimized_selected_hero_list,
        state.optimized_selected_hero_objects,
        state.optimized_item_objects,
        optimized_equip_lists,
    )

    # create joined dataframes of stats for heroes both before and after optimization
    initial_output_df = pd.concat(
        [
            state["hero_info"][hero]["initial"].dataframe_repr().T.reset_index()
            for hero in state.optimized_selected_hero_list
        ]
    )
    optimized_output_df = pd.concat(
        [
            state["hero_info"][hero]["optimized"]
            .dataframe_repr()
            .T.reset_index()
            for hero in state.optimized_selected_hero_list
        ]
    )
    equipment_df_dict = {
        hero: pd.DataFrame(
            state["hero_info"][hero]["optimized"].get_equipment_list()
        )
        for hero in state.optimized_selected_hero_list
    }

    ################################
    ### OPTIMIZATION RESULTS VIZ ###
    ################################

    st.subheader("Initial Stats")
    AgGrid(
        initial_output_df[["index"] + DISPLAY_STAT_LIST + ["Active_Sets"]],
        fit_columns_on_grid_load=True,
        height=GRID_SIZE * (1 + initial_output_df.shape[0]),
        theme=APP_THEME,
    )

    st.subheader("Optimized Stats")
    AgGrid(
        optimized_output_df[["index"] + DISPLAY_STAT_LIST + ["Active_Sets"]],
        fit_columns_on_grid_load=True,
        height=GRID_SIZE * (1 + optimized_output_df.shape[0]),
        theme=APP_THEME,
    )

    # show all equipment in a table and include a save button to store output locally
    equipment_csv = helper.get_equipment_csv(equipment_df_dict)
    st.download_button(
        "Download equipment table as csv",
        equipment_csv,
        file_name="optimized_equipment.csv",
        mime="text/csv",
    )

    with st.expander("Equipment Details"):
        for hero, equip_items in equipment_df_dict.items():
            st.subheader(f"{hero} Equipment")
            AgGrid(
                equip_items[["Slot", "Name", "Set"] + DISPLAY_STAT_LIST],
                fit_columns_on_grid_load=True,
                height=GRID_SIZE * (1 + equip_items.shape[0]),
                theme=APP_THEME,
                key=f"{hero}_equipment_table",
            )


if __name__ == "__main__":
    if st._is_running_with_streamlit:
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
