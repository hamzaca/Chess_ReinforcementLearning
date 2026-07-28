import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { saveSeatToken, saveShareToken } from '../pvp-token-store';
import { ChessService } from '../services/chess.service';

@Component({
  selector: 'app-pvp-setup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pvp-setup.component.html',
  styleUrls: ['./pvp-setup.component.css'],
})
export class PvpSetupComponent {
  mode: 'local' | 'online' = 'local';

  // local
  whiteName = '';
  blackName = '';

  // online
  creatorName = '';
  creatorColor: 'white' | 'black' | 'random' = 'random';

  loading = false;
  error = '';

  constructor(
    private chess: ChessService,
    private router: Router,
  ) {}

  start(): void {
    this.error = '';
    this.loading = true;

    if (this.mode === 'local') {
      this.chess
        .createPvpGame({
          mode: 'local',
          white_name: this.whiteName.trim() || 'White',
          black_name: this.blackName.trim() || 'Black',
        })
        .subscribe({
          next: (game) => this.router.navigate(['/pvp/play', game.game_id]),
          error: () => {
            this.loading = false;
            this.error = 'Could not create the game.';
          },
        });
      return;
    }

    this.chess
      .createPvpGame({
        mode: 'online',
        creator_name: this.creatorName.trim() || 'Player 1',
        creator_color: this.creatorColor,
      })
      .subscribe({
        next: (game) => {
          // Tokens go to sessionStorage, never into the URL.
          if (game.token) {
            saveSeatToken(game.game_id, game.token);
          }
          if (game.join_token) {
            saveShareToken(game.game_id, game.join_token);
          }
          this.router.navigate(['/pvp/play', game.game_id]);
        },
        error: () => {
          this.loading = false;
          this.error = 'Could not create the game.';
        },
      });
  }
}
