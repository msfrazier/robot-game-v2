
from rgkit import run as rg_run

num_games = 7
opponent_1 = "Andrew_1"
opponent_2 = "Erica_2"

while num_games > 0:
    rg_run(opponent_1,opponent_2)
    num_games -= 1