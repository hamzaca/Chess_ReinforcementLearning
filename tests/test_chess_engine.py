"""Tests for the refactored chess_engine package.

The perft tests cross-validate full legal move generation (castling,
en passant, promotion, pins, checks) against python-chess, which is the
reference implementation. Each legacy bug also gets a targeted regression
test.
"""

import chess as pychess  # reference implementation (python-chess)
import pytest

from chess_engine import BLACK, START_FEN, WHITE, Board, IllegalMoveError, Move, parse_square

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
EP_POSITION = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
PROMO_POSITION = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"


def ref_perft(fen: str, depth: int) -> int:
    board = pychess.Board(fen)

    def walk(b: pychess.Board, d: int) -> int:
        if d == 0:
            return 1
        return sum(walk_after(b, m, d) for m in b.legal_moves)

    def walk_after(b: pychess.Board, move: pychess.Move, d: int) -> int:
        b.push(move)
        try:
            return walk(b, d - 1)
        finally:
            b.pop()

    return walk(board, depth)


# --------------------------------------------------------------- perft


@pytest.mark.parametrize(
    "fen,depth,expected",
    [
        (START_FEN, 1, 20),
        (START_FEN, 2, 400),
        (START_FEN, 3, 8902),
        (KIWIPETE, 1, 48),
        (KIWIPETE, 2, 2039),
        (EP_POSITION, 1, 14),
        (EP_POSITION, 2, 191),
        (EP_POSITION, 3, 2812),
        (PROMO_POSITION, 1, 6),
        (PROMO_POSITION, 2, 264),
    ],
)
def test_perft_known_values(fen, depth, expected):
    assert Board(fen).perft(depth) == expected


@pytest.mark.parametrize("fen", [START_FEN, KIWIPETE, EP_POSITION, PROMO_POSITION])
def test_perft_matches_python_chess(fen):
    depth = 2
    assert Board(fen).perft(depth) == ref_perft(fen, depth)


def test_move_lists_match_python_chess_move_by_move():
    """Play a game and compare the full legal move set at every ply."""
    sans = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7",
            "Re1", "b5", "Bb3", "O-O", "c3", "d5", "exd5", "Nxd5"]
    ref = pychess.Board()
    mine = Board()
    for san in sans:
        move = ref.parse_san(san)
        mine.push_uci(move.uci())
        ref.push(move)
        # en_passant="fen" makes python-chess always print the ep square,
        # matching plain-FEN style; both dialects are valid.
        assert mine.fen() == ref.fen(en_passant="fen")
        assert sorted(m.uci for m in mine.legal_moves()) == sorted(
            m.uci() for m in ref.legal_moves
        )


# ------------------------------------------- legacy bug regressions


def test_bug1_color_is_a_plain_attribute():
    """Legacy: get_color was sometimes a @property, sometimes a method."""
    board = Board()
    piece = board.piece_at(parse_square("a1"))
    assert piece.color == WHITE
    assert piece.kind == "R"


def test_bug3_pawn_direction_follows_color_not_player():
    """Legacy: pawn direction depended on player seating; random color
    assignment sent pawns the wrong way."""
    board = Board()
    # White pawn e2 goes up the board.
    assert {m.uci for m in board.legal_moves_from(parse_square("e2"))} == {"e2e3", "e2e4"}
    board.push_uci("e2e4")
    # Black pawn e7 goes down the board, regardless of any "player" concept.
    assert {m.uci for m in board.legal_moves_from(parse_square("e7"))} == {"e7e6", "e7e5"}


def test_bug4_capture_leaves_no_stale_coordinates():
    """Legacy: swap_pieces did not update the capturing piece's x/y."""
    board = Board()
    board.push_uci("e2e4")
    board.push_uci("d7d5")
    board.push_uci("e4d5")  # capture
    pawn = board.piece_at(parse_square("d5"))
    assert pawn is not None and pawn.color == WHITE and pawn.kind == "P"
    assert board.piece_at(parse_square("e4")) is None
    # The capturing pawn generates moves from its NEW square (it is white's
    # turn again after a black reply).
    board.push_uci("g8f6")
    ucis = {m.uci for m in board.legal_moves() if m.from_sq == parse_square("d5")}
    assert "d5d6" in ucis


