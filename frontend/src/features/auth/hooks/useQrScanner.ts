import { useCallback, useEffect, useRef, useState } from 'react';

export type ScannerStatus = 'idle' | 'starting' | 'scanning' | 'denied' | 'no_camera' | 'unsupported' | 'error';

interface DetectedBarcode {
  rawValue: string;
}
interface BarcodeDetectorLike {
  detect(source: CanvasImageSource): Promise<DetectedBarcode[]>;
}
interface BarcodeDetectorCtor {
  new (opts: { formats: string[] }): BarcodeDetectorLike;
  getSupportedFormats?: () => Promise<string[]>;
}

type Decoder = (video: HTMLVideoElement, canvas: HTMLCanvasElement) => Promise<string | null>;

async function createDecoder(): Promise<Decoder> {
  const Native = (window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }).BarcodeDetector;
  if (Native) {
    try {
      const formats = (await Native.getSupportedFormats?.()) ?? ['qr_code'];
      if (formats.includes('qr_code')) {
        const detector = new Native({ formats: ['qr_code'] });
        return async (video) => {
          const codes = await detector.detect(video);
          return codes[0]?.rawValue ?? null;
        };
      }
    } catch {
      /* fall through to jsQR */
    }
  }
  // Loaded only when needed (iOS Safari, Firefox) to keep the login bundle small.
  const { default: jsQR } = await import('jsqr');
  return async (video, canvas) => {
    const size = Math.min(video.videoWidth, video.videoHeight);
    if (!size) return null;
    const target = Math.min(size, 640);
    canvas.width = target;
    canvas.height = target;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return null;
    // Decode only the centre square — that's where the viewfinder guides the child to aim.
    ctx.drawImage(video, (video.videoWidth - size) / 2, (video.videoHeight - size) / 2, size, size, 0, 0, target, target);
    const img = ctx.getImageData(0, 0, target, target);
    return jsQR(img.data, target, target, { inversionAttempts: 'dontInvert' })?.data ?? null;
  };
}

/**
 * Camera + QR decoding lifecycle. The camera is requested ONLY when `start()` is called,
 * i.e. after the student has explicitly chosen QR login and read the explanation.
 */
export function useQrScanner(onResult: (text: string) => void) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const activeRef = useRef(false);
  const onResultRef = useRef(onResult);
  const [status, setStatus] = useState<ScannerStatus>('idle');

  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  const stop = useCallback(() => {
    activeRef.current = false;
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  const start = useCallback(async () => {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setStatus('unsupported');
      return;
    }
    setStatus('starting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        stop();
        return;
      }
      video.srcObject = stream;
      await video.play();
      const decode = await createDecoder();
      canvasRef.current ??= document.createElement('canvas');
      activeRef.current = true;
      setStatus('scanning');

      let last = 0;
      let busy = false;
      const tick = (t: number) => {
        if (!activeRef.current) return;
        rafRef.current = requestAnimationFrame(tick);
        if (busy || t - last < 160 || video.readyState < 2) return;
        last = t;
        busy = true;
        decode(video, canvasRef.current!)
          .then((text) => {
            if (text && activeRef.current) {
              stop();
              onResultRef.current(text);
            }
          })
          .catch(() => undefined)
          .finally(() => {
            busy = false;
          });
      };
      rafRef.current = requestAnimationFrame(tick);
    } catch (err) {
      stop();
      const name = err instanceof DOMException ? err.name : '';
      if (name === 'NotAllowedError' || name === 'SecurityError') setStatus('denied');
      else if (name === 'NotFoundError' || name === 'OverconstrainedError') setStatus('no_camera');
      else setStatus('error');
    }
  }, [stop]);

  useEffect(() => stop, [stop]);

  return { videoRef, status, setStatus, start, stop };
}
