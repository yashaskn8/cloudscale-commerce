import React, { createContext, useContext, useState, useCallback, useMemo } from "react";
import en from "./locales/en.json";
import es from "./locales/es.json";

type Locale = "en" | "es";
type TranslationMap = Record<string, Record<string, string>>;

const translations: Record<Locale, TranslationMap> = {
  en: en as unknown as TranslationMap,
  es: es as unknown as TranslationMap,
};

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string>) => string;
  dir: "ltr" | "rtl";
  availableLocales: { code: Locale; label: string }[];
}

const I18nContext = createContext<I18nContextValue | null>(null);

function getNestedValue(obj: TranslationMap, key: string): string {
  const parts = key.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return key;
    }
  }
  return typeof current === "string" ? current : key;
}

const RTL_LOCALES: Locale[] = []; // Ready for Arabic, Hebrew etc.

const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  es: "Español",
};

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const stored = localStorage.getItem("cloudscale-locale") as Locale | null;
    return stored && stored in translations ? stored : "en";
  });

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem("cloudscale-locale", newLocale);
    document.documentElement.lang = newLocale;
    document.documentElement.dir = RTL_LOCALES.includes(newLocale) ? "rtl" : "ltr";
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string>): string => {
      let value = getNestedValue(translations[locale], key);
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          value = value.replace(`{{${k}}}`, v);
        });
      }
      return value;
    },
    [locale]
  );

  const dir: "ltr" | "rtl" = RTL_LOCALES.includes(locale) ? "rtl" : "ltr";

  const availableLocales = useMemo(
    () => (Object.keys(translations) as Locale[]).map((code) => ({ code, label: LOCALE_LABELS[code] })),
    []
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, dir, availableLocales }),
    [locale, setLocale, t, dir, availableLocales]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function useTranslation() {
  const { t } = useI18n();
  return { t };
}
