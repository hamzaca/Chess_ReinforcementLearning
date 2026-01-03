from .Grid_Pieces import Grid
from .Player import Player
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
    def draw(self, color):
        """ return True or False. """
        if self.grid.is_check(color):
            return False

        for y, row in enumerate(self.grid.get_grid()):
            for x, piece in enumerate(row):
                if not isinstance(piece, EmptyCell) and piece.get_color() == color:
                    for move in piece.possible_moves(self.grid):
                        # Create a copy of the grid to simulate the move
                        import copy
                        temp_grid = copy.deepcopy(self.grid)
                        
                        # Simulate the move
                        current_pos = (x, y)
                        temp_grid.set_piece_in_grid(move, piece)
                        temp_grid.set_piece_in_grid(current_pos, EmptyCell(x=x, y=y))
                        
                        # Check if the king is still in check
                        if not temp_grid.is_check(color):
                            return False
        return True
    def get_grid(self):
        return self.grid

## TODO :