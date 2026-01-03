import pygame
import os
from .Grid_Pieces import Grid, EmptyCell
from .Game import Game

width = height = 500
nb_squares = 8
size_per_square = height // nb_squares
max_fds = 15



def load_pieces_icons():
    """ Load icons for each piece for both colors."""
    pieces_images = {}
    for color in ["black", "white"]:
        for piece in ["Rock", "Bishop", "Knight", "Queen", "King", "Pawn"]:
            pieces_images[color + piece] = pygame.transform.scale(pygame.image.load(os.path.join(os.path.dirname(__file__), "pieces_images", color+piece+".png")),
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
    player_turn = "white"
    possible_moves = []
    game_over = False
    while running:
        # get the grid each time. Cause it might be updated.
        grid = game.get_grid()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONUP and not game_over:
                # get the x and y of the square or piece selected by the user using his mouse.
                location = pygame.mouse.get_pos()
                x = int(location[0])//size_per_square
                y = int(location[1])//size_per_square
                
                if piece_selected == (x, y):
                    piece_selected = ()
                    current_and_target = []
                    possible_moves = []
                else:
                    piece = grid.get_piece((x,y))
                    if not isinstance(piece, EmptyCell) and piece.get_color() == player_turn:
                        piece_selected = (x, y)
                        current_and_target.append(piece_selected)
                        possible_moves = piece.possible_moves(grid)
                    elif piece_selected:
                        if (x, y) in possible_moves:
                            current_and_target.append((x, y))

                if len(current_and_target) == 2:
                    x_y_current = current_and_target[0]
                    x_y_goal = current_and_target[1]
                    if player_turn == "white":
                        game.player1.move_piece(x_y_current, x_y_goal)
                        if grid.is_check_mate("black"):
                            print("Checkmate! White wins.")
                            game_over = True
                        elif game.draw("black"):
                            print("Draw!")
                            game_over = True
                        player_turn = "black"
                    else:
                        game.player2.move_piece(x_y_current, x_y_goal)
                        if grid.is_check_mate("white"):
                            print("Checkmate! Black wins.")
                            game_over = True
                        elif game.draw("white"):
                            print("Draw!")
                            game_over = True
                        player_turn = "white"

                    current_and_target = []
                    piece_selected = ()
                    possible_moves = []

        draw_board(screen, grid)

        # Highlight possible moves
        if piece_selected:
            pygame.draw.rect(screen, (255, 0, 0, 100), pygame.Rect(piece_selected[0]*size_per_square, piece_selected[1]*size_per_square, size_per_square, size_per_square), 3)
            for move in possible_moves:
                pygame.draw.circle(screen, (255, 0, 0, 100), (move[0]*size_per_square + size_per_square//2, move[1]*size_per_square + size_per_square//2), 10)

        clock.tick(max_fds)
        pygame.display.flip()


if __name__ == "__main__":
    mean()
