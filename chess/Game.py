from chess.Grid_Pieces import Grid
from chess import Player
import numpy as np

class Game():
    def __init__(self, color_choice):
        """ color_choice  contain three possible outcomes, either black, white or random """
        self.color_choice = color_choice
        # if method is random , choose colors randomdly according to [0.5, 0.5 ] probabilities
        if self.color_choice == "random":
            self.color_player1 = np.random.choice(a=["black", "white"], p = [0.5, 0.5])
            self.color_player2 = self.choose_player2_color(self.color_player1)

        # initialize Grid to the know position
        self.player1 = Player()
        self.player2 = Player()
        self.grid = Grid(self.player1, self.player2)
        # white starts.
        self.black_to_play = False
        # store the log of the game step by step.
        self.history = []


    @staticmethod
    def choose_player2_color(player1_color):
        if player1_color == "white":
            return "black"
        else:
            return "white"

    def check_mate(self):
        """ return True or False"""
        # when the king is underattack and nowhere  to go
        pass
    def draw(self):
        """ return True or False. """
        # when the king is no where to go but  not underattack. and the king is the only piece.
        pass

## TODO :