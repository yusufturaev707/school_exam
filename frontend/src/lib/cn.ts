type ClassValue = string | false | null | undefined | 0;

/** Tiny className joiner (avoids pulling in clsx for a one-liner). */
export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ');
}
