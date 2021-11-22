import datetime
import json
import os
import shutil
import sys
import time
import numpy as np
import rgkit.rg as rg
import assemble_results
from rgkit import game as rg_game
from tensorflow.keras.layers import Dense, Input, BatchNormalization, Conv1D, Flatten
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam, Adamax
from tensorflow.keras.regularizers import l2
from drl_robot_helpers import DRLRobot, get_player, get_logger
from sklearn.model_selection import ParameterGrid
from tensorflow import config
from tensorflow_core.python.keras.backend import clear_session


class Robot(DRLRobot):
    def __init__(self, model_dir='.', exploit=True, mini_batch_size=1000, memory_size=10000, epsilon_decay=0.99,
                 **model_params):
        super().__init__(model_dir=model_dir, exploit=exploit, mini_batch_size=mini_batch_size,
                         epsilon_decay=epsilon_decay, memory_size=memory_size, **model_params)

    @staticmethod
    def _build_model(state_size=(1,), action_size=10, learning_rate=0.001, layers=(32, 32), activation='relu',
                     reg_const=0, momentum=0.99, output_activation='linear'):
        """
        Build a keras model that takes the game state as input and produces the expected future reward corresponding
        to each possible action.

        :return: a keras model
        """
        clear_session()

        model = Sequential()
        model.add(Input(shape=state_size))
        # for units in conv_layers:
        #     model.add(Conv1D(filters=units,kernel_size=3))
        # Flatten()
        for units in layers:
            model.add(Dense(units, activation=activation, kernel_regularizer=l2(reg_const)))
            # model.add(BatchNormalization(momentum=momentum))
        # model.add(BatchNormalization(momentum=momentum))
        model.add(Dense(action_size, activation=output_activation, kernel_regularizer=l2(reg_const)))
        model.compile(loss='mse', optimizer=Adam(learning_rate=learning_rate))
        return model

    @staticmethod
    def get_action(action_index, game, robot):
        """
        This function converts an action index into a RobotGame action, one of:
        ['guard'], ['suicide'], ['move', loc], ['attack', loc] where loc is
        north, east, south, or west of robot.location.

        :param action_index: index of action
        :param game: The game information
        :param robot: the robot taking the action
        :return: the RobotGame action
        """
        if action_index == 8:
            # if action_index == 5:
            return ['guard']
        # elif action_index == 9:
        #     # elif action_index == 6:
        #     return ['suicide']
        elif action_index == 9:
            return ['move', rg.toward(robot.location, rg.CENTER_POINT)]
        else:
            locations = rg.locs_around(robot.location)
            if action_index < 4:
                return ['move', locations[action_index]]
            else:
                # if action_index < 4:
                return ['attack', locations[action_index - 4]]

    @staticmethod
    def enemy_at_loc(game, robot, loc):
        if loc in game.robots:
            if game.robots[loc].player_id != robot.player_id:
                return True
        return False

    @staticmethod
    def ally_at_loc(game, robot, loc):
        if loc in game.robots:
            if game.robots[loc].player_id == robot.player_id:
                return True
        return False

    @staticmethod
    def get_state(game, robot):
        """
        Return a numpy 'nd-array' representing this robot's state within the game.

        :param game: The game information
        :param robot: The robot to compute the state for.
        :return: The robot's state as a numpy array
        """

        # offsets = ((-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2),
        #            (-2, 1), (-1, 1), (0, 1), (1, -1), (2, 1),
        #            (-2, 0), (-1, 0), (1, -1), (2, 0),
        #            (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1),
        #            (-2, -2), (-1, -2), (0, -2), (1, -1), (2, -2))
        #
        x, y = robot.location
        # locs_around = [(x + dx, y + dy) for dx, dy in offsets]
        # locs_around = [a_loc for a_loc in locs_around]

        # state = [on spawn?, spawn turn?, enemy_down?, enemy_right?, enemy_up?, enemy_left?]
        # state = [
        #             'spawn' in rg.loc_types(robot.location),
        #             game.turn % 10 == 0,
        #         ] + [
        #             #game.robots[loc].hp if Robot.enemy_at_loc(game, robot, loc) else 0 for loc in locs_around
        #             1 if Robot.enemy_at_loc(game, robot, loc) else 0 for loc in locs_around
        #         ] + [
        #             1 if Robot.ally_at_loc(game, robot, loc) else 0 for loc in locs_around
        #         ] + [
        #         robot.hp / 50]

        second_loc = [(x, y + 1), (x + 1, y), (x, y - 1), (x - 1, y)]
        state = [
                    'spawn' in rg.loc_types(robot.location),
                    game.turn % 10 == 0,
                ] + [
                    1 if robot.location == rg.CENTER_POINT else 0,
                ] + [
                    'invalid' in rg.loc_types(loc) for loc in rg.locs_around(robot.location)
                ] + [
                    Robot.ally_at_loc(game, robot, loc) for loc in rg.locs_around(robot.location)
                ] + [
                    Robot.enemy_at_loc(game, robot, loc) for loc in rg.locs_around(robot.location)
                ] + [
                    Robot.enemy_at_loc(game, robot, sec_loc) for sec_loc in second_loc
                ]

        return np.array(state, dtype=np.float32)

        # return np.array(state, dtype=np.float32)

    @staticmethod
    def get_reward(game, robot):
        """
        You can use the robot fields in 'self' and the game information to determine what reward to give the robot.

        :param game: the game information
        :param robot: the robot
        :return: a number indicating reward (higher is better)
        """
        reward = 0.0
        if robot.hp <= 0:
            # death
            # reward -= 1.0
            return -1.0
        elif game.turn == 99:
            # survive
            # reward += 1.0
            return 1.0

        if 'spawn' in rg.loc_types(robot.location):
            return -1.0

        # else:

        if robot.kills > 0:
            # reward += robot.kills
            return 1.0

        # if robot.damage_caused > 0 and robot.damage_taken == 0:
        #     reward += 1.0
        #     # return 1.0
        # elif robot.damage_caused > robot.damage_taken:
        #     reward += (robot.damage_caused - robot.damage_taken) / 10
        #     # return 0.5
        # elif robot.damage_taken > robot.damage_caused and robot.damage_taken < 10:
        #     reward += (robot.damage_taken - robot.damage_caused) / 10
        #     # return -0.5
        # elif robot.damage_taken >= 10:
        #     reward -= 1.0
        # return -1.0
        elif robot.damage_caused > robot.damage_taken:
            # reward += 1.0
            return 1.0
        elif robot.damage_caused < robot.damage_taken:
            # reward -= 1.0
            return -1.0

        if robot.location == rg.CENTER_POINT:
            return 1.0
        # else:
        #     return -rg.dist(robot.location, rg.CENTER_POINT)

        # return reward
        return 0.0




