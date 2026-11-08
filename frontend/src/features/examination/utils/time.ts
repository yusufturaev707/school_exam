/**
 * Clock helpers. The backend deadline is the single source of truth; the device clock is only
 * used for ticking, corrected by the measured offset between server and device.
 */

/**
 * Offset = serverTime − device time at the moment the server produced the response.
 * We assume the server stamped the response halfway through the round trip.
 */
export function computeClockOffset(serverTimeIso: string, sentAtMs: number, receivedAtMs: number): number {
  const serverMs = Date.parse(serverTimeIso);
  if (Number.isNaN(serverMs)) return 0;
  const midpoint = sentAtMs + (receivedAtMs - sentAtMs) / 2;
  return Math.round(serverMs - midpoint);
}

export function serverNow(clockOffsetMs: number, deviceNowMs: number = Date.now()): number {
  return deviceNowMs + clockOffsetMs;
}

export function remainingMs(expiresAtIso: string, clockOffsetMs: number, deviceNowMs: number = Date.now()): number {
  const deadline = Date.parse(expiresAtIso);
  if (Number.isNaN(deadline)) return 0;
  return Math.max(0, deadline - serverNow(clockOffsetMs, deviceNowMs));
}

/** 3599000 → "59:59", 3600000 → "60:00". Rounds up so the clock never shows 00:00 while time remains. */
export function formatClock(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/** Spoken form for screen readers: "12 daqiqa 5 soniya". */
export function spokenClock(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds} soniya`;
  return seconds === 0 ? `${minutes} daqiqa` : `${minutes} daqiqa ${seconds} soniya`;
}
