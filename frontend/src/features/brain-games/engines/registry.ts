import { lazy, type ComponentType, type LazyExoticComponent } from 'react';
import type { GameContent, GameKind } from '../types';
import type { GameEngineProps } from './types';

type Engine = LazyExoticComponent<ComponentType<GameEngineProps<GameContent>>>;
const engine = (load: () => Promise<{ default: ComponentType<never> }>) => lazy(load as () => Promise<{ default: ComponentType<GameEngineProps<GameContent>> }>);

/**
 * One independent, lazily loaded engine per game kind: a student downloads only the game they play.
 * Future games (Odd One Out, Quick Math, Maze, Sudoku, Word Search…) register here.
 */
export const ENGINES: Partial<Record<GameKind, Engine>> = {
  memory: engine(() => import('./memory/MemoryGame')),
  'missing-number': engine(() => import('./missing-number/MissingNumberGame')),
  pattern: engine(() => import('./pattern-master/PatternGame')),
};
