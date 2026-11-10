import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { CameraOff, IdCard, LogIn, QrCode, UserRound } from 'lucide-react';
import { Button, buttonClass } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Card } from '@/components/ui/Card';
import { useQrLinkLogin, useSession } from '../hooks/useSession';
import { readTokenFromHash } from '../utils/qrToken';
import { authErrorMessage } from '../utils/authErrors';

/** Takes `#t=…` out of the address bar and the history entry, so the token isn't left behind. */
function clearTokenFromAddress() {
  if (!window.location.hash) return;
  window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search);
}

function Waiting({ text }: { text: string }) {
  return (
    <Card className="mt-5 flex items-center justify-center gap-3 text-[16px] font-bold" role="status">
      <Spinner className="size-6 text-primary" />
      {text}
    </Card>
  );
}

/**
 * Where a ticket's QR code leads: the phone camera opens `/qr#t=<token>` and the pupil is signed
 * in without opening the scanner. The token is single-use, so it is sent exactly once.
 */
export default function QrLinkPage() {
  // Read before anything rewrites the URL. A pure read, so React's double render in dev is harmless.
  const [token] = useState(() => readTokenFromHash(window.location.hash));
  const session = useSession();
  const login = useQrLinkLogin();
  const navigate = useNavigate();
  const sent = useRef(false);
  const [keepCurrent, setKeepCurrent] = useState(false);

  useEffect(clearTokenFromAddress, []);

  // A second ticket opened in this same tab changes only the "#" part, which doesn't reload the
  // page. Start over so that ticket is read like the first one.
  useEffect(() => {
    const onHashChange = () => {
      if (readTokenFromHash(window.location.hash)) window.location.reload();
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const current = session.data;
  // Wait for /auth/me: a profile cached in this tab may belong to a session that has already ended.
  const checking = session.isFetching && !sent.current;

  const { mutate } = login;
  const signIn = useCallback(() => {
    if (!token || sent.current) return;
    sent.current = true; // survives StrictMode's remount, so the single-use token is never sent twice
    mutate(token);
  }, [token, mutate]);

  // Nobody is signed in on this device: go straight in.
  useEffect(() => {
    if (!checking && !current) signIn();
  }, [checking, current, signIn]);

  useEffect(() => {
    if (keepCurrent) navigate('/', { replace: true });
  }, [keepCurrent, navigate]);

  if (!token) {
    return (
      <Problem
        title="Havola toʻliq emas"
        text="Bu havolada kirish kodi yoʻq yoki u buzilgan. Chiptadagi QR kodni qaytadan skanerlang."
      />
    );
  }

  if (login.isError) {
    return <Problem title="Kirib boʻlmadi" text={authErrorMessage(login.error)} />;
  }

  if (checking) return <Waiting text="Tekshirilmoqda…" />;

  // Someone is already signed in on this device and the ticket may be another pupil's: ask.
  if (current && !sent.current) {
    return (
      <div>
        <h2 className="t-hero">Kim kiryapti?</h2>
        <Card className="mt-5">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary-light text-primary" aria-hidden="true">
              <UserRound className="size-6" />
            </span>
            <p className="text-[15px] text-muted">
              Bu qurilmada hozir{' '}
              <b className="text-ink">
                {current.firstName} {current.lastName}
              </b>{' '}
              kirgan. Chipta boshqa oʻquvchiniki boʻlsa, uning nomidan kiring.
            </p>
          </div>
          <div className="mt-5 flex flex-col gap-3">
            <Button size="lg" fullWidth leftIcon={<LogIn className="size-5" aria-hidden="true" />} onClick={signIn}>
              Chiptadagi oʻquvchi boʻlib kirish
            </Button>
            <Button size="lg" variant="secondary" fullWidth onClick={() => setKeepCurrent(true)}>
              {current.firstName} boʻlib davom etish
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return <Waiting text="Kirilmoqda…" />;
}

function Problem({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h2 className="t-hero">QR kod orqali kirish</h2>
      <Card className="mt-5" role="alert">
        <div className="flex items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-warning-light text-warning-strong" aria-hidden="true">
            <CameraOff className="size-6" />
          </span>
          <div>
            <h3 className="text-[17px] font-extrabold">{title}</h3>
            <p className="mt-1 text-[15px] text-muted">{text}</p>
          </div>
        </div>
        <div className="mt-5 flex flex-col gap-3">
          <Link to="/login/qr" className={buttonClass('primary', { size: 'lg', fullWidth: true })}>
            <QrCode className="size-5" aria-hidden="true" />
            Kamera bilan skanerlash
          </Link>
          <Link to="/login/jshshir" className={buttonClass('secondary', { size: 'lg', fullWidth: true })}>
            <IdCard className="size-5" aria-hidden="true" />
            JSHSHIR orqali kirish
          </Link>
        </div>
      </Card>
    </div>
  );
}
