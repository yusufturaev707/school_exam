/** Dizayn: natija ekrani konfettisi (bd-confetti) — faqat harakatga ruxsat boʻlsa tushadi. */
const COLORS = ['#ffc94a', '#5b5bd6', '#d23f78', '#16895a', '#2575c9', '#e8590c'];

export function Confetti() {
  return (
    <div className="bd-confetti" aria-hidden="true">
      {Array.from({ length: 22 }, (_, i) => (
        <i
          key={i}
          style={{
            left: `${((i * 37 + 8) % 100).toFixed(0)}%`,
            top: (i * 53) % 160,
            background: COLORS[i % COLORS.length],
            animationDelay: `${-((i * 0.37) % 2.8).toFixed(2)}s`,
            transform: `rotate(${i * 33}deg)`,
          }}
        />
      ))}
    </div>
  );
}
