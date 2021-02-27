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
            pieces_images[color + piece] = pygame.transform.scale(
                pygame.image.load("pieces_images/" + color + piece + ".png"), (size_per_square, size_per_square))
    return pieces_images


# Load the icons of the pieces into a dictionary.
images = load_pieces_icons()


def draw_only_board(screen):
    """ draw the screen according to the chosen dimensions."""

    colors = [pygame.Color( 100, 100, 100, 100), pygame.Color(230, 230, 230, 255)]
    for x in range(nb_squares):
        for y in range(nb_squares):
            color = colors[(x + y) % 2]
            pygame.draw.rect(screen, color, pygame.Rect(y*size_per_square, x*size_per_square, size_per_square, size_per_square))



def draw_only_pieces(screen, grid):
    """ draw each piece in it position in the grid."""
    global images
    for x in range(nb_squares):
        for y in range(nb_squares):
            # get the piece in the square
            piece = grid.get_piece(y, x)
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
    images = load_pieces_icons()
    game = Game(color_choice="random")
    grid = game.get_grid()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
        draw_board(screen, grid)
        clock.tick(max_fds)
        pygame.display.flip()


if __name__ == "__main__":
    mean()
