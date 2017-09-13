"""
Use Q-learning to maximize a function, which is feed-forward neural network
"""

import numpy
import tensorflow as tf
from QLearning import QLearning
import time
import argparse
from multiprocessing import Process, Array, Value
from multiprocessing.managers import BaseManager
from env_time import Environment

# Raw parameters
k = 20   # total available card size
d = 6    # deck size
use_prioritized_replay = True
gamma = 0.9
n_hidden_ql = 200                 # number of hidden units in Qlearning NN
BATCH_SIZE = 64
MEMORY_CAPACITY = 64000
MEMORY_CAPACITY_START_LEARNING = 64000
EPISODE_SIZE = 10000001          # the size of training episodes
TEST_PERIOD = 10                 # how many per training episodes to do testing
RANDOM_SEED = 2214               # seed for random behavior except coefficient generation
load = False                     # whether to load existing model

# Read parameters
# parser = argparse.ArgumentParser(description='Process some integers.')
# parser.add_argument('--timed', dest='timed', action='store_true')
# parser.set_defaults(timed=timed)
# args = parser.parse_args()
# timed = args.timed

# Derived parameters
n_actions = d * (k-d) + 1    # number of one-card modification
TRIAL_SIZE = d                # how many card modification allowed
n_input_ql = k+1   # input dimension to qlearning network (k plus time step as a feature)
tensorboard_path = "comb_search_k{0}_d{1}/{2}".format(k, d, time.time())
numpy.random.seed(RANDOM_SEED)


# initialize critical components
BaseManager.register('Environment', Environment)
BaseManager.register('QLearning', QLearning)
manager = BaseManager()
manager.start()
env = manager.Environment(k=k, d=d)
RL = manager.QLearning(
    n_features=n_input_ql, n_actions=n_actions, n_hidden=n_hidden_ql, memory_capacity=MEMORY_CAPACITY, load=load,
    prioritized=use_prioritized_replay, batch_size=BATCH_SIZE, save_and_load_path='optimizer_model/qlearning',
    reward_decay=gamma, n_total_episode=EPISODE_SIZE, n_mem_size_learn_start=MEMORY_CAPACITY_START_LEARNING,
    tensorboard_path=tensorboard_path
)
i_episode = Value('i', 0)


def collect_samples(RL, env, i_episode):
    while i_episode.value < EPISODE_SIZE:
        cur_state = env.reset()
        for i_epsisode_step in range(TRIAL_SIZE):
            next_possible_states, next_possible_actions = env.all_possible_next_state_action(cur_state)
            action, _ = RL.choose_action(cur_state, next_possible_states, next_possible_actions, epsilon_greedy=True)
            cur_state_, reward = env.step(action)
            terminal = True if i_epsisode_step == TRIAL_SIZE - 1 else False
            RL.store_transition(cur_state, action, reward, cur_state_, terminal)
            cur_state = cur_state_
        print('episode ', i_episode.value, ' finished with value', env.output(cur_state),
              'cur_epsilon', RL.cur_epsilon(), ' cur mem size', RL.memory_size())
        i_episode.value = i_episode.value + 1  # += not atomic but is ok because only this process modify it

        if RL.memory_size() > MEMORY_CAPACITY_START_LEARNING and i_episode.value % TEST_PERIOD == 0:
            cur_state = env.reset()
            for i_episode_test_step in range(TRIAL_SIZE):
                next_possible_states, next_possible_actions = env.all_possible_next_state_action(cur_state)
                action, q_val = RL.choose_action(cur_state, next_possible_states, next_possible_actions,
                                                 epsilon_greedy=False)
                cur_state, reward = env.step(action)
                test_output = env.output(cur_state)
                print('TEST step {0}, output: {1}, at {2}, qval: {3}, reward {4}'.
                      format(i_episode_test_step, test_output, cur_state, q_val, reward))

            RL.tb_write(tags=['Prioritized={0}, gamma={1}, seed={2}/Test Ending Output'.
                            format(use_prioritized_replay, gamma, RANDOM_SEED),
                                  'Prioritized={0}, gamma={1}, seed={2}/Test Ending Qvalue'.
                            format(use_prioritized_replay, gamma, RANDOM_SEED),
                                  ],
                            values=[test_output,
                                    q_val],
                            step=i_episode.value)


def learn(RL, i_episode):
    if RL.memory.size > MEMORY_CAPACITY_START_LEARNING:
        RL.learn()
        print('learn at episode', i_episode.value)

p1 = Process(target=collect_samples, args=[RL, env, i_episode])
p1.start()
p1.join()



