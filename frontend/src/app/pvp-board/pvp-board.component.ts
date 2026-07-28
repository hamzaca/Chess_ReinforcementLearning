import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { fenToBoard, pieceImage } from '../board-utils';
import { Color, PvpState } from '../models';
import {
  getSeatToken,
  getShareToken,
  saveSeatToken,
  saveShareToken,
} from '../pvp-token-store';
import { ChessService } from '../services/chess.service';

const POLL_MS = 2000;

@Component({
  selector: 'app-pvp-board',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './pvp-board.component.html',
  styleUrls: ['./pvp-board.component.css'],
})
export class PvpBoardComponent implements OnInit, OnDestroy {
  gameId = 0;
  token: string | null = null;
  shareToken: string | null = null;

  state: PvpState | null = null;
  /** Board matrix in DISPLAY order (own pieces at the bottom for online). */
  board: (string | null)[][] = [];
  orientation: Color = 'white';

  showLegalMoves = true;
  selected: { row: number; col: number } | null = null;
  legalTargets: string[] = [];

  message = '';
  error = '';
  loading = false;
  linkCopied = false;

  private pollHandle: ReturnType<typeof setInterval> | null = null;

  readonly pieceImage = pieceImage;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private chess: ChessService,
  ) {}

  ngOnInit(): void {
    this.gameId = Number(this.route.snapshot.paramMap.get('id'));

    // Security: tokens live in sessionStorage, not in the URL. If an old
    // link still carries them as query params, migrate them into storage
    // once and scrub the address bar.
    const queryToken = this.route.snapshot.queryParamMap.get('token');
    const queryShare = this.route.snapshot.queryParamMap.get('share');
    if (queryToken) {
      saveSeatToken(this.gameId, queryToken);
    }
    if (queryShare) {
      saveShareToken(this.gameId, queryShare);
    }
    if (queryToken || queryShare) {
      this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    }

    this.token = getSeatToken(this.gameId);
    this.shareToken = getShareToken(this.gameId);
    this.refresh();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  // ------------------------------------------------------------- state

  get shareLink(): string {
    return `${location.origin}/join/${this.gameId}/${this.shareToken}`;
  }

  get waitingForOpponent(): boolean {
    return !!this.state && this.state.mode === 'online' && !this.state.opponent_joined;
  }

  get isMyTurn(): boolean {
    if (!this.state || this.state.is_game_over || !this.state.opponent_joined) {
      return false;
    }
    return this.state.mode === 'local' || this.state.turn === this.state.your_color;
  }

  nameOf(color: Color): string {
    const name = color === 'white' ? this.state?.white_name : this.state?.black_name;
    return name ?? (color === 'white' ? 'White' : '(waiting…)');
  }

  isYou(color: Color): boolean {
    return this.state?.mode === 'online' && this.state.your_color === color;
  }

  refresh(): void {
    this.chess.pvpState(this.gameId, this.token ?? undefined).subscribe({
      next: (state) => this.applyState(state),
      error: () => (this.error = 'Could not load this game.'),
    });
  }

  applyState(state: PvpState): void {
    const previousCount = this.state?.move_count ?? -1;
    this.state = state;
    this.orientation = state.mode === 'online' && state.your_color ? state.your_color : 'white';
    this.board = this.orient(fenToBoard(state.fen));
    if (state.is_game_over) {
      this.message = this.resultText(state);
      this.stopPolling();
      return;
    }
    if (state.mode === 'online') {
      this.startPolling();
      if (state.move_count > previousCount && previousCount >= 0 && state.last_move) {
        this.message = `${this.nameOf(state.turn === 'white' ? 'black' : 'white')} played ${state.last_move.san}.`;
      }
    }
  }

  resultText(state: PvpState): string {
    switch (state.result) {
      case '1-0':
        return `Checkmate — ${state.white_name ?? 'White'} wins!`;
      case '0-1':
        return `Checkmate — ${state.black_name ?? 'Black'} wins!`;
      case '1/2-1/2':
        return 'Draw.';
      default:
        return 'Game over.';
    }
  }

  // ------------------------------------------------------------ polling

  private startPolling(): void {
    if (this.pollHandle !== null) {
      return;
    }
    this.pollHandle = setInterval(() => {
      if (!this.loading) {
        this.refresh();
      }
    }, POLL_MS);
  }

  private stopPolling(): void {
    if (this.pollHandle !== null) {
      clearInterval(this.pollHandle);
      this.pollHandle = null;
    }
  }

  // -------------------------------------------------------- orientation

  squareAt(row: number, col: number): string {
    if (this.orientation === 'white') {
      return 'abcdefgh'[col] + String(8 - row);
    }
    return 'abcdefgh'[7 - col] + String(row + 1);
  }

  rankLabel(row: number): number {
    return this.orientation === 'white' ? 8 - row : row + 1;
  }

  fileLabel(col: number): string {
    return this.orientation === 'white' ? 'abcdefgh'[col] : 'abcdefgh'[7 - col];
  }

  private orient(matrix: (string | null)[][]): (string | null)[][] {
    if (this.orientation === 'white') {
      return matrix;
    }
    return matrix
      .slice()
      .reverse()
      .map((row) => row.slice().reverse());
  }

  // ------------------------------------------------------------- board

  private movablePiece(code: string | null): boolean {
    if (!code || !this.state) {
      return false;
    }
    const pieceColor: Color = code === code.toUpperCase() ? 'white' : 'black';
    if (this.state.mode === 'local') {
      return pieceColor === this.state.turn; // whoever is to move plays
    }
    return pieceColor === this.state.your_color && pieceColor === this.state.turn;
  }

  isSelected(row: number, col: number): boolean {
    return this.selected?.row === row && this.selected?.col === col;
  }

  isLegalTarget(row: number, col: number): boolean {
    return this.showLegalMoves && this.legalTargets.includes(this.squareAt(row, col));
  }

  isLastMove(row: number, col: number): boolean {
    const last = this.state?.last_move;
    if (!last) {
      return false;
    }
    const square = this.squareAt(row, col);
    return square === last.from_square || square === last.to_square;
  }

  onSquareClick(row: number, col: number): void {
    if (!this.state || this.state.is_game_over || this.loading || !this.isMyTurn) {
      return;
    }
    this.error = '';
    const code = this.board[row][col];
    const square = this.squareAt(row, col);

    if (this.isSelected(row, col)) {
      this.clearSelection();
      return;
    }

    if (this.movablePiece(code)) {
      this.selected = { row, col };
      this.legalTargets = [];
      if (this.showLegalMoves) {
        this.chess.possibleMoves(square, this.gameId).subscribe({
          next: (response) => (this.legalTargets = response.moves),
        });
      }
      return;
    }

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
    const piece = this.selected ? this.board[this.selected.row][this.selected.col] : null;
    const isPawn = piece?.toLowerCase() === 'p';
    const movingColor = this.state?.turn;
    const promotionRank = movingColor === 'white' ? '8' : '1';
    const promotion = isPawn && to.endsWith(promotionRank) ? 'q' : undefined;

    this.loading = true;
    this.chess
      .pvpMove(this.gameId, from, to, { promotion, token: this.token ?? undefined })
      .subscribe({
        next: (state) => {
          this.loading = false;
          this.clearSelection();
          this.applyState(state);
          if (!state.is_game_over && state.mode === 'local') {
            this.message = `${this.nameOf(state.turn)} to move.`;
          }
        },
        error: (err) => {
          this.loading = false;
          this.clearSelection();
          this.error = err.error?.detail ?? 'Move rejected.';
        },
      });
  }

  clearSelection(): void {
    this.selected = null;
    this.legalTargets = [];
  }

  // -------------------------------------------------------------- misc

  undo(): void {
    if (this.loading || !this.state || this.state.mode !== 'local') {
      return;
    }
    this.loading = true;
    this.chess.pvpUndo(this.gameId).subscribe({
      next: (state) => {
        this.loading = false;
        this.clearSelection();
        this.applyState(state);
        this.message = 'Move taken back.';
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail ?? 'Nothing to undo.';
      },
    });
  }

  copyLink(): void {
    navigator.clipboard?.writeText(this.shareLink).then(() => {
      this.linkCopied = true;
      setTimeout(() => (this.linkCopied = false), 2000);
    });
  }
}
