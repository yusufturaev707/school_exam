import { create } from 'zustand';

export type ToastTone = 'info' | 'success' | 'warning';

export interface Toast {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastState {
  toasts: Toast[];
  show: (message: string, tone?: ToastTone, durationMs?: number) => void;
  dismiss: (id: number) => void;
}

let nextId = 1;

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  show: (message, tone = 'info', durationMs = 4000) => {
    const id = nextId++;
    set((s) => ({ toasts: [...s.toasts.slice(-2), { id, message, tone }] }));
    window.setTimeout(() => get().dismiss(id), durationMs);
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = (message: string, tone?: ToastTone, durationMs?: number) => useToastStore.getState().show(message, tone, durationMs);
