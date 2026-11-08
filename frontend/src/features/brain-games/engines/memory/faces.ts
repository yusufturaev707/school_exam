import { Apple, Bird, Cat, Fish, Flower2, Moon, Rocket, Star, Sun, TreePine, type LucideIcon } from 'lucide-react';

/** Card faces by backend id. Unknown ids fall back to a star so a new face never breaks the board. */
export const MEMORY_FACES: Record<string, { icon: LucideIcon; label: string; color: string; bg: string }> = {
  apple: { icon: Apple, label: 'olma', color: '#D9473F', bg: '#FDECEB' },
  cat: { icon: Cat, label: 'mushuk', color: '#C46A12', bg: '#FFF1DE' },
  fish: { icon: Fish, label: 'baliq', color: '#1D6796', bg: '#E2F2FC' },
  rocket: { icon: Rocket, label: 'raketa', color: '#6343C4', bg: '#EFE9FF' },
  sun: { icon: Sun, label: 'quyosh', color: '#B07A00', bg: '#FFF6D6' },
  moon: { icon: Moon, label: 'oy', color: '#3D4FC4', bg: '#E9EEFF' },
  bird: { icon: Bird, label: 'qush', color: '#17776A', bg: '#E5F4F0' },
  flower: { icon: Flower2, label: 'gul', color: '#A93A6C', bg: '#F9E9F1' },
  star: { icon: Star, label: 'yulduz', color: '#B07A00', bg: '#FDF3DE' },
  tree: { icon: TreePine, label: 'archa', color: '#23774F', bg: '#E3F5EC' },
};
export const faceOf = (id: string) => MEMORY_FACES[id] ?? MEMORY_FACES.star!;
