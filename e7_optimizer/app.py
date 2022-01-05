import copy
import sys

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid
from streamlit import cli as stcli

import app_helper as helper
from app_helper import APP_THEME, GRID_SIZE
from optimizer import data_handlers as dh
from optimizer.data_structures import DISPLAY_STAT_LIST, SET_TYPES, STAT_LIST


### Don't ask ###
class DictX(dict):
    """Dictionary wrapper with get/set/del methods for dict.key access"""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as k:
            raise AttributeError(k)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)

    def __repr__(self):
        return "<DictX " + dict.__repr__(self) + ">"


def main():

    # create dictionary to store everything
    if "state" not in st.session_state:
        st.session_state["state"] = DictX({})

    # alias for session_state since it's too long
    state = st.session_state["state"]

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

            cols = ["Slot", "Name", "Set"] + [
                i for i in STAT_LIST if i != "SpeedPercent"
            ]

            AgGrid(
                equip_items[cols],
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
