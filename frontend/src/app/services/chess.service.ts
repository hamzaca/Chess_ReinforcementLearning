import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  CurrentGame,
  FavoriteResponse,
  GameState,
  GameSummary,
  LogEntry,
  MoveResponse,
  PossibleMoves,
  PvpCreateResponse,
  PvpJoinResponse,
  PvpState,
  ReplayResponse,
} from '../models';

/**
 * Thin typed wrapper over the FastAPI backend. The base URL is relative:
 * the Angular dev server proxies /api to localhost:8000 (proxy.conf.json),
 * and in Docker nginx proxies /api to the backend container.
 */
@Injectable({ providedIn: 'root' })
export class ChessService {
  private readonly base = '/api';

  constructor(private http: HttpClient) {}

  getCurrentGame(): Observable<CurrentGame> {
    return this.http.get<CurrentGame>(`${this.base}/games/current`);
  }

  newGame(userColor?: 'white' | 'black' | 'random'): Observable<CurrentGame> {
    return this.http.post<CurrentGame>(`${this.base}/games/new`, {
      user_color: userColor ?? null,
    });
  }

  /** Take back the user's last move; pass a large ply count to rewind to the start. */
  undo(plies?: number): Observable<GameState> {
    return this.http.post<GameState>(`${this.base}/undo`, { plies: plies ?? null });
  }

  listGames(favoritesOnly = false): Observable<GameSummary[]> {
    const params = new HttpParams().set('favorites_only', favoritesOnly);
    return this.http.get<GameSummary[]>(`${this.base}/games`, { params });
  }

  toggleFavorite(gameId: number): Observable<FavoriteResponse> {
    return this.http.post<FavoriteResponse>(`${this.base}/games/${gameId}/favorite`, {});
  }

  getReplay(gameId: number): Observable<ReplayResponse> {
    return this.http.get<ReplayResponse>(`${this.base}/games/${gameId}/replay`);
  }

  getGameState(): Observable<GameState> {
    return this.http.get<GameState>(`${this.base}/game-state`);
  }

  makeMove(fromSquare: string, toSquare: string, promotion?: string): Observable<MoveResponse> {
    return this.http.post<MoveResponse>(`${this.base}/move`, {
      from_square: fromSquare,
      to_square: toSquare,
      promotion: promotion ?? null,
    });
  }

  possibleMoves(square: string, gameId?: number): Observable<PossibleMoves> {
    return this.http.post<PossibleMoves>(`${this.base}/possible-moves`, {
      square,
      game_id: gameId ?? null,
    });
  }

  // ---------------------------------------------------------- two players

  createPvpGame(payload: {
    mode: 'local' | 'online';
    white_name?: string;
    black_name?: string;
    creator_name?: string;
    creator_color?: 'white' | 'black' | 'random';
  }): Observable<PvpCreateResponse> {
    return this.http.post<PvpCreateResponse>(`${this.base}/pvp/games`, payload);
  }

  joinPvpGame(gameId: number, token: string, name: string): Observable<PvpJoinResponse> {
    return this.http.post<PvpJoinResponse>(`${this.base}/pvp/games/${gameId}/join`, {
      token,
      name,
    });
  }

  // Security: the seat token travels in a header (never in the URL or body),
  // keeping it out of browser history, access logs and Referer headers.
  private tokenHeaders(token?: string): { headers?: Record<string, string> } {
    return token ? { headers: { 'X-Player-Token': token } } : {};
  }

  pvpState(gameId: number, token?: string): Observable<PvpState> {
    return this.http.get<PvpState>(
      `${this.base}/pvp/games/${gameId}/state`,
      this.tokenHeaders(token),
    );
  }

  pvpMove(
    gameId: number,
    fromSquare: string,
    toSquare: string,
    options: { promotion?: string; token?: string } = {},
  ): Observable<PvpState> {
    return this.http.post<PvpState>(
      `${this.base}/pvp/games/${gameId}/move`,
      {
        from_square: fromSquare,
        to_square: toSquare,
        promotion: options.promotion ?? null,
      },
      this.tokenHeaders(options.token),
    );
  }

  pvpUndo(gameId: number): Observable<PvpState> {
    return this.http.post<PvpState>(`${this.base}/pvp/games/${gameId}/undo`, {});
  }

  getLogs(gameId?: number): Observable<LogEntry[]> {
    let params = new HttpParams();
    if (gameId !== undefined) {
      params = params.set('game_id', gameId);
    }
    return this.http.get<LogEntry[]>(`${this.base}/logs/`, { params });
  }
}
