import pandas as pd
from optimizer.data_structures import (
    SET_TYPE_STATS,
    STAT_LIST,
    ItemTypes,
    SET_TYPE_STATS,
)
from ortools.sat.python import cp_model
import numpy as np

# may/may not need this
# sys.setrecursionlimit(10000)


class Optimizer:
    def __init__(
        self,
        item_df: pd.DataFrame,
        hero_base_df: pd.DataFrame,
        hero_additional_df: pd.DataFrame,
    ):
        self.item_df = self._convert_to_int(item_df)
        self.hero_base_df = self._convert_to_int(hero_base_df)
        self.hero_additional_df = self._convert_to_int(hero_additional_df)

        # init generated attributes
        self.hero_df_equip = self.hero_additional_df.copy()
        self.item_iterator = range(self.item_df.shape[0])
        self.hero_iterator = range(self.hero_base_df.shape[0])

        # placeholder attributes
        self.model = None
        self.solver = None
        self.equip_vars = None
        self.optimized_equip_dict = None

        ### Run initilisation methods
        self._create_model()
        self._define_objective_function()

    def _convert_to_int(self, df):
        """converts all numerical columns in a df to integers"""

        numeric_cols = df.select_dtypes(np.number).columns
        df[numeric_cols] = df[numeric_cols].applymap(round)

        return df

    def _create_model(self):

        # create model
        self.model = cp_model.CpModel()

        self.equip_vars = {
            (hero, item): self.model.NewIntVar(0, 1, f"{hero}_{item}")
            for item in self.item_iterator
            for hero in self.hero_iterator
        }

    def _define_objective_function(self):

        # mapping between stat modifiers and the stat they modify
        multiplier_map = {
            "DefensePercent": "Defense",
            "HealthPercent": "Health",
            "SpeedPercent": "Speed",
            "AttackPercent": "Attack",
        }

        #######################
        ### SET BONUS STATS ###
        #######################

        for hero in self.hero_iterator:
            for current_set_type, vals in SET_TYPE_STATS.items():

                # only run if the specific set_type gives a stat bonus (e.g. SetTypes.SPEED)
                if "stat" in vals:

                    # variable in model that stores the count of current set
                    set_count = self.model.NewIntVar(
                        0, len(self.item_iterator), f"{hero}_{current_set_type}"
                    )

                    # get the count of the current set type equipped
                    tmp_lin = sum(
                        [
                            self.equip_vars[(hero, item)] * 1
                            if self.item_df["set_type"].iloc[item]
                            == current_set_type
                            else 0
                            for item in self.item_iterator
                        ]
                    )

                    # assign the current set count to variable
                    self.model.Add(set_count == tmp_lin)

                    # determine how many sets are active (handled multiple counts for crit, hit, etc)
                    active_set_counts = self.model.NewIntVar(
                        0, 3, f"stat_bonus_{hero}"
                    )

                    # dividing the count of each set (as an integer) by the relevant set threshold
                    # 4 piece bonuses won't ever be more than 1, 2 piece can be upto 3
                    # TODO: Maybe add some handling for limited 2 piece (e.g. penetration set)
                    self.model.AddDivisionEquality(
                        active_set_counts, set_count, vals["threshold"]
                    )

                    stat_increase = active_set_counts * vals["stat_bonus"]

                    self.hero_df_equip[vals["stat"]].iloc[hero] += stat_increase

                    # add set bonus stats to regular stat (e.g. for AttackPercent)
                    if vals["stat"] in multiplier_map.keys():
                        adj_stat = multiplier_map[vals["stat"]]

                        # calculate the stat adjustment for a single 'bonus'
                        single_bonus_adj_stat = (
                            vals["stat_bonus"]
                            * int(self.hero_base_df[adj_stat].iloc[hero])
                        ) // 100

                        # calculate total bonus based on active count (opt param)
                        total_bonus = active_set_counts * single_bonus_adj_stat

                        # add total bonus to existing stat
                        self.hero_df_equip[adj_stat].iloc[hero] += total_bonus

        ##################
        ### ITEM STATS ###
        ##################

        # calculate the components in the objective function -> stats if items are equiped
        for hero, item in self.equip_vars.keys():
            for stat in STAT_LIST:

                stat_val = self.item_df[stat].iloc[item]

                # adjustment for stat multipliers -> e.g. AttackPercent should increase the Attack based on hero stats
                if stat in multiplier_map.keys():
                    adj_stat = multiplier_map[stat]

                    mult = (
                        stat_val * int(self.hero_base_df[adj_stat].iloc[hero])
                    ) // 100

                    used_item_mult = self.equip_vars[(hero, item)] * mult

                    # update stat with multiplier value
                    self.hero_df_equip[adj_stat].iloc[hero] += used_item_mult

                # update stat with equipment value (in all cases)
                self.hero_df_equip[stat].iloc[hero] += (
                    stat_val * self.equip_vars[(hero, item)]
                )

    def add_constraints(self, hero_min_df, hero_max_df, set_constraints_df):
        """Add constraints to the model.
        This includes game logic constraints (e.g. items can only be equipped by one hero
        and user defined constraints (e.g. Speed >= 200)
        """

        # ensure all columns are integer
        hero_min_df = self._convert_to_int(hero_min_df)
        hero_max_df = self._convert_to_int(hero_max_df)

        # CONDITION 1. Only one type of item per hero (e.g. 1 ring, 1 boots)
        for hero in self.hero_iterator:
            for item_type in ItemTypes:
                self.model.Add(
                    sum(
                        [
                            self.equip_vars[(hero, item_iter)]
                            for item_iter in self.item_iterator
                            if self.item_df.iloc[item_iter]["item_type"]
                            == item_type
                        ]
                    )
                    <= 1
                )

        # CONDITION 2. An item cannot be equipped by more than one hero
        for item in self.item_iterator:
            self.model.Add(
                sum(
                    [
                        self.equip_vars[(hero_iter, item)]
                        for hero_iter in self.hero_iterator
                    ]
                )
                <= 1
            )

        # CONDITION 3. Net hero stats must be within the user defined ranges (min and max values)
        for hero in self.hero_iterator:
            for stat in STAT_LIST:
                self.model.AddLinearExpressionInDomain(
                    self.hero_df_equip.iloc[hero][stat],
                    cp_model.Domain(
                        int(hero_min_df.iloc[hero][stat]),
                        int(hero_max_df.iloc[hero][stat]),
                    ),
                )

        # CONDITION 4. Heroes must have at least 1 active count per user defined set constraint
        for hero in self.hero_iterator:
            # only add set type constraint if not empty
            if ~pd.isnull(set_constraints_df.iloc[hero])[0]:
                for desired_set_type in set_constraints_df.iloc[hero][0]:

                    self.model.Add(
                        sum(
                            [
                                self.equip_vars[(hero, item_iter)]
                                for item_iter in self.item_iterator
                                if self.item_df.iloc[item_iter]["set_type"]
                                == desired_set_type
                            ]
                        )
                        >= SET_TYPE_STATS[desired_set_type]["threshold"]
                    )

    def set_objective_optimisation(self, stat_weightings_df=None):
        """Sets the objective function to be maximized. Janky arguments to be fixed"""

        if stat_weightings_df is not None:
            self.model.Maximize(
                (
                    self.hero_df_equip[stat_weightings_df.columns]
                    * stat_weightings_df
                )
                .sum()
                .sum()
            )
        else:
            self.model.Maximize(
                self.hero_df_equip[stat_weightings_df.columns].sum().sum()
            )

    def define_solver(self, timer=60, worker_count=8):

        self.solver = cp_model.CpSolver()
        self.solver.parameters.num_search_workers = worker_count
        self.solver.parameters.max_time_in_seconds = timer

        self.solution_printer = cp_model.ObjectiveSolutionPrinter()

    def run_solver(self):

        # run the solver
        status = self.solver.SolveWithSolutionCallback(
            self.model, self.solution_printer
        )

        response_dict = {}

        if status == cp_model.OPTIMAL:

            response_dict["status"] = "OPTIMAL"
            response_dict["message"] = "Optimal solution found"
            response_dict["stats_table"] = self._generate_output_stats_table()
            response_dict["equip_dict"] = self._generate_equip_dict()

        elif status == cp_model.FEASIBLE:

            response_dict["status"] = "FEASIBLE"
            response_dict[
                "message"
            ] = "(potentially) Sub-optimal solution found"
            response_dict["stats_table"] = self._generate_output_stats_table()
            response_dict["equip_dict"] = self._generate_equip_dict()

        elif status == cp_model.INFEASIBLE:

            response_dict["status"] = "INFEASIBLE"
            response_dict[
                "message"
            ] = "Solution is infeasible. Please try relaxing your constraints."
            response_dict["stats_table"] = None
            response_dict["equip_dict"] = None

        else:
            response_dict["status"] = "UNKNOWN"
            response_dict[
                "message"
            ] = """Solution could not be found (likely ran out of time). 
            Please try extending the search time or relaxing constraints."""
            response_dict["stats_table"] = None
            response_dict["equip_dict"] = None

        print("\n" + response_dict["message"] + "\n")

        return response_dict

    def _generate_equip_dict(self):
        """After reaching a solution, generates a dictionary showing optimal hero item mappings"""

        optimized_equip_dict = {}

        for hero_item, var in self.equip_vars.items():
            optimized_equip_dict[
                (hero_item[0], hero_item[1])
            ] = self.solver.Value(var)

        self.optimized_equip_dict = optimized_equip_dict
        return self.optimized_equip_dict

    def _generate_output_stats_table(self):

        best_solution_df = self.hero_df_equip[STAT_LIST].applymap(
            self.solver.Value
        )
        return best_solution_df


if __name__ == "__main__":
    pass
