import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { fenToBoard, pieceImage } from '../board-utils';
import { Color, MovePlayed } from '../models';
import { ChessService } from '../services/chess.service';

interface PositionState {
  fen: string;
  turn: Color;
  pgn: string;
  user_color: Color;
  in_check: boolean;
  is_game_over: boolean;
  result: string | null;
  move_count: number;
}

@Component({
  selector: 'app-chess-board',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './chess-board.component.html',
  styleUrls: ['./chess-board.component.css'],
})
export class ChessBoardComponent implements OnInit {
  /** Board matrix in DISPLAY order — the user's pieces are always at the bottom. */
  board: (string | null)[][] = [];
  fen = '';
  turn: Color = 'white';
  pgn = '';
  gameId: number | null = null;
  userColor: Color = 'white';
  moveCount = 0;

  /** UI toggle: highlight legal destinations of the selected piece. */
  showLegalMoves = true;

  selected: { row: number; col: number } | null = null;
  legalTargets: string[] = [];
  lastMove: string[] = [];

  inCheck = false;
  isGameOver = false;
  result: string | null = null;

  message = '';
  error = '';
  loading = false;

  readonly pieceImage = pieceImage;

  constructor(private chess: ChessService) {}

  ngOnInit(): void {
    // Resume (or create) the current game and render its exact position.
    this.chess.getCurrentGame().subscribe({
      next: (game) => {
        this.gameId = game.game_id;
        this.applyState(game);
        this.message = game.created
          ? `New game started. You play ${game.user_color}.`
          : `Game resumed. You play ${game.user_color}.`;
      },
      error: () => (this.error = 'Could not reach the server.'),
    });
  }

  // ---------------------------------------------------------- orientation

  /** Map a displayed cell to its algebraic square, honoring board flip. */
  squareAt(row: number, col: number): string {
    if (this.userColor === 'white') {
      return 'abcdefgh'[col] + String(8 - row);
    }
    return 'abcdefgh'[7 - col] + String(row + 1);
  }

  rankLabel(row: number): number {
    return this.userColor === 'white' ? 8 - row : row + 1;
  }

  fileLabel(col: number): string {
    return this.userColor === 'white' ? 'abcdefgh'[col] : 'abcdefgh'[7 - col];
  }

  private orient(matrix: (string | null)[][]): (string | null)[][] {
    if (this.userColor === 'white') {
      return matrix;
    }
    return matrix
      .slice()
      .reverse()
      .map((row) => row.slice().reverse());
  }

  // -------------------------------------------------------------- state

  applyState(state: PositionState): void {
    this.fen = state.fen;
    this.turn = state.turn;
    this.pgn = state.pgn;
    this.userColor = state.user_color;
    this.inCheck = state.in_check;
    this.isGameOver = state.is_game_over;
    this.result = state.result;
    this.moveCount = state.move_count;
    this.board = this.orient(fenToBoard(state.fen));
    if (state.is_game_over) {
      this.message = this.resultText(state.result);
    }
  }

  resultText(result: string | null): string {
    const userWon = (this.userColor === 'white') === (result === '1-0');
    switch (result) {
      case '1-0':
      case '0-1':
        return userWon ? 'Checkmate — you win!' : 'Checkmate — the agent wins.';
      case '1/2-1/2':
        return 'Draw.';
      case '*':
        return 'Game aborted.';
      default:
        return 'Game over.';
    }
  }

  isUserPiece(code: string | null): boolean {
    if (!code) {
      return false;
    }
    const isWhitePiece = code === code.toUpperCase();
    return isWhitePiece === (this.userColor === 'white');
  }

  isSelected(row: number, col: number): boolean {
    return this.selected?.row === row && this.selected?.col === col;
  }

  isLegalTarget(row: number, col: number): boolean {
    return this.showLegalMoves && this.legalTargets.includes(this.squareAt(row, col));
  }

