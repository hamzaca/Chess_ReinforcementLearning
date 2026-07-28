import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { fenToBoard, pieceImage } from '../board-utils';
import { ReplayResponse } from '../models';
import { ChessService } from '../services/chess.service';

@Component({
  selector: 'app-replay-viewer',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './replay-viewer.component.html',
  styleUrls: ['./replay-viewer.component.css'],
})
export class ReplayViewerComponent implements OnInit {
  replay: ReplayResponse | null = null;
  board: (string | null)[][] = [];

  /** -1 = start position; otherwise index into replay.moves. */
  index = -1;
  error = '';

  readonly pieceImage = pieceImage;

  constructor(
    private route: ActivatedRoute,
    private chess: ChessService,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.chess.getReplay(id).subscribe({
      next: (replay) => {
        this.replay = replay;
        this.render();
      },
      error: () => (this.error = 'Could not load this game.'),
    });
  }

  render(): void {
    if (!this.replay) {
      return;
    }
    const fen =
      this.index < 0 ? this.replay.start_fen : this.replay.moves[this.index].fen_after;
    this.board = fenToBoard(fen);
  }

  next(): void {
    if (this.replay && this.index < this.replay.moves.length - 1) {
      this.index++;
      this.render();
    }
  }

  previous(): void {
    if (this.index > -1) {
      this.index--;
      this.render();
    }
  }

  toStart(): void {
    this.index = -1;
    this.render();
  }

  toEnd(): void {
    if (this.replay) {
      this.index = this.replay.moves.length - 1;
      this.render();
    }
  }

  get currentLabel(): string {
    if (!this.replay || this.index < 0) {
      return 'Start position';
    }
    const move = this.replay.moves[this.index];
    const number = Math.ceil(move.move_number / 2);
    const side = move.move_number % 2 === 1 ? 'White' : 'Black';
    return `${number}. ${side}: ${move.move_san}`;
  }
}
