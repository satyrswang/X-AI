from actions import *
from card import *
from collections import deque
import numpy
import copy
import logging
import time
import constant
from player import Player
from typing import Union


logger = logging.getLogger('hearthstone')


class GameWorld:
    def __init__(self, player1, player2, turn):
        self.data = {player1.name: {'intable': player1.intable,
                                    'inhands': player1.inhands,
                                    'health': player1.health,
                                    'mana': player1.this_turn_mana,
                                    'heropower': player1.heropower,
                                    'rem_deck': player1.deck.deck_remain_size},

                     player2.name: {'intable': player2.intable,
                                    'inhands': player2.inhands,
                                    'health': player2.health,
                                    'mana': player2.this_turn_mana,
                                    'heropower': player2.heropower,
                                    'rem_deck': player2.deck.deck_remain_size}}
        self.player1_name = player1.name
        self.player2_name = player2.name
        self.turn = turn
        self.data = copy.deepcopy(self.data)  # make sure game world is a copy of player states
                                              # so altering game world will not really affect player states

    def __repr__(self):
        """ representation of this game world, which looks like a simple game UI """
        str = 'Turn %d\n' % self.turn
        str += '%r. health: %d, mana: %d\n' % \
              (self.player1_name, self[self.player1_name]['health'], self[self.player1_name]['mana'])
        str += 'intable: %r\n' % self[self.player1_name]['intable']
        str += 'inhands: %r\n' % self[self.player1_name]['inhands']
        str += "-----------------------------------------------\n"
        str += '%r. health: %d, mana: %d\n' % \
              (self.player2_name, self[self.player2_name]['health'], self[self.player2_name]['mana'])
        str += 'intable: %r\n' % self[self.player2_name]['intable']
        str += 'inhands: %r\n' % self[self.player2_name]['inhands']
        return str

    def __getitem__(self, player_name):
        return self.data[player_name]

    def copy(self):
        return copy.deepcopy(self)

    def update_player(self, player1, player2):
        """ update player1 and player2 according to this game world
        This represents the real updates, the updates really affect player states """
        player1.intable = self[player1.name]['intable']
        player1.inhands = self[player1.name]['inhands']
        player1.health = self[player1.name]['health']
        player1.this_turn_mana = self[player1.name]['mana']
        player1.heropower = self[player1.name]['heropower']

        player2.intable = self[player2.name]['intable']
        player2.inhands = self[player2.name]['inhands']
        player2.health = self[player2.name]['health']
        player2.this_turn_mana = self[player2.name]['mana']
        player2.heropower = self[player2.name]['heropower']

    def health(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return self[player]['health']

    def mana(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return self[player]['mana']

    def rem_deck(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return self[player]['rem_deck']

    def hp_used(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return self[player]['heropower'].used_this_turn

    def inhands(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return self[player]['inhands']

    def intable(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return self[player]['intable']

    def len_intable(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return len(self.intable(player))

    def len_inhands(self, player: Union[Player, str]):
        if isinstance(player, Player):
            player = player.name
        return len(self.inhands(player))

    def inhands_has_card(self, player, card_name):
        if isinstance(player, Player):
            player = player.name
        for card in self.inhands(player):
            if card.name == card_name:
                return True
        return False


class Match:

    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.player1.opponent = self.player2
        self.player2.opponent = self.player1
        self.recent_player1_win_lose = deque(maxlen=constant.player1_win_rate_num_games)
        self.winner = None
        self.winner_reason = None

    def play_n_match(self, n):
        t1 = time.time()
        for i in range(n):
            self.play_one_match(i)
        # self.player2.print_qtable()
        logger.warning('playing %d matches takes %d seconds.' % (n, time.time() - t1))

    def play_one_match(self, match_idx):
        turn = 0

        while True:
            turn += 1
            player = self.player1 if turn % 2 else self.player2

            match_end = player.turn_begin_init(turn)      # update mana, etc. at the beginning of a turn
            game_world = GameWorld(self.player1, self.player2, turn)
            logger.info("Turn {0}. {1}".format(turn, player))

            # match end due to insufficient deck to draw
            if match_end:
                self.winner = player.opponent
                self.winner_reason = "%r has no card to draw" % player.name
                break

            if turn > 2:
                # update the last end-turn action's Q value
                player.post_action(game_world, match_end=False, winner=False)

            # one action search
            act = player.search_and_pick_action(game_world)
            while not isinstance(act, NullAction):
                act.apply(game_world)
                game_world.update_player(self.player1, self.player2)
                logger.info(game_world)
                match_end = self.check_for_match_end(game_world)
                if match_end:
                    break
                player.post_action(game_world, match_end=False, winner=False)
                act = player.search_and_pick_action(game_world)

            if match_end:
                break

            logger.info("")

        self.post_one_match(game_world, match_idx)

    def post_one_match(self, game_world, match_idx):
        if self.winner == self.player1:
            self.match_end(game_world=game_world, winner=self.player1, loser=self.player2,
                           match_idx=match_idx, reason=self.winner_reason)
            self.recent_player1_win_lose.append(1)
        else:
            self.match_end(game_world=game_world, winner=self.player2, loser=self.player1,
                           match_idx=match_idx, reason=self.winner_reason)
            self.recent_player1_win_lose.append(0)
        self.player1.post_match()
        self.player2.post_match()
        logger.warning("last {0} player 1 win rate: {1}"
                       .format(len(self.recent_player1_win_lose),
                               numpy.mean(self.recent_player1_win_lose)))
        logger.warning("-------------------------------------------------------------------------------")
        self.winner = None
        self.winner_reason = None
        self.player1.reset()
        self.player2.reset()

    def match_end(self, game_world, winner, loser, match_idx, reason):
        logger.warning("%dth match ends at turn %d. winner=%r, loser=%r, reason=%r" %
                       (match_idx, game_world.turn, winner.name, loser.name, reason))
        winner.post_action(game_world, match_end=True, winner=True)
        loser.post_action(game_world, match_end=True, winner=False)
        self.winner = winner

    def check_for_match_end(self, game_world: 'GameWorld') -> bool:
        """ return True if the match ends. Otherwise return False """
        if game_world[self.player1.name]['health'] <= 0:
            self.winner = self.player2
            self.winner_reason = "player1 health<=0"
            return True
        elif game_world[self.player2.name]['health'] <= 0:
            self.winner = self.player1
            self.winner_reason = "player2 health<=0"
            return True
        else:
            return False

