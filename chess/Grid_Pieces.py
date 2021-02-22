##################################################### Interface for Pieces ########################################################

import abc
class PieceInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def possible_moves(self):
         # Possible moves by the pieces
        raise NotImplementedError

    @abc.abstractmethod
    def get_current_position(self):
        raise NotImplemented

    @aabc.bstractmethod
    def get_color(self):
        raise NotImplemented


####################################### Class Cell - all piece inherite from this class  ########################################################

class Cell():

    y_possible_positions = [0,1, 2, 3, 4, 5, 6, 7]
    x_possible_positions = [0, 1, 2, 3, 4, 5, 6, 7]

    def __init__(self, x : str, y : int):
        if self.x_does_exist(x):
            self.x = x
        if self.y_does_exist(y):
            self.y = y
    @staticmethod
    def y_does_exist(y):
        global y_possible_positions
        return y in y_possible_positions
    @staticmethod
    def x_does_exist(y):
        global x_possible_positions
        return x in x_possible_positions

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def is_empty(self):
        pass
    def occupant(self):
        """ return the  piece in the cell"""
        pass

################################ The Pawn  #################################

class Pawn(Cell):
    def __init__(self,x,y, black_or_white):
        super().__init__(self,x,y )
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        pass
    def get_current_position(self):
        pass

    def is_first_move(self):
        """  Return True if the Pawn is not moved yet. Flase else"""
        pass

################################ The Bishop  #################################

class Bishop(Cell):
    def __init__(self,x,y, black_or_white):
        super().__init__(self,x,y )
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        pass

    def get_current_position(self):
        pass


################################ The Knight  #################################

class Knight(Cell):
    def __init__(self,x,y, black_or_white):
        super().__init__(self,x,y )
        self.black_or_white = black_or_white


    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        pass

    def get_current_position(self):
        pass

################################ The Rock  #################################


class Rock(Cell):
    def __init__(self,x,y, black_or_white):
        super().__init__(self,x,y )
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        pass

    def get_current_position(self):
        pass

################################ The Queen  #################################


class Queen(Cell):
    def __init__(self,x,y, black_or_white):
        super().__init__(self,x,y )
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        pass

    def get_current_position(self):
        pass


################################ The King  #################################


class King(Cell):

    def __init__(self,x,y, black_or_white):
        super().__init__(self,x,y )
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        pass

    def get_current_position(self):
        pass

class EmptyCell(Cell) :

    def __init__(self,x,y):
        super().__init__(self,x,y)


##################################################### Cell and Grid ########################################################

class Grid():
    # The Grid is Matrix of 8x8 of Cells.
    def __init__(self, color_player1: str, color_player2: str ):
        self.color_player1 = color_player1
        self.color_player2 = color_player2
        # initialiaze Grid to the .
 

        self.grid = []
        self.grid += [[Rock(x=0, y=7, black_or_white=self.color_player1), Knight(x=1, y=7, black_or_white=self.color_player1), Bishop(x=2, y=7, black_or_white=self.color_player1), King(x=3, y=7, black_or_white=self.color_player1), Queen(x=4, y=7, black_or_white=self.color_player1), Bishop(x=5, y=7, black_or_white=self.color_player1),Knight(x=6, y=7, black_or_white=self.color_player1), Rock(x=7, y=7, black_or_white=self.color_player1)]]
        self.grid += [[Pawn(x=0, y=6, black_or_white=self.color_player1), Pawn(x=1, y=6, black_or_white=self.color_player1), Pawn(x=2, y=6, black_or_white=self.color_player1),     Pawn(x=3, y=6, black_or_white=self.color_player1), Pawn(x=4, y=6, black_or_white=self.color_player1), Pawn(x=5, y=6, black_or_white=self.color_player1) ,Pawn(x=6, y=6, black_or_white=self.color_player1)   , Pawn(x=7, y=6, black_or_white=self.color_player1)]]

        self.grid += [[EmptyCell(x=0, y=5),EmptyCell(x=1, y=5),EmptyCell(x=2, y=5),EmptyCell(x=3, y=5),EmptyCell(x=4, y=5),EmptyCell(x=5, y=5),EmptyCell(x=6, y=5),EmptyCell(x=7, y=5) ]]
        self.grid += [[EmptyCell(x=0, y=4),EmptyCell(x=1, y=4),EmptyCell(x=2, y=4),EmptyCell(x=3, y=4),EmptyCell(x=4, y=4),EmptyCell(x=5, y=4),EmptyCell(x=6, y=4),EmptyCell(x=7, y=4) ]]

        self.grid += [[EmptyCell(x=0, y=3),EmptyCell(x=1, y=3),EmptyCell(x=2, y=3),EmptyCell(x=3, y=3),EmptyCell(x=4, y=3),EmptyCell(x=5, y=3),EmptyCell(x=6, y=3),EmptyCell(x=7, y=3) ]]
        self.grid += [[EmptyCell(x=0, y=2),EmptyCell(x=1, y=2),EmptyCell(x=2, y=2),EmptyCell(x=3, y=2),EmptyCell(x=4, y=2),EmptyCell(x=5, y=2),EmptyCell(x=6, y=2),EmptyCell(x=7, y=2) ]]

        self.grid += [[Pawn(x=0, y=1, black_or_white=self.color_player2), Pawn(x=1, y=1, black_or_white=self.color_player2),   Pawn(x=2, y=1, black_or_white=self.color_player2),     Pawn(x=3, y=1, black_or_white=self.color_player2), Pawn(x=4, y=1, black_or_white=self.color_player2), Pawn(x=5, y=1, black_or_white=self.color_player2) ,  Pawn(x=6, y=1, black_or_white=self.color_player2)   , Pawn(x=7, y=1, black_or_white=self.color_player2)]]
        self.grid += [[Rock(x=0, y=0, black_or_white=self.color_player2), Knight(x=1, y=0, black_or_white=self.color_player2), Bishop(x=2, y=0, black_or_white=self.color_player2),   King(x=3, y=0, black_or_white=self.color_player2), Queen(x=4, y=0, black_or_white=self.color_player2), Bishop(x=5, y=0, black_or_white=self.color_player2),Knight(x=6, y=0, black_or_white=self.color_player2),  Rock(x=7, y=0, black_or_white=self.color_player2)]]


    def get_grid(self):
        return self.grid

    def get_piece(self, x, y):
        """ return the piece in the position given.
            May be an empty cell
        """
        return self.grid[y][x]

    def is_check(self):
        """" Verify if the king is check"""
        pass

    def is_check_mate(self):
        """ Verify if the King is checkmate"""
        pass