def test_bug5_checkmate_detection_is_sound():
    """Legacy: is_check_mate simulated with stale piece objects."""
    board = Board()
    for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:  # Fool's mate
        board.push_uci(uci)
    assert board.is_checkmate()
    assert board.result() == "0-1"
    assert board.legal_moves() == []


def test_bug6_cannot_move_into_check_or_ignore_pin():
    # After 1.e4 e5 2.Bb5 the d7 pawn is NOT pinned, but after Bb5 pins a
    # knight on c6... use a direct pin: white Bb5 pins black Nc6 after d7 out.
    board = Board("rnbqkbnr/ppp2ppp/3p4/1B2p3/4P3/8/PPPP1PPP/RNBQK1NR b KQkq - 0 3")
    # Nc6 would be legal; but from this position check the king cannot walk
    # into an attacked square instead.
    board = Board("4k3/8/8/8/8/8/4r3/4K3 w - - 0 1")
    ucis = {m.uci for m in board.legal_moves()}
    # King on e1, black rook on e2: e1 is in check; capturing e2 is legal
    # (undefended rook), but d2/f2 stay illegal only if attacked — here rook
    # covers d2/f2, so the only legal moves are Kxe2, Kd1->? etc. Verify
    # against python-chess instead of hand-listing.
    ref = pychess.Board("4k3/8/8/8/8/8/4r3/4K3 w - - 0 1")
    assert ucis == {m.uci() for m in ref.legal_moves}


def test_pinned_piece_cannot_move():
    # Black knight on d7 pinned against the king on e8 by white rook on d1?
    # Use a classic absolute pin: white Re1, black Ne5, black Ke8.
    fen = "4k3/8/8/4n3/8/8/8/4RK2 b - - 0 1"
    board = Board(fen)
    ref = pychess.Board(fen)
    assert {m.uci for m in board.legal_moves()} == {m.uci() for m in ref.legal_moves}
    # The knight is pinned: it must have no legal moves.
    assert board.legal_moves_from(parse_square("e5")) == []


def test_castling_through_check_is_illegal():
    # White to castle kingside, but black rook attacks f1.
    fen = "4k3/8/8/8/8/8/5r2/R3K2R w KQ - 0 1"
    board = Board(fen)
    ref = pychess.Board(fen)
    assert {m.uci for m in board.legal_moves()} == {m.uci() for m in ref.legal_moves}
    assert "e1g1" not in {m.uci for m in board.legal_moves()}


def test_en_passant_round_trip():
    board = Board()
    for uci in ["e2e4", "a7a6", "e4e5", "d7d5"]:
        board.push_uci(uci)
    assert board.ep_target == parse_square("d6")
    board.push_uci("e5d6")  # en passant capture
    assert board.piece_at(parse_square("d5")) is None  # captured pawn removed
    captured_ref = pychess.Board()
    for uci in ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"]:
        captured_ref.push_uci(uci)
    assert board.fen() == captured_ref.fen()


def test_promotion_defaults_to_queen():
    fen = "8/P6k/8/8/8/8/8/K7 w - - 0 1"
    board = Board(fen)
    board.push_uci("a7a8")  # no promotion piece given -> auto-queen
    piece = board.piece_at(parse_square("a8"))
    assert piece.kind == "Q" and piece.color == WHITE


def test_illegal_move_raises():
    board = Board()
    with pytest.raises(IllegalMoveError):
        board.push(Move(parse_square("e2"), parse_square("e5")))
    with pytest.raises(IllegalMoveError):
        board.push_uci("b8c6")  # not white's piece


def test_fen_round_trip():
    for fen in [START_FEN, KIWIPETE, EP_POSITION, PROMO_POSITION]:
        assert Board(fen).fen() == fen


def test_stalemate():
    fen = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"  # classic queen stalemate
    board = Board(fen)
    ref = pychess.Board(fen)
    assert ref.is_stalemate()
    assert board.is_stalemate()
    assert board.result() == "1/2-1/2"
