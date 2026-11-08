import { ApiError } from '@/lib/http';

/** Turns any login failure into a calm, child-friendly Uzbek message. */
export function authErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Kutilmagan xatolik yuz berdi. Qayta urinib ko‘r.';
  switch (error.code) {
    case 'INVALID_CREDENTIALS':
      return 'Bu JSHSHIR bo‘yicha o‘quvchi topilmadi. Raqamlarni tekshirib, qayta kiritib ko‘r.';
    case 'QR_EXPIRED':
      return 'Bu QR kodning muddati tugagan. O‘qituvchingdan yangi QR kod so‘ra.';
    case 'QR_ALREADY_USED':
      return 'Bu QR kod allaqachon ishlatilgan. O‘qituvchingdan yangisini so‘ra.';
    case 'QR_INVALID':
      return 'Bu QR kod bizniki emasga o‘xshaydi. Imtihon chiptangdagi QR kodni skanerla.';
    case 'RATE_LIMITED':
      return 'Juda ko‘p urinish bo‘ldi. Bir daqiqa dam olib, keyin qayta urin.';
  }
  switch (error.kind) {
    case 'network':
      return 'Internet aloqasi yo‘q. Ulanishni tekshirib, qayta urin.';
    case 'rate_limited':
      return 'Juda ko‘p urinish bo‘ldi. Bir daqiqa dam olib, keyin qayta urin.';
    case 'unauthorized':
    case 'validation':
      return 'Ma’lumotlar to‘g‘ri kelmadi. Tekshirib, qayta urinib ko‘r.';
    default:
      return 'Hozir kirishning imkoni bo‘lmadi. Birozdan so‘ng qayta urinib ko‘r.';
  }
}