  isLastMove(row: number, col: number): boolean {
    return this.lastMove.includes(this.squareAt(row, col));
  }

  // -------------------------------------------------------------- moves

  onSquareClick(row: number, col: number): void {
    if (this.isGameOver || this.loading) {
      return;
    }
    this.error = '';
    const code = this.board[row][col];
    const square = this.squareAt(row, col);

    // Clicking the selected piece again deselects it.
    if (this.isSelected(row, col)) {
      this.clearSelection();
      return;
    }

    // Clicking one of our own pieces (re)selects and highlights it.
    if (this.isUserPiece(code) && this.turn === this.userColor) {
      this.selected = { row, col };
      this.legalTargets = [];
      if (this.showLegalMoves) {
        this.chess.possibleMoves(square).subscribe({
          next: (response) => (this.legalTargets = response.moves),
        });
      }
      return;
    }

    // Otherwise: attempt a move if a piece is selected.
    if (this.selected) {
      if (this.showLegalMoves && !this.legalTargets.includes(square)) {
        this.error = `${square} is not a legal destination.`;
        this.clearSelection();
        return;
      }
      this.attemptMove(this.squareAt(this.selected.row, this.selected.col), square);
    }
  }

  attemptMove(from: string, to: string): void {
    // Auto-queen: a user pawn arriving on its promotion rank.
    const piece = this.selected ? this.board[this.selected.row][this.selected.col] : null;
    const isPawn = piece?.toLowerCase() === 'p';
    const promotionRank = this.userColor === 'white' ? '8' : '1';
    const promotion = isPawn && to.endsWith(promotionRank) ? 'q' : undefined;

    this.loading = true;
    this.chess.makeMove(from, to, promotion).subscribe({
      next: (response) => {
        this.loading = false;
        this.clearSelection();
        this.applyState(response);
        this.lastMove = this.movesToSquares(response.agent_move ?? response.user_move);
        if (!response.is_game_over) {
          this.message = response.agent_move
            ? `Agent played ${response.agent_move.san}. Your turn.`
            : 'Your turn.';
        }
      },
      error: (err) => {
        this.loading = false;
        this.clearSelection();
        this.error = err.error?.detail ?? 'Move rejected.';
      },
    });
  }

  movesToSquares(move: MovePlayed): string[] {
    return [move.from_square, move.to_square];
  }

  clearSelection(): void {
    this.selected = null;
    this.legalTargets = [];
  }

  // -------------------------------------------------------------- undo

  undoMove(): void {
    this.performUndo(undefined, 'Move taken back.');
  }

  undoToStart(): void {
    this.performUndo(9999, 'Rewound to the start of the game.');
  }

  private performUndo(plies: number | undefined, successMessage: string): void {
    if (this.loading) {
      return;
    }
    this.loading = true;
    this.chess.undo(plies).subscribe({
      next: (state) => {
        this.loading = false;
        this.clearSelection();
        this.lastMove = [];
        this.applyState(state);
        this.message = successMessage;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail ?? 'Nothing to undo.';
      },
    });
  }

  abortGame(): void {
    if (this.loading || this.isGameOver) {
      return;
    }
    if (!confirm('Abort this game? It ends with no winner.')) {
      return;
    }
    this.loading = true;
    this.chess.abortGame().subscribe({
      next: (state) => {
        this.loading = false;
        this.clearSelection();
        this.applyState(state);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail ?? 'Could not abort the game.';
      },
    });
  }

  // ---------------------------------------------------------- new game

  newGame(): void {
    this.loading = true;
    this.chess.newGame().subscribe({
      next: (game) => {
        this.loading = false;
        this.gameId = game.game_id;
        this.clearSelection();
        this.lastMove = [];
        this.applyState(game);
        this.message = `New game started. You play ${game.user_color}.`;
      },
      error: () => {
        this.loading = false;
        this.error = 'Could not start a new game.';
      },
    });
  }
}
