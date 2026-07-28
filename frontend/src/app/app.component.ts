import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <nav class="topbar">
      <span class="brand">&#9812; Chess AI</span>
      <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Play vs Agent</a>
      <a routerLink="/pvp" routerLinkActive="active">Two Players</a>
      <a routerLink="/library" routerLinkActive="active">Game Library</a>
    </nav>
    <main>
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [
    `
      .topbar {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        padding: 0.75rem 1.5rem;
        background: #14120f;
        border-bottom: 1px solid #3c362f;
      }
      .brand {
        font-weight: 700;
        font-size: 1.15rem;
        color: #d7b36a;
        margin-right: 1rem;
      }
      .topbar a {
        text-decoration: none;
        color: #b9b2a6;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
      }
      .topbar a.active {
        color: #eae6df;
        background: #2c2823;
      }
      main {
        padding: 1.5rem;
        max-width: 1100px;
        margin: 0 auto;
      }
    `,
  ],
})
export class AppComponent {}
