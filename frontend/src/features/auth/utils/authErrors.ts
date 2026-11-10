import { ApiError } from '@/lib/http';

/** Turns any login failure into a calm, child-friendly Uzbek message. */
export function authErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Kutilmagan xatolik yuz berdi. Qayta urinib koʻring.';
  switch (error.code) {
    case 'INVALID_CREDENTIALS':
      return 'Bu JSHSHIR boʻyicha oʻquvchi topilmadi. Raqamlarni tekshirib, qayta kiritib koʻring.';
    case 'QR_EXPIRED':
      return 'Bu QR kodning muddati tugagan. Oʻqituvchingizdan yangi QR kod soʻrang.';
    case 'QR_ALREADY_USED':
      return 'Bu QR kod allaqachon ishlatilgan. Oʻqituvchingizdan yangisini soʻrang.';
    case 'QR_INVALID':
      return 'Bu QR kod bizniki emasga oʻxshaydi. Imtihon chiptangizdagi QR kodni skanerlang.';
    case 'RATE_LIMITED':
      return 'Juda koʻp urinish boʻldi. Bir daqiqa dam olib, keyin qayta urining.';
  }
  switch (error.kind) {
    case 'network':
      return 'Internet aloqasi yoʻq. Ulanishni tekshirib, qayta urining.';
    case 'rate_limited':
      return 'Juda koʻp urinish boʻldi. Bir daqiqa dam olib, keyin qayta urining.';
    case 'unauthorized':
    case 'validation':
      return 'Maʼlumotlar toʻgʻri kelmadi. Tekshirib, qayta urinib koʻring.';
    default:
      return 'Hozir kirishning imkoni boʻlmadi. Birozdan soʻng qayta urinib koʻring.';
  }
}
