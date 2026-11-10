import { useCallback, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { Camera, CameraOff, IdCard, RotateCcw, ScanLine } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Card } from '@/components/ui/Card';
import { BackLink } from '../components/BackLink';
import { useQrScanner, type ScannerStatus } from '../hooks/useQrScanner';
import { useQrLogin } from '../hooks/useSession';
import { extractQrToken } from '../utils/qrToken';
import { authErrorMessage } from '../utils/authErrors';
import { safeRedirect } from '../utils/redirect';
import { cn } from '@/lib/cn';

const CAMERA_PROBLEMS: Partial<Record<ScannerStatus, { title: string; text: string }>> = {
  denied: {
    title: 'Kameraga ruxsat berilmadi',
    text: 'QR kodni oʻqish uchun kamera kerak. Brauzer sozlamalarida kameraga ruxsat berib, “Qayta urinish” tugmasini bosing.',
  },
  no_camera: { title: 'Kamera topilmadi', text: 'Bu qurilmada kamera yoʻqqa oʻxshaydi. JSHSHIR orqali kirib koʻring.' },
  unsupported: { title: 'Kamera ishlamayapti', text: 'Bu brauzer kamerani qoʻllab-quvvatlamaydi. Boshqa brauzerda oching yoki JSHSHIR orqali kiring.' },
  error: { title: 'Kamerani yoqib boʻlmadi', text: 'Kamera boshqa ilovada ochiq boʻlishi mumkin. Uni yopib, qayta urinib koʻring.' },
};

export default function QrLoginPage() {
  const location = useLocation();
  const login = useQrLogin(safeRedirect(location.state));
  const [scanError, setScanError] = useState<string | null>(null);

  const handleScan = useCallback(
    (text: string) => {
      const token = extractQrToken(text);
      if (!token) {
        setScanError('Bu QR kod bizniki emasga oʻxshaydi. Imtihon chiptangizdagi QR kodni skanerlang.');
        return;
      }
      setScanError(null);
      login.mutate(token);
    },
    [login],
  );

  const { videoRef, status, start } = useQrScanner(handleScan);
  const problem = CAMERA_PROBLEMS[status];
  const verifying = login.isPending;
  const errorText = scanError ?? (login.isError ? authErrorMessage(login.error) : null);
  const showCamera = status === 'starting' || status === 'scanning';

  const retry = () => {
    setScanError(null);
    login.reset();
    void start();
  };

  return (
    <div>
      <BackLink to="/login" state={location.state} />
      <h2 className="t-hero mt-2">QR kod orqali kirish</h2>

      {/* Viewfinder — the <video> must stay mounted so the hook can attach the stream. */}
      <div
        className={cn(
          'relative mt-5 aspect-square w-full overflow-hidden rounded-[28px] bg-[#0F2E2A] shadow-[var(--shadow-lift)]',
          !showCamera && 'hidden',
        )}
      >
        <video ref={videoRef} muted playsInline className="h-full w-full object-cover" aria-label="Kamera koʻrinishi" />
        <div className="pointer-events-none absolute inset-[14%] rounded-[24px] border-4 border-white/90 shadow-[0_0_0_999px_rgb(15_46_42/0.45)]" aria-hidden="true">
          <div className="absolute inset-x-4 top-1/2 h-0.5 bg-warning/90 motion-safe:animate-pulse" />
        </div>
        {(status === 'starting' || verifying) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#0F2E2A]/70 text-white" role="status">
            <Spinner className="size-8" />
            <span className="text-[16px] font-bold">{verifying ? 'Tekshirilmoqda…' : 'Kamera yoqilmoqda…'}</span>
          </div>
        )}
      </div>

      {status === 'scanning' && !verifying && (
        <p className="mt-4 flex items-center justify-center gap-2 text-center text-[16px] font-semibold text-muted" role="status">
          <ScanLine className="size-5 text-primary" aria-hidden="true" />
          QR kodni ramka ichiga joylashtiring
        </p>
      )}

      {verifying && !showCamera && (
        <Card className="mt-5 flex items-center justify-center gap-3 text-[16px] font-bold" role="status">
          <Spinner className="size-6 text-primary" />
          Tekshirilmoqda…
        </Card>
      )}

      {status === 'idle' && !verifying && !errorText && (
        <Card className="mt-5">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary-light text-primary" aria-hidden="true">
              <Camera className="size-6" />
            </span>
            <div>
              <h3 className="text-[17px] font-extrabold">Kamera kerak boʻladi</h3>
              <p className="mt-1 text-[15px] text-muted">
                QR kodni oʻqish uchun telefoningiz kamerasidan foydalanamiz. Rasm hech qayerga saqlanmaydi. Brauzer ruxsat soʻraganda “Ruxsat berish” tugmasini bosing.
              </p>
            </div>
          </div>
          <Button size="lg" fullWidth className="mt-5" leftIcon={<Camera className="size-5" aria-hidden="true" />} onClick={() => void start()}>
            Kamerani yoqish
          </Button>
        </Card>
      )}

      {(problem || errorText) && !verifying && !showCamera && (
        <Card className="mt-5" role="alert">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-warning-light text-warning-strong" aria-hidden="true">
              <CameraOff className="size-6" />
            </span>
            <div>
              <h3 className="text-[17px] font-extrabold">{problem?.title ?? 'Kirib boʻlmadi'}</h3>
              <p className="mt-1 text-[15px] text-muted">{problem?.text ?? errorText}</p>
            </div>
          </div>
          <div className="mt-5 flex flex-col gap-3">
            {status !== 'no_camera' && status !== 'unsupported' && (
              <Button size="lg" fullWidth leftIcon={<RotateCcw className="size-5" aria-hidden="true" />} onClick={retry}>
                Qayta urinish
              </Button>
            )}
          </div>
        </Card>
      )}

      <Link
        to="/login/jshshir"
        state={location.state}
        className="mt-6 flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-control)] text-[15px] font-bold text-primary-dark hover:bg-primary-light"
      >
        <IdCard className="size-5" aria-hidden="true" />
        JSHSHIR orqali kirish
      </Link>

      {/* Direct import.meta.env check so the bundler removes this block from production builds. */}
      {import.meta.env.VITE_USE_MOCKS === 'true' && (
        <div className="mt-4 flex flex-col gap-2 rounded-xl bg-warning-light p-3 text-[13px] text-warning-strong">
          <span>Demo rejim: kamerasiz sinash uchun skanerlashni simulyatsiya qiling.</span>
          <div className="flex flex-wrap gap-2">
            {[
              ['Toʻgʻri', 'demo-qr-valid-7f3a9c2e1b4d'],
              ['Muddati oʻtgan', 'demo-qr-expired-0c8e2a9f71'],
              ['Ishlatilgan', 'demo-qr-used-5b1d7e3c9a20'],
              ['Begona', 'https://shop.example.com/x'],
            ].map(([label, value]) => (
              <button key={label} type="button" className="min-h-9 rounded-lg bg-card px-3 font-bold" onClick={() => handleScan(value!)}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
