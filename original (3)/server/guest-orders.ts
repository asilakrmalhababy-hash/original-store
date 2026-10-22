import { createHash, timingSafeEqual } from "node:crypto";

export function isValidGuestPhone(value: string): boolean {
  const latinDigits = value
    .replace(/[٠-٩]/g, digit => String(digit.charCodeAt(0) - 0x0660))
    .replace(/[۰-۹]/g, digit => String(digit.charCodeAt(0) - 0x06f0));
  const digits = latinDigits.replace(/\D/g, "");
  return /^\+?[\d\s().-]+$/.test(latinDigits) && digits.length >= 7 && digits.length <= 15;
}

/** Store only a one-way digest for new guest-order access references. */
export function hashGuestOrderKey(key: string): string {
  return createHash("sha256").update(key, "utf8").digest("hex");
}

function constantTimeEqual(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left, "utf8");
  const rightBytes = Buffer.from(right, "utf8");
  return leftBytes.length === rightBytes.length && timingSafeEqual(leftBytes, rightBytes);
}

/**
 * Accept the digest used by new guest orders and the raw key used by orders
 * created before the digest change. The legacy path preserves existing local
 * references without changing or deleting historical order data.
 */
export function matchesGuestOrderKey(providedKey: string, storedKey: string): boolean {
  const digest = hashGuestOrderKey(providedKey);
  const digestMatches = constantTimeEqual(digest, storedKey);
  const legacyMatches = constantTimeEqual(providedKey, storedKey);
  return digestMatches || legacyMatches;
}
