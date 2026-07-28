import { Routes } from '@angular/router';

import { ChessBoardComponent } from './chess-board/chess-board.component';
import { GameLibraryComponent } from './game-library/game-library.component';
import { PvpBoardComponent } from './pvp-board/pvp-board.component';
import { PvpJoinComponent } from './pvp-join/pvp-join.component';
import { PvpSetupComponent } from './pvp-setup/pvp-setup.component';
import { ReplayViewerComponent } from './replay-viewer/replay-viewer.component';

export const routes: Routes = [
  { path: '', component: ChessBoardComponent },
  { path: 'pvp', component: PvpSetupComponent },
  { path: 'pvp/play/:id', component: PvpBoardComponent },
  { path: 'join/:id/:token', component: PvpJoinComponent },
  { path: 'library', component: GameLibraryComponent },
  { path: 'replay/:id', component: ReplayViewerComponent },
  { path: '**', redirectTo: '' },
];
