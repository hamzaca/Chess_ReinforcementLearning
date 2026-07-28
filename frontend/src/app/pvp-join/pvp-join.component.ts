import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { saveSeatToken } from '../pvp-token-store';
import { ChessService } from '../services/chess.service';

@Component({
  selector: 'app-pvp-join',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="join">
      <h2>Join Game #{{ gameId }}</h2>
      <p *ngIf="hostName">You've been invited by <strong>{{ hostName }}</strong>.</p>
      <form (ngSubmit)="join()">
        <label>
          Your name
          <input type="text" [(ngModel)]="name" name="name" placeholder="Player 2" maxlength="40" autofocus />
        </label>
        <p *ngIf="error" class="error">{{ error }}</p>
        <button type="submit" [disabled]="loading">Join & Play</button>
      </form>
    </div>
  `,
  styles: [
    `
      .join { max-width: 420px; }
      form { display: flex; flex-direction: column; gap: 0.9rem; }
      label { display: flex; flex-direction: column; gap: 0.3rem; color: #b9b2a6; }
      input {
        font: inherit; padding: 0.5rem 0.65rem; border-radius: 6px;
        border: 1px solid #6b6257; background: #14120f; color: #eae6df;
      }
      button { align-self: flex-start; }
      .error { color: #e08a7a; margin: 0; }
    `,
  ],
})
export class PvpJoinComponent implements OnInit {
  gameId = 0;
  token = '';
  name = '';
  hostName: string | null = null;
  error = '';
  loading = false;

  constructor(
    private route: ActivatedRoute,
    private chess: ChessService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.gameId = Number(this.route.snapshot.paramMap.get('id'));
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    // Show who invited them (whichever seat already has a name).
    this.chess.pvpState(this.gameId).subscribe({
      next: (state) => (this.hostName = state.white_name ?? state.black_name),
      error: () => (this.error = 'This game could not be found.'),
    });
  }

  join(): void {
    this.error = '';
    this.loading = true;
    this.chess.joinPvpGame(this.gameId, this.token, this.name.trim() || 'Player 2').subscribe({
      next: (joined) => {
        // The server rotated the token — store the fresh one, keep the URL clean.
        saveSeatToken(joined.game_id, joined.token);
        this.router.navigate(['/pvp/play', joined.game_id]);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail ?? 'Could not join this game.';
      },
    });
  }
}
