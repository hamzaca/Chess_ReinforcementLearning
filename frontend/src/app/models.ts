export type Color = 'white' | 'black';

export interface CurrentGame {
  game_id: number;
  fen: string;
  turn: Color;
  pgn: string;
  created: boolean;
  user_color: Color;
  in_check: boolean;
  is_game_over: boolean;
  result: string | null;
  move_count: number;
}

export interface GameState {
  game_id: number;
  fen: string;
  turn: Color;
  pgn: string;
  user_color: Color;
  in_check: boolean;
  is_game_over: boolean;
  result: string | null;
  move_count: number;
}

export interface MovePlayed {
  from_square: string;
  to_square: string;
  san: string;
  player: 'User' | 'Agent';
}

export interface MoveResponse {
  user_move: MovePlayed;
  agent_move: MovePlayed | null;
  fen: string;
  turn: Color;
  pgn: string;
  user_color: Color;
  in_check: boolean;
  is_game_over: boolean;
  result: string | null;
  move_count: number;
}

export interface PossibleMoves {
  square: string;
  moves: string[];
}

export interface GameSummary {
  id: number;
  created_at: string;
  updated_at: string;
  is_completed: boolean;
  result: string | null;
  is_favorite: boolean;
  move_count: number;
  mode: 'agent' | 'local' | 'online';
  white_name: string | null;
  black_name: string | null;
}

// ------------------------------------------------------------ two players

export interface PvpCreateResponse {
  game_id: number;
  mode: 'local' | 'online';
  your_color: Color | null;
  token: string | null;
  join_token: string | null;
}

export interface PvpJoinResponse {
  game_id: number;
  your_color: Color;
  token: string;
}

export interface LastMove {
  from_square: string;
  to_square: string;
  san: string;
}

export interface PvpState {
  game_id: number;
  mode: 'local' | 'online';
  fen: string;
  turn: Color;
  pgn: string;
  in_check: boolean;
  is_game_over: boolean;
  result: string | null;
  move_count: number;
  white_name: string | null;
  black_name: string | null;
  your_color: Color | null;
  opponent_joined: boolean;
  last_move: LastMove | null;
}

export interface FavoriteResponse {
  game_id: number;
  is_favorite: boolean;
}

export interface ReplayMove {
  move_number: number;
  from_square: string;
  to_square: string;
  move_san: string;
  fen_after: string;
}

export interface ReplayResponse {
  game_id: number;
  pgn: string;
  start_fen: string;
  moves: ReplayMove[];
}

export interface LogEntry {
  id: number;
  game_id: number | null;
  timestamp: string;
  action_type: string;
  details: Record<string, unknown>;
}
