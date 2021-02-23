from chess.Player import  Player
from chess.Grid_Pieces import Grid


if __name__ == '__main__':

    color_player1 = "white"
    color_player2 = "black"
    grid = Grid(color_player1=color_player1,color_player2=color_player2)
    player1 = Player(grid,name='Hamza',color_player="white")
    player2 = Player(grid,name='Chess_Engine', color_player="black")

    print(" The player {}  plays the color {}, while the player {} plays the color {}.".format(player1.get_name(), player1.get_color(),player2.get_name(), player2.get_color()))

    rock = grid.get_grid()[0][0]
    print(" the rock in the position x={}, y={} has the color {}".format(rock.get_x(),rock.get_y(), rock.get_color()))
    rock = grid.get_grid()[0][7]
    print(" the rock in the position x={}, y={} has the color {}".format(rock.get_x(),rock.get_y(), rock.get_color()))

    ## test the possible moves.
    pawn = grid.get_grid()[0][6]
    print(" the pawn in the position x={}, y={} has the color {}".format(pawn.get_x(),pawn.get_y(), pawn.get_color()))
    print(" the pawn possible moves : {}".format(pawn.possible_moves()))