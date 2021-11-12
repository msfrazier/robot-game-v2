import rgkit.rg as rg

class Robot:
    def act(self, game):
        # if we're in the center, stay put
        if self.location == rg.CENTER_POINT:
            return ['guard']

        # if there are enemies around, attack them
        for key in game.robots:
            bot = game.robots.get(key)
            if bot.get('player_id') != self.player_id:
                if rg.dist(bot.get('location'), self.location) == 1:
                    return ['attack', bot.get('location')]

        # move toward the center
        return ['move', rg.toward(self.location, rg.CENTER_POINT)]