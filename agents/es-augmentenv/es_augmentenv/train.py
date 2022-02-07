import os.path

import numpy as np
from tqdm import tqdm
import datetime as dt

from es_augmentenv.es import SimpleGA, CMAES
from es_augmentenv.model import make_model, simulate, record_video
from es_augmentenv import config

from gym.wrappers import Monitor


def train_es_augment(make_env, seed, name, pop_size=16, max_len=3000, num_episodes=1, sigma_init=0.3,
                     sigma_decay=.99, optimizer="cmaes", predictor=None, feedback_interval=20,
                     show_video=False, store_params=False):
    game_name = "augment_hopper"
    game = config.games[game_name]

    model = make_model(game, make_env_inner=make_env)
    model.make_env()
    seeder = Seeder(seed)
    num_params = model.param_count
    es = None
    if optimizer == "cmaes":
        es = CMAES(num_params,
                sigma_init=sigma_init,
                popsize=pop_size)
    elif optimizer == "ga":
        es = SimpleGA(num_params,
                  sigma_init=sigma_init,
                  sigma_decay=sigma_decay,
                  sigma_limit=0.02,
                  elite_ratio=0.1,
                  weight_decay=0.005,
                  popsize=pop_size)
    else:
        print(f"{optimizer} not a valid optimizer")

    gen = 0
    episodes = 0
    # initialize logging data
    # start_time = int(time.time())
    #
    # history = []
    # eval_log = []
    while True:
        #get population
        solutions = es.ask()

        #evaluate population
        reward_list = []
        t_list = []
        seeds = seeder.next_batch(pop_size)
        for i, solution in enumerate(tqdm(solutions)):
            model.set_model_params(solution)
            model.make_env()
            feedback = episodes % feedback_interval == 0 and feedback_interval != np.inf
            rewards, ts = simulate(model, train_mode=True, render_mode=False, num_episode=num_episodes, seed=seeds[i],
                                   max_len=max_len, predictor=predictor, feedback=feedback)
            episodes += num_episodes
            reward_list.append(np.min(rewards))
            t_list.append(np.mean(ts))
        es.tell(reward_list)

        #update parameters
        es_solution = es.result()
        model_params = es_solution[0]  # best historical solution
        reward = es_solution[1]  # best reward
        curr_reward = es_solution[2]  # best of the current batch
        model.set_model_params(np.array(model_params).round(4))

        #record training data
        gen += 1
        print("Generation: ", gen)
        print("cur best reward: ", curr_reward)
        print("best reward: ", reward)

        if show_video:
            print("recording video")
            record_video(model, os.path.join(os.path.dirname(__file__), f"saved_videos/gen_{gen}_{name}.mp4"))

        if store_params:
            file_path = os.path.join(os.path.dirname(__file__), f"saved_params/gen_{gen}_{name}.npy")
            with open(file_path, "wb") as f:
                np.save(f, np.array(model_params).round(4))


class Seeder:

    def __init__(self, init_seed=0):
        np.random.seed(init_seed)
        self.limit = np.int32(2**31-1)

    def next_seed(self):
        result = np.random.randint(self.limit)
        return result

    def next_batch(self, batch_size):
        result = np.random.randint(self.limit, size=batch_size).tolist()
        return result






