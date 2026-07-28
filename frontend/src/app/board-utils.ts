/** Shared helpers for rendering a chess position from a FEN string. */

/**
 * Parse the piece-placement field of a FEN into an 8x8 matrix.
 * Row 0 is rank 8 (top of the board from White's point of view),
 * row 7 is rank 1. Cells hold FEN piece letters ('P', 'n', ...) or null.
 */
export function fenToBoard(fen: string): (string | null)[][] {
  const placement = fen.split(' ')[0];
  return placement.split('/').map((row) => {
    const cells: (string | null)[] = [];
    for (const ch of row) {
      if (/\d/.test(ch)) {
        for (let i = 0; i < Number(ch); i++) cells.push(null);
      } else {
        cells.push(ch);
      }
    }
    return cells;
  });
}

/** Algebraic name ('e4') for a board cell addressed by row/col as above. */
export function squareName(row: number, col: number): string {
  return 'abcdefgh'[col] + String(8 - row);
}

const PIECE_NAMES: Record<string, string> = {
  p: 'Pawn',
  n: 'Knight',
  b: 'Bishop',
  r: 'Rook',
  q: 'Queen',
  k: 'King',
};

/** Asset path for a FEN piece letter, e.g. 'P' -> assets/pieces/whitePawn.png */
export function pieceImage(code: string): string {
  const color = code === code.toUpperCase() ? 'white' : 'black';
  return `assets/pieces/${color}${PIECE_NAMES[code.toLowerCase()]}.png`;
}

export function isWhitePiece(code: string | null): boolean {
  return !!code && code === code.toUpperCase();
}
