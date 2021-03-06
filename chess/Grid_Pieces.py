import abc
# TODO : Fix the x and y position when black is up and when black is down.

################### Interface for Pieces ####################


class PieceInterface():
    @abc.abstractmethod
    def possible_moves(self):
         # Possible moves by the pieces
        raise NotImplementedError

    @abc.abstractmethod
    def get_current_position(self):
        raise NotImplemented

    @abc.abstractmethod
    def get_color(self):
        raise NotImplemented

    @abc.abstractmethod
    def get_name(self):
        raise NotImplemented


####################################### Class Cell - all piece inherite from this class  ########################################################

class Cell:

    def __init__(self, x: str, y: int):
        if self.x_does_exist(x):
            self.x = x
        if self.y_does_exist(y):
            self.y = y
        self.is_first_move = True

    @staticmethod
    def y_does_exist(y):
        possible_positions = [0, 1, 2, 3, 4, 5, 6, 7]
        return y in possible_positions
    @staticmethod
    def x_does_exist(x):
        possible_positions = [0,1, 2, 3, 4, 5, 6, 7]
        return x in possible_positions

    def set_is_first_move_to_false(self):
        self.is_first_move = False

    def set_position(self, x_destina, y_destina):
        """ Set the piece to a new position."""
        self.x = x_destina
        self.y = y_destina
        # when the piece is moved set the first movement to false.
        if self.is_first_move:
            self.set_is_first_move_to_false()

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


class Pawn(Cell, PieceInterface):
    def __init__(self, x, y, black_or_white):
        Cell.__init__(self, x, y)
        self.black_or_white = black_or_white
        # when the pawn is created, he didn't move yet so it's true.
        self.is_first_move = True

    def get_is_first_move(self):
        return self.is_first_move

    def set_is_first_move_to_false(self):
        self.is_first_move = False

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        """ Return a list of the possible general  moves of the piece.
        :return  :  matrix of the possible move for the pawn. eaxh line is a possible move.
        """
        possible_targets = []
        if self.black_or_white == "white":
            if self.is_first_move:
                possible_targets.append((self.x, self.y + 1))
                possible_targets.append((self.x, self.y + 2))
                # Capture to left or right
                # if not the pawn in the far lest of Grid, the pawn can capture.
                if self.x != 0:
                    possible_targets.append((self.x - 1, self.y + 1))
                # if not the pawn in the far right of Grid, the pawn can capture.
                if self.x != 7:
                    possible_targets.append((self.x + 1, self.y + 1))

            # Not the first move.
            else:
                possible_targets.append((self.x, self.y + 1))
                # Capture to left or right
                # if not the pawn in the far lest of Grid, the pawn can capture.
                if self.x != 0:
                    possible_targets.append((self.x - 1, self.y + 1))
                # if not the pawn in the far right of Grid, the pawn can capture.
                if self.x != 7:
                    possible_targets.append((self.x + 1, self.y + 1))


        # when it's the black pawn.
        else:
            if self.is_first_move:
                possible_targets.append((self.x, self.y - 1))
                possible_targets.append((self.x, self.y - 2))
                # Capture to left or right
                # if not the pawn in the far lest of Grid, the pawn can capture.
                if self.x != 0:
                    possible_targets.append((self.x - 1, self.y - 1))
                # if not the pawn in the far right of Grid, the pawn can capture.
                if self.x != 7:
                    possible_targets.append((self.x + 1, self.y - 1))
            # Not the first move
            else:
                possible_targets.append((self.x, self.y - 1))
                # Capture to left or right
                # if not the pawn in the far lest of Grid, the pawn can capture.
                if self.x != 0:
                    possible_targets.append((self.x - 1, self.y - 1))
                # if not the pawn in the far right of Grid, the pawn can capture.
                if self.x != 7:
                    possible_targets.append((self.x + 1, self.y - 1))

        return possible_targets


    def get_current_position(self):
        pass

    def get_name(self):
        return "Pawn"

    def get_color(self):
        return self.black_or_white


    def __repr__(self):
        return "Pawn(x={}, y={}, color = {})".format(self.x, self.y, self.black_or_white)


