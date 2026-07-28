/**
 * Seat/invite tokens live in sessionStorage, NOT in the URL — keeping them
 * out of the address bar, browser history and copy-pasted links. They are
 * per-tab and vanish when the tab closes.
 */

const seatKey = (gameId: number) => `pvp-token-${gameId}`;
const shareKey = (gameId: number) => `pvp-share-${gameId}`;

export function saveSeatToken(gameId: number, token: string): void {
  sessionStorage.setItem(seatKey(gameId), token);
}

export function getSeatToken(gameId: number): string | null {
  return sessionStorage.getItem(seatKey(gameId));
}

export function saveShareToken(gameId: number, token: string): void {
  sessionStorage.setItem(shareKey(gameId), token);
}

export function getShareToken(gameId: number): string | null {
  return sessionStorage.getItem(shareKey(gameId));
}
