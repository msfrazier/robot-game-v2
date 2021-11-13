import random
from rgkit import rg


class Robot:


    def enemy_at_loc(game, robot, loc):
        if loc in game.robots:
            if game.robots[loc].player_id != robot.player_id:
                return True
        return False

    def act(self, game):
        locs_around = rg.locs_around(self.location, filter_out=('obstacle', 'invalid'))

        actions = [[a, loc] for a in ['move'] for loc in locs_around] + [['guard']]

        for loc in locs_around:
            if Robot.enemy_at_loc(game,self,loc)==True:
                return ['attack', loc]

        return random.choice(actions)