def main():
    gpus = config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            # Currently, memory growth needs to be the same across GPUs
            for gpu in gpus:
                config.experimental.set_memory_growth(gpus[0], True)
        except RuntimeError as e:
            # Memory growth must be set before GPUs have been initialized
            print(e)

    self_play = True
    params = {
        'learning_rate': [0.001],
        # 'conv_layers': [[64,128]],
        'layers': [[256, 128, 64, 32]],
        'activation': ['relu'],
        'momentum': [0.99],
        'mini_batch_size': [5000],  # roughly one game's worth of actions
        'memory_size': [10000],  # roughly 10 games worth of actions
        'reg_const': [0.000],
        'epsilon_decay': [0.99],
        'output_activation': ['tanh'],
        'state_size': [(19,)],
        'action_size': [10],
    }

    # Get params for GridSearch
    params_grid = list(ParameterGrid(params))

    for params_ in params_grid:
        print(params_)

        if len(sys.argv) > 1:
            model_dir = sys.argv[1]
        else:
            model_dir = os.path.join('drl_robot', datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"))

        if len(sys.argv) > 2:
            opponent = sys.argv[2]
        else:
            opponent = 'Simple'
            opponent3 = None, None

        if not os.path.isdir(model_dir):
            print(f'Creating {model_dir}')
            os.makedirs(model_dir, exist_ok=True)
            # write params file
            with open(os.path.join(model_dir, 'params.json'), 'w') as fp:
                json.dump(params_, fp)
            shutil.copyfile(__file__, os.path.join(model_dir, 'robot_game.py'))
        else:
            with open(os.path.join(model_dir, 'params.json')) as fp:
                params_ = json.load(fp)

        logger = get_logger(model_dir)

        logger.info(f'{model_dir} vs. {opponent}, self_play={self_play}')

        # New Robot
        # robot1 = Robot(model_dir=model_dir, exploit=False, **params_)
        # player1 = rg_game.Player(robot=robot1)

        # Use existing robot
        robot1 = Robot(model_dir='drl_robot\\20211122014207', exploit=False, **params_)
        player1 = rg_game.Player(robot=robot1)

        if self_play:
            player2 = rg_game.Player(robot=robot1)
            player3, robot3 = get_player(opponent)
        else:
            player2, robot2 = get_player(opponent)
            player3, robot3 = None, None

        # check_states = np.array([
        #     [0, 0, 0, 0, 0, 0],
        #     [0, 1, 0, 0, 0, 0],
        #     [1, 0, 0, 0, 0, 0],
        #     [1, 1, 0, 0, 0, 0],
        #     [0, 0, 1, 0, 0, 0],
        #     [0, 0, 0, 1, 0, 0],
        #     [0, 0, 0, 0, 1, 0],
        #     [0, 0, 0, 0, 0, 1],
        # ], dtype=np.float32)

        # check_states = np.array([
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.],
        #
        # ], dtype=np.float32)

        check_states = np.array(
            [
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ]
        )

        logger.info('\n' + str(robot1.model(check_states).numpy().round(2)))

        average_score = 0
        num_episodes = 1000  # number of games to train
        t = time.time()
        avg_score = []
        best_test_score = -np.inf
        for e in range(1, num_episodes + 1):
            t0 = time.time()

            # create new game
            game = rg_game.Game([player1, player2], record_actions=False, record_history=False, print_info=False)

            # run all turns in the game
            game.run_all_turns()

            # get final score
            scores = game.get_scores()
            score = scores[0] - scores[1]
            t_play = time.time()

            # train the robot
            robot1.train()
            t_train = time.time()

            # keep exponential running average of final score
            if (e == 1):
                average_score = score
            else:
                average_score += 0.01 * (score - average_score)

            # log the results
            logger.info(f'episode: {e}/{num_episodes}, score = {scores[0]:2d} - {scores[1]:2d} = {score:2d}, '
                        f'e: {robot1.epsilon:.3f}, average_score: {average_score:.2f}, '
                        f'average_reward: {robot1.ema_reward:.3f}, '
                        f'play: {t_play - t0:.1f} s., train: {t_train - t_play:.1f} s.')

            # save the model every 50 games.
            if e % 50 == 0:
                robot1.save()
                # log the expected future reward for actions in two states
                logger.info('\n' + str(robot1.model(check_states).numpy().round(2)))
                if self_play:
                    # compare against opponent
                    # set robot to exploit model
                    robot1.exploit = True
                    # play 50 games
                    num_games = 10
                    scores = []
                    t_opp = time.time()
                    for _ in range(num_games):
                        game = rg_game.Game([player1, player3], record_actions=False, record_history=False,
                                            print_info=False)
                        game.run_all_turns()
                        # get final score
                        scores.append(game.get_scores())
                    t_opp = time.time() - t_opp
                    wins = sum([s[0] > s[1] for s in scores])
                    loss = sum([s[0] < s[1] for s in scores])
                    draw = sum([s[0] == s[1] for s in scores])
                    score = sum(s[0] for s in scores) / len(scores)
                    opp_score = sum(s[1] for s in scores) / len(scores)
                    opponent_average_score = score - opp_score
                    logger.info(
                        f'vs. {opponent}: {wins}-{loss}-{draw}, average score = {score} - {opp_score} = {opponent_average_score}, '
                        f'{t_opp:.1f} s.')
                    robot1.exploit = False
                    # Add avg score
                    avg_score.append(opponent_average_score)
                    # Test best score and save best
                    if opponent_average_score > best_test_score and self_play == True:
                        # robot1.save()

                        counter = 0
                        avg_score_dict = {}
                        avg_score_dict['testing_bot'] = opponent
                        avg_score_dict['Play_against_self'] = self_play
                        while counter < len(avg_score):
                            avg_score_dict[f'score_{counter}'] = avg_score[counter]
                            counter += 1
                        avg_score_dict['mean'] = np.mean(avg_score)

                        assemble_results
                        best_test_score = opponent_average_score

        logger.info(f'{(time.time() - t) / num_episodes:.3f} s. per episode')

        if self_play == True:
            counter = 0
            avg_score_dict = {}
            avg_score_dict['testing_bot'] = opponent
            avg_score_dict['Play_against_self'] = self_play
            while counter < len(avg_score):
                avg_score_dict[f'score_{counter}'] = avg_score[counter]
                counter += 1
            avg_score_dict['mean'] = np.mean(avg_score)

            with open(os.path.join(model_dir, 'average_scores.json'), 'w') as fp:
                json.dump(avg_score_dict, fp)


if __name__ == '__main__':
    main()