################################ The Bishop  #################################

class Bishop(Cell, PieceInterface):
    def __init__(self, x, y, black_or_white):
        Cell.__init__(self, x, y)
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        """ Return a list of the possible general  moves of the piece.
        :return  :  matrix of the possible move for the bishop. each line is a possible move.
        """
        possible_targets = []
        # bihsop's movement are according two lines. y = ax + b. with a = 1 for the first one and a = -1 for the second.
        # the value of b depends on the bishop  initial position.
        # compute b1 and b2
        b1 = self.y - self.x
        b2 = self.y + self.x
        x_y_possible_values=[0, 1, 2, 3, 4, 5, 6, 7]
        # for each x compute the correspondant y value that are in the lines of the bishop's movement.
        # check they are  integers among 0 and 7.
        for x_value in x_y_possible_values:
            y1 = x_value + b1
            y2 = -x_value + b2
            if y1 in x_y_possible_values:
                possible_targets.append((x_value, 7-y1))
            if y2 in x_y_possible_values:
                possible_targets.append((x_value, 7-y2))
        return list(dict.fromkeys(possible_targets))




    def get_current_position(self):
        pass

    def get_name(self):
        return "Bishop"

    def get_color(self):
        return self.black_or_white

    def __repr__(self):
        return "Bishop(x={}, y={}, color = {})".format(self.x, self.y, self.black_or_white)


################################ The Knight  #################################

class Knight(Cell, PieceInterface):
    def __init__(self, x, y, black_or_white):
        Cell.__init__(self, x, y)
        self.black_or_white = black_or_white


    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        """ Return a list of the possible general  moves of the piece.
        :return  :  matrix of the possible move for the knight. each line is a possible move.
        """
        possible_targets = []
        x_y_possible_values=[0,1,2,3,4,5,6,7]
        if self.x + 2 in x_y_possible_values:
            if self.y+1 in x_y_possible_values:
                possible_targets.append((self.x+2, self.y+1))
            if self.y - 1 in x_y_possible_values:
                possible_targets.append((self.x + 2, self.y - 1))

        if self.x - 2 in x_y_possible_values:
            if self.y+1 in x_y_possible_values:
                possible_targets.append((self.x-2, self.y + 1))
            if self.y - 1 in x_y_possible_values:
                possible_targets.append((self.x-2, self.y - 1))

        if self.y + 2 in x_y_possible_values:
            if self.x + 1 in x_y_possible_values:
                possible_targets.append((self.x + 1, self.y + 2))
            if self.x - 1 in x_y_possible_values:
                possible_targets.append((self.x - 1, self.y + 2))

        if self.y - 2 in x_y_possible_values:
            if self.x + 1 in x_y_possible_values:
                possible_targets.append((self.x + 1, self.y - 2))
            if self.x - 1 in x_y_possible_values:
                possible_targets.append((self.x - 1, self.y - 2))

        return list(dict.fromkeys(possible_targets))



    def get_current_position(self):
        pass

    def get_name(self):
        return "Knight"

    def get_color(self):
        return self.black_or_white

    def __repr__(self):
        return "Knight(x={}, y={}, color = {})".format(self.x, self.y, self.black_or_white)

################################ The Rock  #################################


class Rock(Cell, PieceInterface):
    def __init__(self, x, y, black_or_white):
        Cell.__init__(self, x, y)
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        """ Return a list of the possible general  moves of the piece.
        :return  :  matrix of the possible move for the bishop. each line is a possible move.
        """
        possible_targets = []
        for value in range(8):
            # vertical movement.
            if value != self.y:
                possible_targets.append((self.x, value))
            # horizontal movement.
            if value != self.x:
                possible_targets.append((value, self.y))
        print(" possible_targets : ",possible_targets)
        return list(dict.fromkeys(possible_targets))


    def get_current_position(self):
        pass

    def get_name(self):
        return "Rock"

    def get_color(self):
        return self.black_or_white

    def __repr__(self):
        return "Rock(x={}, y={}, color = {})".format(self.x, self.y, self.black_or_white)

