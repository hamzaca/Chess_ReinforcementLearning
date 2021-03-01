from chess.Grid_Pieces import Grid
from chess.Player import Player
import numpy as np


class Game():
    def __init__(self, color_choice):
        """ color_choice  contain three possible outcomes, either black, white or random """
        self.color_choice = color_choice.replace(" ", "")
        # if method is random , choose colors randomdly according to [0.5, 0.5 ] probabilities
        if self.color_choice == "random":
            self.color_player1 = np.random.choice(a=["black", "white"], p=[0.5, 0.5])
            self.color_player2 = self.choose_player2_color(self.color_player1)

        # initialize Grid to the know position
        self.grid = Grid(self.color_player1, self.color_player2)

        self.player1 = Player(grid=self.grid, name="Hamza1", color_player=self.color_player1)
        self.player2 = Player(grid=self.grid, name="Hamza2", color_player=self.color_player2)
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
    def get_grid(self):
        return self.grid

## TODO :