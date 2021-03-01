from chess.Grid_Pieces import Grid
from chess.Grid_Pieces import Pawn, Rock, Bishop, Knight, Queen, King, EmptyCell


class Player:

    def __init__(self, grid: Grid, name: str, color_player: str):
        self.name = name
        self.color_player = color_player
        self.grid = grid

    @property
    def get_name(self):
        return self.name

    @property
    def get_color(self):
        return self.color_player

    def swap_pieces(self, x_y_current, x_y_goal):
        """This method move a piece from the current position to a target (x_goal,y_goal)
        :parameter
            -  x_y_current : coordinates of the current position.
            -  x_y_goal   : coordinates of the target position.


        """
        x_current, y_current = x_y_current
        x_goal, y_goal = x_y_goal

        piece = self.grid.get_piece(x_y_current)
        # check if it's a piece, not an empty cell.
        if not isinstance(piece, EmptyCell):
            target_cell = self.grid.get_piece(x_y_goal)
            if isinstance(target_cell, EmptyCell):
                # set the internal position of the piece to the goal coordinates.
                piece.set_position(x_destina=x_goal, y_destina=y_goal)
                # move the piece to the goal cell and destroy the piece already in the cell.
                self.grid.set_piece_in_grid(x_y_goal, piece)
                # set the cell where the piece was to an Empty Cell.
                self.grid.set_piece_in_grid(x_y_current, EmptyCell(x=x_current, y=y_current))

            else:
                color_piece = target_cell.get_color()
                if color_piece != self.color_player:
                    self.grid.set_piece_in_grid(x_y_goal, piece)
                    self.grid.set_piece_in_grid(x_y_current, EmptyCell(x=x_current, y=y_current))
                else:
                    print(" This move is not allowed. you can not capture you own piece ! ")
        else:
            print(" The selected piece is not a pawn. Check Please ! ")




    ### Pieces movements :
    def move_pawn(self,x_y_current, x_y_goal):
        pawn = self.grid.get_piece(x_y_current)
        # get the possible moves from the current cell.
        possibles_moves = pawn.possible_moves()
        print(" paw first move : ------>", pawn.get_is_first_move())
        print(" pawn possible moves : ", possibles_moves)
        if x_y_goal in possibles_moves:
            self.swap_pieces(x_y_current, x_y_goal)
        else:
            print(" the move selected is not allowed..")
        # when the pawn moves  the first times it loses the possibility to mov two wells at one jump.
        pawn.set_is_first_move_to_false()
        print(" paw first move : ------>", pawn.get_is_first_move())


    def move_rock(self, x_y_current, x_y_goal):
        """Move the rock to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the rock
        rock = self.grid.get_piece(x_y_current)
        possibles_moves = rock.possible_moves()
        print(" pawn possible moves : ", possibles_moves)
        if x_y_goal in possibles_moves:
            self.swap_pieces(x_y_current, x_y_goal)

    def move_bishop(self, x_y_current, x_y_goal):
        """Move the bishop to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the bishop
        bishop = self.grid.get_piece(x_y_current)
        possibles_moves = bishop.possible_moves()
        print(" pawn possible moves : ", possibles_moves)

        if x_y_goal in possibles_moves:
            self.swap_pieces(x_y_current, x_y_goal)

    def move_knight(self, x_y_current, x_y_goal):
        """Move the knight to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the knight
        knight = self.grid.get_piece(x_y_current)
        possibles_moves = knight.possible_moves()
        print(" pawn possible moves : ", possibles_moves)
        if x_y_goal in possibles_moves:
            self.swap_pieces(x_y_current, x_y_goal)
    def move_queen(self, x_y_current, x_y_goal):
        """Move the queen to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the queen
        queen = self.grid.get_piece(x_y_current)
        possibles_moves = queen.possible_moves()
        print(" pawn possible moves : ", possibles_moves)
        self.swap_pieces(x_y_current, x_y_goal)

    def move_king(self, x_y_current, x_y_goal):
        """Move the king to the position (x_goal,y_goal)"""
        #TODO : check if it's a legal move for the king
        king = self.grid.get_piece(x_y_current)
        possibles_moves = king.possible_moves()
        if x_y_goal in possibles_moves:
            self.swap_pieces(x_y_current, x_y_goal)

    def move_piece(self, x_y_current, x_y_goal):
        """" move the pieces and using the defined function for each piece to check if it's a legal move or not.
        :parameter
            - x_y_current :  The coordinate of the current cell in the grid.
            - x_y_goal    : The coordinate of the target cell where the pice is going to be moved to."""
        piece = self.grid.get_piece(x_y_current)
        if isinstance(piece, Pawn):
            self.move_pawn(x_y_current, x_y_goal)
        elif isinstance(piece, Rock):
            self.move_rock(x_y_current, x_y_goal)
        elif isinstance(piece, Bishop):
            self.move_bishop(x_y_current, x_y_goal)
        elif isinstance(piece, Knight):
            self.move_knight(x_y_current, x_y_goal)
        elif isinstance(piece, Queen):
            self.move_queen(x_y_current, x_y_goal)
        elif isinstance(piece, King):
            self.move_king(x_y_current, x_y_goal)