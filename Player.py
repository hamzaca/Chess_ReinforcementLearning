from Chess.Grid_Pieces import Grid
from Chess.Grid_Pieces import Pawn, Rock, Bishop, Knight, Queen, King, EmptyCell

class Player():

    def __init__(self, name:str, color_player:str,grid:Grid):
        self.name = name
        self.color_player = color_player
        self.grid = grid

    def get_color(self):
        return self.color_player
    ### This method move a piece from the current position to a target.
    def move_piece(self,x_current, y_current, x_goal,y_goal):
        """Move the pawn to the position (x_goal,y_goal)"""
        piece = self.grid.get_piece(x_current, y_current)
        # check if it's a piece, not an empty cell.
        if not isinstance(piece, EmptyCell):
            target_cell = self.grid[y_goal][x_goal]
            if isinstance(target_cell, EmptyCell):
                self.grid[y_goal][x_goal] = piece
                self.grid[y_current][x_current] = EmptyCell(x=x_current, y=y_current )
            else:
                color_piece = target_cell.get_color()
                if color_piece != self.color_player:
                    self.grid[y_goal][x_goal] = piece
                    self.grid[y_current][x_current] = EmptyCell(x=x_current, y=y_current)
                else:
                    print(" This move is not allowed. you can not capture you own piece ! ")
        else :
            print(" The selected piece is not a pawn. Check Please ! ")




    ### Pieces movements :
    def move_pawn(self, x_current, y_current, x_goal,y_goal):
        #TODO : check if it's a legal move for the pawn
        self.move_piece(x_current, y_current, x_goal,y_goal)


    def move_rock(self,x_current, y_current, x_goal,y_goal):
        """Move the rock to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the rock
        self.move_piece(x_current, y_current, x_goal,y_goal)


    def move_bishop(self, x_current, y_current, x_goal, y_goal):
        """Move the bishop to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the bishop
        self.move_piece(x_current, y_current, x_goal,y_goal)


    def move_knight(self, x_current, y_current, x_goal, y_goal):
        """Move the knight to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the knight
        self.move_piece(x_current, y_current, x_goal,y_goal)

    def move_queen(self, x_current, y_current, x_goal, y_goal):
        """Move the queen to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the queen
        self.move_piece(x_current, y_current, x_goal,y_goal)

    def move_king(self, x_current, y_current, x_goal, y_goal):
        """Move the king to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the king
        self.move_piece(x_current, y_current, x_goal,y_goal)