################################ The Queen  #################################


class Queen(Cell, PieceInterface):

    def __init__(self, x, y, black_or_white):
        Cell.__init__(self, x, y)
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        """ Return a list of the possible general  moves of the piece.
        :return  :  matrix of the possible move for the queen. each line is a possible move.
        """
        possible_targets = []
        ## The bishop like movements.
        b1 = self.y - self.x
        b2 = self.y + self.x
        x_y_possible_values=[0,1,2,3,4,5,6,7]
        # for each x compute the correspondant y value that are in the lines of the bishop's movement.
        # check they are  integers among 0 and 7.
        for x_value in x_y_possible_values:
            y1 = x_value + b1
            y2 = -x_value + b2
            if y1 in x_y_possible_values:
                possible_targets.append((x_value, 7 - y1))
            if y2 in x_y_possible_values:
                possible_targets.append((x_value, 7 - y2))
        ## add the rock like movement.
        for value in range(8):
            # vertical movement.
            if value != self.y:
                possible_targets.append((self.x, value))
            # horizontal movement.
            if value != self.x:
                possible_targets.append((value, self.y))
        # The bishop line have a cell in common. so let's delete the duplicates in the output.
        return list(dict.fromkeys(possible_targets))

    def get_current_position(self):
        pass

    def get_name(self):
        return "Queen"

    def get_color(self):
        return self.black_or_white

    def __repr__(self):
        return "Queen(x={}, y={}, color = {})".format(self.x, self.y, self.black_or_white)


################################ The King  #################################


class King(Cell, PieceInterface):

    def __init__(self, x, y, black_or_white):
        Cell.__init__(self, x, y)
        self.black_or_white = black_or_white

    def get_color(self):
        return self.black_or_white

    def possible_moves(self):
        """ Return a list of the possible general  moves of the piece.
        :return  :  matrix of the possible move for the king. each line is a possible move.
        """
        possible_targets = []
        x_y_possible_values=[0, 1, 2, 3, 4, 5, 6, 7]
        if self.x + 1 in x_y_possible_values:
            possible_targets.append((self.x + 1, self.y))
            if self.y+1 in x_y_possible_values:
                possible_targets.append((self.x+1, self.y+1))
            if self.y - 1 in x_y_possible_values:
                possible_targets.append((self.x + 1, self.y - 1))

        if self.x - 1 in x_y_possible_values:
            possible_targets.append((self.x - 1, self.y))
            if self.y+1 in x_y_possible_values:
                possible_targets.append((self.x - 1, self.y+1))
            if self.y - 1 in x_y_possible_values:
                possible_targets.append((self.x - 1, self.y - 1))

        if self.y + 1 in x_y_possible_values:
            possible_targets.append((self.x, self.y + 1))
        if self.y - 1 in x_y_possible_values:
            possible_targets.append((self.x, self.y - 1))

        return list(dict.fromkeys(possible_targets))


    def get_current_position(self):
        pass

    def get_name(self):
        return "King"

    def get_color(self):
        return self.black_or_white

    def __repr__(self):
        return "King(x={}, y={}, color = {})".format(self.x, self.y, self.black_or_white)



class EmptyCell(Cell):
    def __init__(self, x, y):
        super().__init__(x, y)

    def __repr__(self):
        return "EmptyCell(x={}, y={})".format(self.x, self.y)



##################################################### Cell and Grid ########################################################

