import { describe, expect, it } from 'vitest';
import { computeClockOffset, formatClock, remainingMs } from './time';

describe('time utils', () => {
  it('computes offset from the round-trip midpoint', () => {
    // Device sent at 1000, received at 1200 → midpoint 1100. Server said 6100 → device is 5s behind.
    expect(computeClockOffset(new Date(6100).toISOString(), 1000, 1200)).toBe(5000);
  });

  it('uses the server deadline even if the device clock is wrong', () => {
    const expiresAt = new Date(60 * 60_000).toISOString(); // server deadline at t = 60min
    // Device thinks it's t = 0, but it's 10 minutes slow (offset +10min) → 50 minutes remain.
    expect(remainingMs(expiresAt, 10 * 60_000, 0)).toBe(50 * 60_000);
  });

  it('never returns negative remaining time', () => {
    expect(remainingMs(new Date(1000).toISOString(), 0, 5000)).toBe(0);
  });

  it('formats the countdown, rounding up partial seconds', () => {
    expect(formatClock(60 * 60_000)).toBe('60:00');
    expect(formatClock(59_001)).toBe('01:00');
    expect(formatClock(500)).toBe('00:01');
    expect(formatClock(0)).toBe('00:00');
  });
});
