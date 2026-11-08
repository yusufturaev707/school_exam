/* @ds-bundle: {"format":4,"namespace":"Bilimdon","components":[{"name":"Mascot"},{"name":"Icon"},{"name":"Button"},{"name":"Chip"},{"name":"Card"},{"name":"SubjectCard"},{"name":"Progress"},{"name":"Badge"},{"name":"AppHeader"},{"name":"BottomNav"},{"name":"ExamHero"},{"name":"MissionCard"},{"name":"QuestionCard"},{"name":"GameCard"},{"name":"StatTile"}]} */
(function () {
  /* Duotone ikonkalar: d = yarim shaffof toʻldirish, s = 2px chiziq. 24×24 setka, Phosphor Duotone uslubida. */
  var I = {
    home: { d: 'M6 9.4 12 4.6l6 4.8V20h-4v-5.5h-4V20H6z', s: 'M3.5 11 12 4l8.5 7M6 9.4V19a1 1 0 0 0 1 1h3v-5.5h4V20h3a1 1 0 0 0 1-1V9.4' },
    exam: { d: 'M5.5 6.5h13v14h-13z', s: 'M9 3.5h6v3H9zM8.5 5H7a1.5 1.5 0 0 0-1.5 1.5v13A1.5 1.5 0 0 0 7 21h10a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 17 5h-1.5M8.8 14l2.4 2.4 4.2-4.6' },
    game: { d: 'M7.6 7h8.8a4.4 4.4 0 0 1 4.3 5.3l-.9 4.8a2.4 2.4 0 0 1-4.2 1.2L14 16.5h-4l-1.6 1.8a2.4 2.4 0 0 1-4.2-1.2l-.9-4.8A4.4 4.4 0 0 1 7.6 7z', s: 'M7.6 7h8.8a4.4 4.4 0 0 1 4.3 5.3l-.9 4.8a2.4 2.4 0 0 1-4.2 1.2L14 16.5h-4l-1.6 1.8a2.4 2.4 0 0 1-4.2-1.2l-.9-4.8A4.4 4.4 0 0 1 7.6 7zM8 10v3.6M6.2 11.8h3.6M15.2 10.6h.01M17.2 12.8h.01' },
    chart: { d: 'M5.5 11h3v6h-3zM10.5 6h3v11h-3zM15.5 9h3v8h-3z', s: 'M4 20h16M5.5 11h3v6h-3zM10.5 6h3v11h-3zM15.5 9h3v8h-3z' },
    user: { d: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20a7.5 7.5 0 0 1 15 0z', s: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20a7.5 7.5 0 0 1 15 0' },
    fire: { d: 'M12 21c3.9 0 6.5-2.6 6.5-6.3 0-3.6-2.4-6-4.4-8.7-.4 2.2-1.4 3.4-2.6 4-.3-2.6-1.6-4.8-3.5-6.5C8.2 7.5 5.5 10 5.5 14.7 5.5 18.4 8.1 21 12 21z', s: 'M12 21c3.9 0 6.5-2.6 6.5-6.3 0-3.6-2.4-6-4.4-8.7-.4 2.2-1.4 3.4-2.6 4-.3-2.6-1.6-4.8-3.5-6.5C8.2 7.5 5.5 10 5.5 14.7 5.5 18.4 8.1 21 12 21zM12 21c-1.7 0-3-1.2-3-3 0-1.9 1.6-3 3-4.8 1.4 1.8 3 2.9 3 4.8 0 1.8-1.3 3-3 3z' },
    star: { d: 'M12 3.5l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z', s: 'M12 3.5l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z' },
    clock: { d: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17z', s: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM12 7.5V12l3 2' },
    list: { d: 'M3 5h3v4H3zM3 10h3v4H3zM3 15h3v4H3z', s: 'M9.5 7H20M9.5 12H20M9.5 17H20M4.5 7h.01M4.5 12h.01M4.5 17h.01' },
    sigma: { d: 'M6.5 4.5H17v3l-4.5 4.5L17 16.5v3H6.5l6-7.5z', s: 'M17 6.5v-2H6.5l6 7.5-6 7.5H17v-2' },
    puzzle: { d: 'M5 8h3.2a2.2 2.2 0 1 1 4.1 0H16v3.4a2.2 2.2 0 1 1 0 4.2V19h-3.6a2.2 2.2 0 1 0-4.2 0H5v-3.6a2.2 2.2 0 1 0 0-4.2z', s: 'M5 8h3.2a2.2 2.2 0 1 1 4.1 0H16v3.4a2.2 2.2 0 1 1 0 4.2V19h-3.6a2.2 2.2 0 1 0-4.2 0H5v-3.6a2.2 2.2 0 1 0 0-4.2z' },
    book: { d: 'M12 6.5C10 5 7.5 4.5 4 4.5v13c3.5 0 6 .5 8 2 2-1.5 4.5-2 8-2v-13c-3.5 0-6 .5-8 2z', s: 'M12 6.5C10 5 7.5 4.5 4 4.5v13c3.5 0 6 .5 8 2 2-1.5 4.5-2 8-2v-13c-3.5 0-6 .5-8 2zM12 6.5v13' },
    brain: { d: 'M12 5.3A2.6 2.6 0 0 0 7 6.5 2.8 2.8 0 0 0 4.8 10a3 3 0 0 0 .6 4.6A3 3 0 0 0 8.6 19 2.6 2.6 0 0 0 12 19.6zM12 5.3A2.6 2.6 0 0 1 17 6.5a2.8 2.8 0 0 1 2.2 3.5 3 3 0 0 1-.6 4.6 3 3 0 0 1-3.2 4.4 2.6 2.6 0 0 1-3.4.6z', s: 'M12 5.3A2.6 2.6 0 0 0 7 6.5 2.8 2.8 0 0 0 4.8 10a3 3 0 0 0 .6 4.6A3 3 0 0 0 8.6 19 2.6 2.6 0 0 0 12 19.6V5.3zM12 5.3A2.6 2.6 0 0 1 17 6.5a2.8 2.8 0 0 1 2.2 3.5 3 3 0 0 1-.6 4.6 3 3 0 0 1-3.2 4.4 2.6 2.6 0 0 1-3.4.6M8.5 10.5c1.2 0 2 .8 2 2M15.5 10.5c-1.2 0-2 .8-2 2' },
    eye: { d: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', s: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z' },
    compass: { d: 'M15.5 8.5l-2 5-5 2 2-5z', s: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM15.5 8.5l-2 5-5 2 2-5z' },
    text: { d: 'M5 5h14v2.5H5z', s: 'M5 7.5V5h14v2.5M12 5v14M9 19h6' },
    trophy: { d: 'M8 4h8v5a4 4 0 0 1-8 0z', s: 'M8 4h8v5a4 4 0 0 1-8 0zM8 6H5v1.5a3 3 0 0 0 3 3M16 6h3v1.5a3 3 0 0 1-3 3M12 13v3.5M9.5 20h5l-.5-3.5h-4z' },
    lock: { d: 'M6.5 10.5h11a1.5 1.5 0 0 1 1.5 1.5v6.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 18.5V12a1.5 1.5 0 0 1 1.5-1.5z', s: 'M6.5 10.5h11a1.5 1.5 0 0 1 1.5 1.5v6.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 18.5V12a1.5 1.5 0 0 1 1.5-1.5zM8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5' },
    check: { d: '', s: 'M5 12.5l4.5 4.5L19 7.5' },
    x: { d: '', s: 'M6.5 6.5l11 11M17.5 6.5l-11 11' },
    arrowR: { d: '', s: 'M5 12h14M13 6l6 6-6 6' },
    arrowL: { d: '', s: 'M19 12H5M11 6l-6 6 6 6' },
    chevR: { d: '', s: 'M9.5 6l6 6-6 6' },
    play: { d: 'M8 5.5v13l10.5-6.5z', s: 'M8 5.5v13l10.5-6.5z' },
    bolt: { d: 'M13 3 5 13.5h6L10 21l8-10.5h-6z', s: 'M13 3 5 13.5h6L10 21l8-10.5h-6z' },
    bulb: { d: 'M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V17h5v-1.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z', s: 'M9.5 17.5h5M10.3 21h3.4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V17h5v-1.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z' },
    target: { d: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z', s: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 13.2a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4z' },
    history: { d: 'M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16z', s: 'M4 12a8 8 0 1 0 2.3-5.6M4 4.5V8h3.5M12 8v4l2.5 2' },
    help: { d: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17z', s: 'M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17zM9.6 9.5a2.5 2.5 0 0 1 4.8.8c0 1.7-2.4 2-2.4 3.4M12 16.8h.01' },
    shield: { d: 'M12 3.5 5 6v5.5c0 4.3 3 7.6 7 9 4-1.4 7-4.7 7-9V6z', s: 'M12 3.5 5 6v5.5c0 4.3 3 7.6 7 9 4-1.4 7-4.7 7-9V6zM9 12l2 2 4-4' },
    logout: { d: '', s: 'M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M10 16l-4-4 4-4M6 12h10' },
    flag: { d: 'M5 4h12l-2.5 4L17 12H5z', s: 'M5 21V4M5 4h12l-2.5 4L17 12H5' },
    sparkle: { d: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z', s: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18.5 16v4M16.5 18h4' },
    calendar: { d: 'M4.5 6.5h15V10h-15z', s: 'M6 5h12a1.5 1.5 0 0 1 1.5 1.5v12A1.5 1.5 0 0 1 18 20H6a1.5 1.5 0 0 1-1.5-1.5v-12A1.5 1.5 0 0 1 6 5zM4.5 10h15M8.5 3.5v3M15.5 3.5v3' },
    calc: { d: 'M7.5 4h9v5h-9z', s: 'M7 3.5h10a1.5 1.5 0 0 1 1.5 1.5v14a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5zM8 7h8M8.5 12h.01M12 12h.01M15.5 12h.01M8.5 16h.01M12 16h.01M15.5 16h.01' },
    sun: { d: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', s: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4' },
    moon: { d: 'M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z', s: 'M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z' },
    bell: { d: 'M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z', s: 'M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15zM10 20.5h4' },
    retry: { d: '', s: 'M4.5 12a7.5 7.5 0 1 0 2.2-5.3M4.5 4.5V8H8' },
    grid: { d: 'M4.5 4.5h6v6h-6zM13.5 13.5h6v6h-6z', s: 'M4.5 4.5h6v6h-6zM13.5 4.5h6v6h-6zM4.5 13.5h6v6h-6zM13.5 13.5h6v6h-6z' },
    users: { d: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z', s: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M15.5 4.3a3.5 3.5 0 0 1 0 6.4M18 14a6.5 6.5 0 0 1 3.5 6' }
  };
  function icon(name, size) {
    var g = I[name]; if (!g) return '';
    var px = size || 20;
    return '<svg class="bd-svg" width="' + px + '" height="' + px + '" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
      (g.d ? '<path d="' + g.d + '" fill="currentColor" opacity=".22"/>' : '') +
      '<path d="' + g.s + '" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  /* Maskot: yashil kitob. Kayfiyatlar: salom, xursand, oylayapti, ishora, hayron. */
  var M = { body: '#2e8b74', spine: '#1f6f5f', page: '#fff6df', mark: '#ffc94a', ink: '#11302a', cheek: '#ff9fae' };
  function eye(cx, cy, dx, dy) {
    return '<circle cx="' + cx + '" cy="' + cy + '" r="11" fill="#fff"/>' +
      '<circle cx="' + (cx + dx) + '" cy="' + (cy + dy) + '" r="5.6" fill="' + M.ink + '"/>' +
      '<circle cx="' + (cx + dx + 2) + '" cy="' + (cy + dy - 2.2) + '" r="1.9" fill="#fff"/>';
  }
  function arm(d, cls) { return '<path d="' + d + '" stroke="' + M.ink + '" stroke-width="8.5" stroke-linecap="round" fill="none"/><path d="' + d + '" stroke="' + M.body + '" stroke-width="5" stroke-linecap="round" fill="none"/>'; }
  function hand(x, y, cls) { return '<circle class="' + (cls || '') + '" cx="' + x + '" cy="' + y + '" r="5" fill="' + M.body + '" stroke="' + M.ink + '" stroke-width="2"/>'; }
  function mascot(mood, size) {
    mood = mood || 'salom';
    var h = size || 120, w = Math.round(h * 120 / 140);
    var eyes, mouth, arms = '', extra = '', brows = '';
    if (mood === 'xursand') {
      eyes = '<path d="M41 54q9-11 18 0M65 54q9-11 18 0" stroke="' + M.ink + '" stroke-width="4.5" stroke-linecap="round" fill="none"/>';
      mouth = '<path d="M50 70q12 14 24 0z" fill="' + M.ink + '"/><path d="M55 75q7 4 14 0" stroke="#ff8a9b" stroke-width="3" stroke-linecap="round" fill="none"/>';
      arms = '<g class="bd-m-cheer">' + arm('M24 70Q12 56 10 40') + hand(10, 38) + arm('M96 70Q108 56 110 40') + hand(110, 38) + '</g>';
      extra = '<path d="M14 18l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="' + M.mark + '"/><path d="M104 10l1.6 4 4 1.6-4 1.6-1.6 4-1.6-4-4-1.6 4-1.6z" fill="' + M.mark + '"/>';
    } else if (mood === 'oylayapti') {
      eyes = eye(50, 52, 2.5, -4) + eye(74, 52, 2.5, -4);
      mouth = '<path d="M56 74q6-3 12 0" stroke="' + M.ink + '" stroke-width="3.5" stroke-linecap="round" fill="none"/>';
      arms = arm('M24 76Q12 86 18 100') + hand(18, 101) + arm('M96 78Q86 84 76 78') + hand(74, 77);
      extra = '<g transform="translate(92 -2)"><circle cx="12" cy="12" r="9" fill="' + M.mark + '"/><rect x="8" y="20" width="8" height="5" rx="2" fill="' + M.spine + '"/><path d="M12 -2v-3M24 8l3-2M0 8l-3-2" stroke="' + M.mark + '" stroke-width="2.5" stroke-linecap="round"/></g>';
    } else if (mood === 'ishora') {
      eyes = eye(50, 52, -4, 1) + eye(74, 52, -4, 1);
      mouth = '<path d="M52 70q10 9 20 0" stroke="' + M.ink + '" stroke-width="3.5" stroke-linecap="round" fill="none"/>';
      arms = '<g class="bd-m-point">' + arm('M26 74Q16 72 8 76') + hand(7, 76) + '</g>' + arm('M96 76Q106 88 102 100') + hand(102, 101);
    } else if (mood === 'hayron') {
      eyes = eye(50, 54, 0, 1) + eye(74, 54, 0, 1);
      brows = '<path d="M41 42l14-5M83 42l-14-5" stroke="' + M.ink + '" stroke-width="3.5" stroke-linecap="round"/>';
      mouth = '<path d="M54 76q3-4 6 0t6 0t6 0" stroke="' + M.ink + '" stroke-width="3.5" stroke-linecap="round" fill="none"/>';
      arms = arm('M24 76Q14 88 18 100') + hand(18, 101) + arm('M96 76Q106 88 102 100') + hand(102, 101);
    } else { /* salom */
      eyes = eye(50, 52, 1, 1) + eye(74, 52, 1, 1);
      mouth = '<path d="M50 69q12 12 24 0" stroke="' + M.ink + '" stroke-width="3.5" stroke-linecap="round" fill="none"/>';
      arms = arm('M24 76Q14 88 18 100') + hand(18, 101) + '<g class="bd-m-wave">' + arm('M96 72Q110 60 108 42') + hand(108, 40) + '</g>';
    }
    return '<svg class="bd-mascot bd-mascot--' + mood + '" width="' + w + '" height="' + h + '" viewBox="0 0 120 140" fill="none" role="img" aria-label="Bilimdon maskoti">' +
      '<rect x="40" y="116" width="12" height="18" rx="6" fill="' + M.ink + '"/><rect x="68" y="116" width="12" height="18" rx="6" fill="' + M.ink + '"/>' +
      '<rect x="31" y="20" width="68" height="102" rx="14" fill="' + M.page + '"/>' +
      '<path d="M93 30v82" stroke="#ead9b4" stroke-width="2"/>' +
      '<rect x="24" y="16" width="70" height="104" rx="14" fill="' + M.body + '"/>' +
      '<path d="M38 16h-0a14 14 0 0 0-14 14v76a14 14 0 0 0 14 14z" fill="' + M.spine + '"/>' +
      '<path d="M74 8h12v28l-6-5-6 5z" fill="' + M.mark + '"/>' +
      arms + brows + eyes +
      '<circle cx="40" cy="66" r="4.5" fill="' + M.cheek + '" opacity=".55"/><circle cx="84" cy="66" r="4.5" fill="' + M.cheek + '" opacity=".55"/>' +
      mouth + extra + '</svg>';
  }

  /* Hech qanday framework talab qilinmaydi: <i data-ico="star" data-size="16"></i> va <span data-mascot="salom" data-size="96"></span> joylanadi. */
  function mount(root) {
    root = root || document;
    var a = root.querySelectorAll('[data-ico]');
    for (var i = 0; i < a.length; i++) { if (!a[i].firstChild) a[i].innerHTML = icon(a[i].getAttribute('data-ico'), +a[i].getAttribute('data-size') || 20); }
    var b = root.querySelectorAll('[data-mascot]');
    for (var j = 0; j < b.length; j++) { if (!b[j].firstChild) b[j].innerHTML = mascot(b[j].getAttribute('data-mascot'), +b[j].getAttribute('data-size') || 120); }
  }
  window.Bilimdon = { icon: icon, mascot: mascot, mount: mount, icons: Object.keys(I) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { mount(); });
  else mount();
})();
