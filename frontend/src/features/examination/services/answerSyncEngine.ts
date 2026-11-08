/**
 * Reliable autosave for exam answers — framework-agnostic so it can be unit-tested.
 *
 * Guarantees:
 *  - Every selection is queued and sent; the newest choice per question always wins
 *    (monotonic `seq`, and the backend ignores lower seqs).
 *  - Network / 5xx failures retry with exponential backoff; nothing is dropped.
 *  - "Fatal" errors (attempt already closed, forbidden) stop retrying and are reported.
 *  - `flush()` lets the caller wait until everything is on the server (used before submit).
 */

export interface PendingAnswer {
  questionId: string;
  optionIds: string[];
  seq: number;
}

export type SyncPhase = 'idle' | 'saving' | 'retrying' | 'blocked';

export interface SyncState {
  phase: SyncPhase;
  pendingCount: number;
  lastSavedAt: number | null;
}

export interface AnswerSyncOptions {
  save: (answer: PendingAnswer) => Promise<void>;
  isFatal: (error: unknown) => boolean;
  onState?: (state: SyncState) => void;
  onPendingChange?: (pending: PendingAnswer[]) => void;
  onFatal?: (error: unknown) => void;
  initialPending?: PendingAnswer[];
  now?: () => number;
  setTimer?: (fn: () => void, ms: number) => unknown;
  clearTimer?: (handle: unknown) => void;
  maxBackoffMs?: number;
}

export class AnswerSyncEngine {
  private readonly pending = new Map<string, PendingAnswer>();
  private readonly opts: Required<Pick<AnswerSyncOptions, 'now' | 'setTimer' | 'clearTimer' | 'maxBackoffMs'>> & AnswerSyncOptions;
  private lastSeq = 0;
  private inFlight: Promise<boolean> | null = null;
  private rerun = false;
  private failures = 0;
  private retryHandle: unknown = null;
  private blocked = false;
  private disposed = false;
  private lastSavedAt: number | null = null;

  constructor(options: AnswerSyncOptions) {
    this.opts = {
      now: () => Date.now(),
      setTimer: (fn, ms) => setTimeout(fn, ms),
      clearTimer: (h) => clearTimeout(h as ReturnType<typeof setTimeout>),
      maxBackoffMs: 15_000,
      ...options,
    };
    for (const p of options.initialPending ?? []) {
      this.pending.set(p.questionId, p);
      this.lastSeq = Math.max(this.lastSeq, p.seq);
    }
  }

  get state(): SyncState {
    const phase: SyncPhase = this.blocked ? 'blocked' : this.inFlight ? 'saving' : this.retryHandle !== null ? 'retrying' : 'idle';
    return { phase, pendingCount: this.pending.size, lastSavedAt: this.lastSavedAt };
  }

  getPending(): PendingAnswer[] {
    return [...this.pending.values()];
  }

  /** Monotonic across page reloads too, because it is anchored to wall-clock ms. */
  private nextSeq(): number {
    this.lastSeq = Math.max(this.lastSeq + 1, this.opts.now());
    return this.lastSeq;
  }

  enqueue(questionId: string, optionIds: string[]): void {
    if (this.disposed || this.blocked) return;
    this.pending.set(questionId, { questionId, optionIds: [...optionIds], seq: this.nextSeq() });
    this.opts.onPendingChange?.(this.getPending());
    this.emit();
    void this.flush();
  }

  /** Resolves true when the queue is empty, false if something is still unsaved. */
  flush(): Promise<boolean> {
    if (this.disposed || this.blocked) return Promise.resolve(this.pending.size === 0);
    if (this.inFlight) {
      this.rerun = true;
      return this.inFlight;
    }
    if (this.retryHandle !== null) {
      this.opts.clearTimer(this.retryHandle);
      this.retryHandle = null;
    }
    this.inFlight = this.run().finally(() => {
      this.inFlight = null;
      this.emit();
    });
    this.emit();
    return this.inFlight;
  }

  private async run(): Promise<boolean> {
    do {
      this.rerun = false;
      const batch = this.getPending();
      if (batch.length === 0) return true;

      const results = await Promise.allSettled(batch.map((item) => this.opts.save(item)));
      if (this.disposed) return false;

      let retryable = false;
      results.forEach((result, i) => {
        const item = batch[i]!;
        if (result.status === 'fulfilled') {
          // Only clear if no newer choice was queued for this question meanwhile.
          if (this.pending.get(item.questionId)?.seq === item.seq) this.pending.delete(item.questionId);
          this.lastSavedAt = this.opts.now();
        } else if (this.opts.isFatal(result.reason)) {
          if (!this.blocked) {
            this.blocked = true;
            this.opts.onFatal?.(result.reason);
          }
        } else {
          retryable = true;
        }
      });
      this.opts.onPendingChange?.(this.getPending());

      if (this.blocked) return false;
      if (retryable) {
        this.scheduleRetry();
        return false;
      }
      this.failures = 0;
    } while (this.rerun || this.pending.size > 0);
    return true;
  }

  private scheduleRetry(): void {
    this.failures += 1;
    const base = Math.min(this.opts.maxBackoffMs, 1000 * 2 ** (this.failures - 1));
    const delay = base * (0.8 + Math.random() * 0.4);
    this.retryHandle = this.opts.setTimer(() => {
      this.retryHandle = null;
      void this.flush();
    }, delay);
  }

  /** Stops all work (e.g. once the attempt is finalised). Pending items stay readable. */
  dispose(): void {
    this.disposed = true;
    if (this.retryHandle !== null) this.opts.clearTimer(this.retryHandle);
    this.retryHandle = null;
  }

  private emit(): void {
    this.opts.onState?.(this.state);
  }
}
