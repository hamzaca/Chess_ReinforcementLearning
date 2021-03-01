import pygame
from chess.Grid_Pieces import Grid, EmptyCell
from chess.Game import Game

width = height = 500
nb_squares = 8
size_per_square = height // nb_squares
max_fds = 15



def load_pieces_icons():
    """ Load icons for each piece for both colors."""
    pieces_images = {}
    for color in ["black", "white"]:
        for piece in ["Rock", "Bishop", "Knight", "Queen", "King", "Pawn"]:
            pieces_images[color + piece] = pygame.transform.scale(pygame.image.load("pieces_images/" + color+piece+".png"),
                                                                  (size_per_square, size_per_square))
    return pieces_images


images = load_pieces_icons()



def draw_only_board(screen):
    """ draw the screen according to the chosen dimensions."""

    colors = [pygame.Color(100, 100, 100, 100), pygame.Color(230, 230, 230, 255)]
    for x in range(nb_squares):
        for y in range(nb_squares):
            color = colors[(x + y) % 2]
            pygame.draw.rect(screen, color, pygame.Rect(y*size_per_square, x*size_per_square, size_per_square, size_per_square))



def draw_only_pieces(screen, grid):
    """ draw each piece in it position in the grid."""
    # Load the icons of the pieces into a dictionary.
    for x in range(nb_squares):
        for y in range(nb_squares):
            # get the piece in the square
            piece = grid.get_piece((y, x))
            if not isinstance(piece, EmptyCell):
                piece_name = piece.get_name()
                piece_color = piece.get_color()
                screen.blit(images[piece_color+piece_name], pygame.Rect(y*size_per_square, x*size_per_square, size_per_square, size_per_square))





def draw_board(screen, grid):
    """ draw the whole board """
    draw_only_board(screen)
    draw_only_pieces(screen, grid)


def mean():
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    screen.fill(pygame.Color("white"))
    game = Game(color_choice="random")
    running = True
    piece_selected = ()
    # list of two tuples indicating the start and the target of the selected piece.
    current_and_target = []
    while running:
        # get the grid each time. Cause it might be updated.
        grid = game.get_grid()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONUP:
                # get the x and y of the square or piece selected by the user using his mouse.
                location = pygame.mouse.get_pos()
                x = int(location[0])//size_per_square
                y = int(location[1])//size_per_square
                # check if the piece is selected already.
                # deselect it if so.
                ## TODO : draw a red dot on the selected cell.
                if piece_selected == (x, y):
                    piece_selected = ()
                    current_and_target = []
                    print(" x , y = ({}, {}) is already selected;  so it will be deselected ".format(x, y))
                # if the target is != from the current position. when add
                else:
                    piece_selected = (x, y)
                    piece = grid.get_piece(piece_selected)
                    print(" --------- the piece selected -------> :  ", piece)
                    current_and_target.append(piece_selected)

                # if two position already selected, play the move reset and add the new selected piece to the list.
                if len(current_and_target) == 2:
                    print(" the positions to play is : ", current_and_target)
                    x_y_current = current_and_target[0]
                    x_y_goal = current_and_target[1]
                    game.player1.move_piece(x_y_current, x_y_goal)
                    print("current_and_target = ({})".format(current_and_target))


                    # When the position is played reset the list to empty.
                    current_and_target = []
                else:
                    print(" x , y = ({}, {})".format(x, y))
                    print("current_and_target = ({})".format(current_and_target))
                print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

        draw_board(screen, grid)
        clock.tick(max_fds)
        pygame.display.flip()


if __name__ == "__main__":
    mean()
