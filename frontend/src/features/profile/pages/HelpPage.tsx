import { Icon } from '@/components/ui/Icon';
import { Mascot } from '@/components/shared/Mascot';
import { Section, TopBar } from '@/components/shared/design';

const FAQ = [
  ['Internet uzilib qolsa nima boʻladi?', 'Xavotir olmang. Javoblaringiz telefoningizda saqlanib turadi va aloqa tiklanganda avtomatik yuboriladi. Vaqt esa serverda hisoblanadi.'],
  ['Sahifani yangilab yuborsam-chi?', 'Imtihon oʻsha joyidan davom etadi. Javoblaringiz va qolgan vaqt saqlanadi.'],
  ['Javobimni oʻzgartirsam boʻladimi?', 'Ha, imtihon tugaguncha istalgan savolga qaytib, javobingizni oʻzgartirishingiz mumkin.'],
  ['Vaqt tugasa-chi?', 'Imtihon avtomatik yakunlanadi va belgilagan javoblaringiz hisobga olinadi.'],
];

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <TopBar title="Yordam" back="/profile" />

      <div className="bd-card bd-card--cream row gap-3! px-4! py-3!">
        <Mascot mood="oylayapti" size={64} />
        <p className="t-sm">Savolingiz bormi? Koʻp soʻraladigan savollarga javoblar shu yerda.</p>
      </div>

      <Section title="Koʻp soʻraladigan savollar" id="faq-title">
        <div className="flex flex-col gap-2">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group bd-card p-0! [&_summary::-webkit-details-marker]:hidden">
              <summary className="bd-rowcard tap-card cursor-pointer list-none rounded-[var(--radius-lg)] px-4 py-2 hover:bg-bg-tint">
                <span className="bd-tile">
                  <Icon name="help" size={18} />
                </span>
                <span className="t-h3 grow">{q}</span>
                <Icon name="chevD" size={18} className="text-ink-3 transition-transform group-open:rotate-180" />
              </summary>
              <p className="t-sm muted border-t border-line px-4 pt-3 pb-4">{a}</p>
            </details>
          ))}
        </div>
      </Section>

      <section id="privacy" className="sec scroll-mt-4">
        <div className="bd-card px-4! py-3.5!">
          <div className="row">
            <span className="bd-tile">
              <Icon name="shield" size={18} />
            </span>
            <h2 className="t-h2">Maxfiylik</h2>
          </div>
          <p className="t-sm muted mt-2">
            Biz faqat imtihon uchun kerakli maʼlumotlarni saqlaymiz: ismingiz, maktabingiz, sinfingiz va javoblaringiz. Shaxsiy raqamingiz (JSHSHIR) ekranda koʻrsatilmaydi. Reklama va
            kuzatuv xizmatlari ishlatilmaydi. Natijalaringizni faqat siz, ota-onangiz va maktabingiz koʻra oladi.
          </p>
        </div>
      </section>
    </div>
  );
}
