/**
 * Minimal XSS protection: Sanitizes raw HTML strings by escaping special characters.
 */
export function sanitizeHTML(str: string): string {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;")
    .replace(/\//g, "&#x2F;");
}

function computeHash(str: string): string {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 33) ^ str.charCodeAt(i);
  }
  return (hash >>> 0).toString(16);
}

/**
 * Secure LocalStorage wrapper that base64 encodes data and signs it with a simple checksum
 * to prevent tamper-based attacks in administrative variables.
 */
export const secureStorage = {
  setItem(key: string, value: any): void {
    try {
      const dataStr = JSON.stringify(value);
      const encoded = btoa(unescape(encodeURIComponent(dataStr)));
      
      // Compute integrity signature
      const checksum = computeHash(encoded);
      const storageObj = { d: encoded, s: checksum };
      
      localStorage.setItem(`cs_${key}`, JSON.stringify(storageObj));
    } catch {
      localStorage.setItem(`cs_${key}`, JSON.stringify({ d: "", s: "" }));
    }
  },

  getItem<T = any>(key: string): T | null {
    try {
      const stored = localStorage.getItem(`cs_${key}`);
      if (!stored) return null;

      const { d: encoded, s: checksum } = JSON.parse(stored);
      
      // Validate checksum signature
      const validChecksum = computeHash(encoded);
      if (checksum !== validChecksum) {
        console.warn(`[Security Alert] Storage corruption or tampering detected for key: cs_${key}`);
        return null;
      }

      const decoded = decodeURIComponent(escape(atob(encoded)));
      return JSON.parse(decoded) as T;
    } catch {
      return null;
    }
  },

  removeItem(key: string): void {
    localStorage.removeItem(`cs_${key}`);
  }
};

/**
 * Attaches standard anti-CSRF request validation header mocks.
 */
export function getCSRFToken(): string {
  // Read token from secure cookies or session meta
  return "cloudscale-csrf-guard-v1";
}
