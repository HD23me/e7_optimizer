# e7_optimizer

This is a rough demo/WIP of a constraint programming based approach for optimising gear in the game Epic 7. 

### Prerequisites
This tool requires a gear file from the [**Fribbels Epic 7 Gear Optimizer**](https://github.com/fribbels/Fribbels-Epic-7-Optimizer), notably using the [**auto importer**](https://github.com/fribbels/Fribbels-Epic-7-Optimizer#setting-up-the-auto-importer). You can still play around with it using the provided `sample_gear.txt` file however.

### Quick Start Guide
1. Install Python (only tested on version 3.9.7).
2. (Optional) Create a virtual environment.
3. Clone the repo with `git clone https://github.com/HD23me/e7_optimizer.git`.
4. Install the requirements with `pip install -r requirements.txt`.
5. Start the streamlit app using from the project root with `streamlit run ./e7_optimizer/app.py`.
6. Your browser should open up, or if not just click on the address shown in your terminal.

### Usage
1. Load in your `gear.txt` file.
2. Select the hero you wish to add to the optimizer using the sidebar dropdown menu.
3. In the main window you should see a two expandable sections, a guide which goes into some detail about the optimizer options, and a constraint window.
4. In the second column of the table you can see the current stats of your selected hero including their gear. The stats will be slightly off as additional sources such as the artifact, imprint, and exclusive equipment haven't been added. To include these fill out the sidebar form and click submit. The stats in the constraint table should update accordingly.
5. After setting the desired constraints/weights (follow the expander guide), select the `Add Hero to Optimizer` button to add your first hero.
6. More tables should be generated showing the constraints you've set, as you add more heroes, they will also be shown here.
7. When you're satisfied with your set up click the Optimize button and wait for the solver to finish.
8. If you want you can play around with the displayed solver settings to add more time or workers to the solver.
9. If the solver is successful you should see more tables pop up showing a comparison between the loaded stats and optimized stats.
10. You can also view the gear used and click the `Download equipment table as csv` button to prepare yourself for the tedious process of regearing all your heroes.


### Things to be aware of
- There's no handling for changing the item file mid-session, if you do just clear the cache/restart the session.
- No handling for additional stats from speciality changes or character specific bonuses.
- While I haven't stress tested it much it usually finds some sort of solution in under a minute or decides that there is no solution. In cases where a solution can be reached but it's not the optimal one, you can try adding more time to the solver.
- There are probably quite a few bugs, submit an issue if you find any though I can't promise they'll be fixed.

### Yet to be implemented
- Handling for additional stats.
- Setting current gear as minimum constraints.
- Locking gear for repeated runs with different Hero groups.
- ???
