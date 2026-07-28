import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { GameSummary } from '../models';
import { ChessService } from '../services/chess.service';

@Component({
  selector: 'app-game-library',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './game-library.component.html',
  styleUrls: ['./game-library.component.css'],
})
export class GameLibraryComponent implements OnInit {
  games: GameSummary[] = [];
  favoritesOnly = false;
  error = '';

  constructor(
    private chess: ChessService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.chess.listGames(this.favoritesOnly).subscribe({
      next: (games) => (this.games = games),
      error: () => (this.error = 'Could not load games.'),
    });
  }

  toggleFavorite(game: GameSummary): void {
    this.chess.toggleFavorite(game.id).subscribe({
      next: (response) => {
        game.is_favorite = response.is_favorite;
        if (this.favoritesOnly && !response.is_favorite) {
          this.load();
        }
      },
    });
  }

  startNewGame(): void {
    this.chess.newGame().subscribe({
      next: () => this.router.navigate(['/']),
      error: () => (this.error = 'Could not start a new game.'),
    });
  }

  playersOf(game: GameSummary): string {
    if (game.mode === 'agent') {
      return 'You vs Agent';
    }
    const white = game.white_name ?? 'White';
    const black = game.black_name ?? '(open seat)';
    return `${white} vs ${black}`;
  }

  statusOf(game: GameSummary): string {
    if (!game.is_completed) {
      return 'In progress';
    }
    switch (game.result) {
      case '1-0':
        return 'White won';
      case '0-1':
        return 'Black won';
      case '1/2-1/2':
        return 'Draw';
      default:
        return 'Abandoned';
    }
  }
}
