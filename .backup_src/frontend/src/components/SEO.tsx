import { useEffect } from "react";

interface SEOProps {
  title?: string;
  description?: string;
  canonical?: string;
  ogImage?: string;
  ogType?: string;
  twitterCard?: "summary" | "summary_large_image";
  structuredData?: Record<string, unknown>;
  noindex?: boolean;
}

const BASE_TITLE = "CloudScale Commerce";
const BASE_URL = typeof window !== "undefined" ? window.location.origin : "";

function setMeta(name: string, content: string, isProperty = false) {
  const attr = isProperty ? "property" : "name";
  let el = document.querySelector(`meta[${attr}="${name}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.content = content;
}

function setLink(rel: string, href: string) {
  let el = document.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.rel = rel;
    document.head.appendChild(el);
  }
  el.href = href;
}

export function SEO({
  title,
  description = "Enterprise cloud-native commerce platform built with microservices, event-driven architecture, and production-grade observability.",
  canonical,
  ogImage = "/og-image.png",
  ogType = "website",
  twitterCard = "summary_large_image",
  structuredData,
  noindex = false,
}: SEOProps) {
  useEffect(() => {
    // Title
    document.title = title ? `${title} | ${BASE_TITLE}` : BASE_TITLE;

    // Meta description
    setMeta("description", description);

    // Robots
    if (noindex) {
      setMeta("robots", "noindex, nofollow");
    } else {
      setMeta("robots", "index, follow");
    }

    // Open Graph
    setMeta("og:title", title || BASE_TITLE, true);
    setMeta("og:description", description, true);
    setMeta("og:type", ogType, true);
    setMeta("og:image", ogImage.startsWith("http") ? ogImage : `${BASE_URL}${ogImage}`, true);
    setMeta("og:url", canonical || window.location.href, true);
    setMeta("og:site_name", BASE_TITLE, true);

    // Twitter
    setMeta("twitter:card", twitterCard);
    setMeta("twitter:title", title || BASE_TITLE);
    setMeta("twitter:description", description);
    setMeta("twitter:image", ogImage.startsWith("http") ? ogImage : `${BASE_URL}${ogImage}`);

    // Canonical
    if (canonical) {
      setLink("canonical", canonical);
    }

    // Structured Data (JSON-LD)
    const existingLD = document.querySelector("#structured-data");
    if (existingLD) existingLD.remove();
    if (structuredData) {
      const script = document.createElement("script");
      script.id = "structured-data";
      script.type = "application/ld+json";
      script.textContent = JSON.stringify(structuredData);
      document.head.appendChild(script);
    }
  }, [title, description, canonical, ogImage, ogType, twitterCard, structuredData, noindex]);

  return null;
}
