from collections import deque
from prioritized_exp import RL_brain
import numpy


class Memory(object):

    def __init__(self, capacity, prioritized, planning, n_features, n_actions, batch_size,
                 qsa_feature_extract, qsa_feature_extract_for_all_acts):
        self.size = 0            # current memory size: 0 ~ capacity
        self.virtual_size = 0    # the size of memory if there is no cap
        self.capacity = capacity
        self.prioritized = prioritized
        self.planning = planning
        self.n_actions = n_actions
        self.n_features = n_features
        self.batch_size = batch_size
        self.qsa_feature_extract = qsa_feature_extract   # feature vector for Q(s,a)
        self.qsa_feature_extract_for_all_acts = qsa_feature_extract_for_all_acts  # feature vectors for Q(s', a') for all a'

        if self.prioritized:
            self.memory = RL_brain.Memory(self.capacity)
        else:
            self.memory = deque(maxlen=self.capacity)

    def store(self, transition):
        if self.prioritized:
            # if transition[2] > 4407:
            #     print('save 4408')
            self.memory.store(transition)
        else:
            # if transition[2] > 4407:
            #     print('save 4408')
            self.memory.append(transition)
        self.size += 1
        self.virtual_size += 1
        if self.size > self.capacity:
            self.size = self.capacity

    def sample(self):
        if self.prioritized and not self.planning:
            return self._prioritized_sample()
        elif not self.prioritized and not self.planning:
            return self._no_prioritized_sample()
        elif self.prioritized and self.planning:
            return self._prioritized_planning_sample()
        elif not self.prioritized and self.planning:
            pass  # not implemented yet

    def _prioritized_planning_sample(self):
        pass

    def _prioritized_sample(self):
        tree_idx, samples, is_weights = self.memory.sample(self.batch_size)

        qsa_feature = numpy.zeros((self.batch_size, self.n_features))  # feature for Q(s,a)
        qsa_features = None                  # features for Q('s,'a) for all 'a which leads to s'
        qsa_next_features = numpy.zeros((self.batch_size, self.n_actions,
                                        self.n_features))      # features for Q(s',a') for all a'
        rewards = numpy.zeros(self.batch_size)
        terminal_weights = numpy.ones(self.batch_size)
        is_weights = numpy.squeeze(is_weights)   # morvan's memory return 2d is_weights array

        for i, (state, action, reward, next_state, terminal) in enumerate(samples):
            rewards[i] = reward
            # if reward > 4407:
            #     print('sample 4408')
            terminal_weights[i] = 0 if terminal else 1
            qsa_feature[i] = self.qsa_feature_extract(state, action)
            qsa_next_features[i] = self.qsa_feature_extract_for_all_acts(next_state)
            # we do not directly save feature vectors in memory because that may take too much memory

        return qsa_feature, qsa_features, qsa_next_features, rewards, terminal_weights, is_weights, tree_idx

    def _no_prioritized_sample(self):
        assert self.batch_size <= len(self.memory)
        sample_mem_idxs = numpy.random.choice(len(self.memory), self.batch_size, replace=False)

        qsa_feature = numpy.zeros((self.batch_size, self.n_features)) # feature for Q(s,a)
        qsa_features = None                  # features for Q('s,'a) for all 'a which leads to s'
        qsa_next_features = numpy.zeros((self.batch_size, self.n_actions,
                                         self.n_features))     # features for Q(s',a') for all a'
        rewards = numpy.zeros(self.batch_size)
        terminal_weights = numpy.ones(self.batch_size)
        # every sample is equally important in non-prioritized sampling
        is_weights = numpy.ones(self.batch_size)

        for i, mem_idx in enumerate(sample_mem_idxs):
            state, action, reward, next_state, terminal = self.memory[mem_idx]
            # if reward > 4407:
            #     print('sample 4408')
            rewards[i] = reward
            terminal_weights[i] = 0 if terminal else 1
            qsa_feature[i] = self.qsa_feature_extract(state, action)
            qsa_next_features[i] = self.qsa_feature_extract_for_all_acts(next_state)

        return qsa_feature, qsa_features, qsa_next_features, rewards, terminal_weights, is_weights, sample_mem_idxs

    def update_priority(self, e_ids, abs_errors):
        assert self.prioritized
        self.memory.batch_update(e_ids, abs_errors)
