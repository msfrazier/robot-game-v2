@staticmethod
def _make_player(file_name):
    import json
    from importlib.util import spec_from_file_location, module_from_spec
    """
    Changed this to load the robot in the usual way allowing debugging in Pycharm.

    :param file_name: local file containing the robot
    :return: the player.
    """
    try:
        assert os.path.isdir(file_name)
        # RMP: if it's a model directory
        model_dir = file_name
        params_file = os.path.join(model_dir, 'params.json')
        assert os.path.isfile(params_file), f'Failed to find {params_file}'

        with open(params_file) as fp:
            model_params = json.load(fp)

        robot_file = os.path.join(model_dir, 'robot_game.py')
        assert os.path.isfile(robot_file), f'Failed to find {robot_file}'

        spec = spec_from_file_location('robot_game', robot_file, submodule_search_locations=[model_dir])
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        robot = getattr(module, 'Robot')(model_dir=file_name, **model_params)
        return game.Player(robot=robot)
    except AssertionError:
        try:
            return game.Player(file_name=file_name)
        except IOError as msg:
            if pkg_resources.resource_exists('rgkit', file_name):
                bot_filename = pkg_resources.resource_filename('rgkit', file_name)
                return game.Player(file_name=bot_filename)
            raise IOError(msg)