import { describe, it, expect, beforeEach } from "vitest";
import { fuzzyMatchScore, fuzzySearch } from "@/lib/fuzzySearch";
import { sanitizeHTML, secureStorage } from "@/lib/security";
import { isFeatureEnabled, getFeatureFlags } from "@/lib/config";

describe("Phase 14 Production Hardening Utilities", () => {
  describe("Fuzzy Search & Relevance", () => {
    it("should calculate exact matches correctly", () => {
      expect(fuzzyMatchScore("test", "test")).toBe(1.0);
      expect(fuzzyMatchScore("", "test")).toBe(1.0);
      expect(fuzzyMatchScore("test", "")).toBe(0.0);
    });

    it("should rank substring matches higher than fuzzy gaps", () => {
      const score1 = fuzzyMatchScore("app", "apparel");
      const score2 = fuzzyMatchScore("app", "grape"); // fuzzy match
      expect(score1).toBeGreaterThan(score2);
    });

    it("should search collections and rank results", () => {
      const collection = [
        { name: "Red Shirt", sku: "SHIRT-RED" },
        { name: "Blue Jeans", sku: "JEAN-BLUE" },
        { name: "Green Hat", sku: "HAT-GREEN" },
      ];

      const results = fuzzySearch(collection, "shirt", (item) => [item.name, item.sku]);
      expect(results).toHaveLength(1);
      expect(results[0].item.name).toBe("Red Shirt");
    });
  });

  describe("Frontend XSS & DOM Sanitization", () => {
    it("should escape malicious characters properly", () => {
      const dirty = "<script>alert('xss')</script>";
      const clean = sanitizeHTML(dirty);
      expect(clean).not.toContain("<script>");
      expect(clean).toContain("&lt;script&gt;");
    });
  });

  describe("Secure LocalStorage Wrapper", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("should securely encode and decode data", () => {
      const data = { adminPrivileges: true };
      secureStorage.setItem("user_role", data);

      const retrieved = secureStorage.getItem("user_role");
      expect(retrieved).toEqual(data);
    });

    it("should reject tampered or corrupted storage items", () => {
      secureStorage.setItem("secure_flag", { val: 42 });

      // Tamper with the raw string in localStorage
      const key = "cs_secure_flag";
      const raw = localStorage.getItem(key);
      if (raw) {
        const parsed = JSON.parse(raw);
        // Change data payload without updating checksum signature
        parsed.d = btoa(JSON.stringify({ val: 999 }));
        localStorage.setItem(key, JSON.stringify(parsed));
      }

      const value = secureStorage.getItem("secure_flag");
      expect(value).toBeNull();
    });
  });

  describe("Enterprise Configuration & Flags", () => {
    it("should read default feature flags", () => {
      expect(isFeatureEnabled("enableWebSocket")).toBe(true);
      expect(isFeatureEnabled("enablePWA")).toBe(true);
      expect(getFeatureFlags()).toHaveProperty("enableOnboarding");
    });
  });
});
