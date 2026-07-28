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
        padding: 0.8rem 1.75rem;
        background: var(--panel);
        border-bottom: 1px solid var(--border);
        box-shadow: 0 2px 10px rgba(96, 84, 59, 0.06);
        position: sticky;
        top: 0;
        z-index: 10;
      }
      .brand {
        font-weight: 700;
        font-size: 1.15rem;
        color: var(--accent);
        margin-right: 1rem;
      }
      .topbar a {
        text-decoration: none;
        color: var(--muted);
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        transition: background 0.15s ease, color 0.15s ease;
      }
      .topbar a:hover {
        color: var(--text);
        background: var(--panel-soft);
      }
      .topbar a.active {
        color: var(--green-dark);
        background: var(--green-soft);
        font-weight: 600;
      }
      main {
        padding: 1.75rem 1.5rem;
        max-width: 1360px;
        margin: 0 auto;
      }
    `,
  ],
})
export class AppComponent {}