class Grid:
    # The Grid is Matrix of 8x8 of Cells.
    def __init__(self, color_player1: str, color_player2: str):
        self.color_player1 = color_player1
        self.color_player2 = color_player2
        # initialiaze Grid to the .
 

        self.grid = []
        self.grid += [[Rock(x=0, y=0, black_or_white=self.color_player1), Knight(x=1, y=0, black_or_white=self.color_player1), Bishop(x=2, y=0, black_or_white=self.color_player1), King(x=3, y=0, black_or_white=self.color_player1), Queen(x=4, y=0, black_or_white=self.color_player1), Bishop(x=5, y=0, black_or_white=self.color_player1),Knight(x=6, y=0, black_or_white=self.color_player1), Rock(x=7, y=0, black_or_white=self.color_player1)]]
        self.grid += [[Pawn(x=0, y=1, black_or_white=self.color_player1), Pawn(x=1, y=1, black_or_white=self.color_player1), Pawn(x=2, y=1, black_or_white=self.color_player1),     Pawn(x=3, y=1, black_or_white=self.color_player1), Pawn(x=4, y=1, black_or_white=self.color_player1), Pawn(x=5, y=1, black_or_white=self.color_player1) ,Pawn(x=6, y=1, black_or_white=self.color_player1)   , Pawn(x=7, y=1, black_or_white=self.color_player1)]]

        self.grid += [[EmptyCell(x=0, y=2), EmptyCell(x=1, y=2),EmptyCell(x=2, y=2),EmptyCell(x=3, y=5),EmptyCell(x=4, y=2),EmptyCell(x=5, y=2),EmptyCell(x=6, y=2),EmptyCell(x=7, y=2) ]]
        self.grid += [[EmptyCell(x=0, y=3), EmptyCell(x=1, y=3),EmptyCell(x=2, y=3),EmptyCell(x=3, y=4),EmptyCell(x=4, y=3),EmptyCell(x=5, y=3),EmptyCell(x=6, y=3),EmptyCell(x=7, y=3) ]]

        self.grid += [[EmptyCell(x=0, y=4), EmptyCell(x=1, y=4),EmptyCell(x=2, y=4),EmptyCell(x=3, y=3),EmptyCell(x=4, y=4),EmptyCell(x=5, y=4),EmptyCell(x=6, y=4),EmptyCell(x=7, y=4) ]]
        self.grid += [[EmptyCell(x=0, y=5), EmptyCell(x=1, y=5),EmptyCell(x=2, y=5),EmptyCell(x=3, y=2),EmptyCell(x=4, y=5),EmptyCell(x=5, y=5),EmptyCell(x=6, y=5),EmptyCell(x=7, y=5) ]]

        self.grid += [[Pawn(x=0, y=6, black_or_white=self.color_player2), Pawn(x=1, y=6, black_or_white=self.color_player2),   Pawn(x=2, y=6, black_or_white=self.color_player2),     Pawn(x=3, y=6, black_or_white=self.color_player2), Pawn(x=4, y=6, black_or_white=self.color_player2), Pawn(x=5, y=6, black_or_white=self.color_player2) ,  Pawn(x=6, y=6, black_or_white=self.color_player2)   , Pawn(x=7, y=6, black_or_white=self.color_player2)]]
        self.grid += [[Rock(x=0, y=7, black_or_white=self.color_player2), Knight(x=1, y=7, black_or_white=self.color_player2), Bishop(x=2, y=7, black_or_white=self.color_player2),   King(x=3, y=7, black_or_white=self.color_player2), Queen(x=4, y=7, black_or_white=self.color_player2), Bishop(x=5, y=7, black_or_white=self.color_player2),Knight(x=6, y=7, black_or_white=self.color_player2),  Rock(x=7, y=7, black_or_white=self.color_player2)]]


    def get_grid(self):
        return self.grid

    def get_piece(self, x_and_y):
        """ return the piece in the position given.
            May be an empty cell
            :param
                - x_and_y : is a tuple of the coordinate x and y of the cell in the grid.
        """
        x, y = x_and_y
        return self.grid[y][x]


    def set_piece_in_grid(self, x_y_goal, piece):
        x, y = x_y_goal
        self.grid[y][x] = piece



    def is_check(self):
        """" Verify if the king is check"""
        pass

    def is_check_mate(self):
        """ Verify if the King is checkmate"""
        pass

