/**
 * Computes a fuzzy match score between a query and a target string.
 * Returns a score between 0 (no match) and 1 (exact match).
 */
export function fuzzyMatchScore(query: string, target: string): number {
  const q = query.toLowerCase().trim();
  const t = target.toLowerCase().trim();

  if (!q) return 1.0;
  if (!t) return 0.0;
  if (q === t) return 1.0;
  if (t.includes(q)) {
    // Boost score if query is a direct substring
    return 0.8 + (q.length / t.length) * 0.2;
  }

  let qIdx = 0;
  let tIdx = 0;
  let matches = 0;
  let gaps = 0;

  while (qIdx < q.length && tIdx < t.length) {
    if (q[qIdx] === t[tIdx]) {
      matches++;
      qIdx++;
    } else {
      gaps++;
    }
    tIdx++;
  }

  // All query chars must be found in target sequentially
  if (matches !== q.length) {
    return 0.0;
  }

  // Score penalizes gaps
  const penalty = gaps * 0.01;
  const score = 0.5 + (matches / t.length) * 0.3 - penalty;

  return Math.max(0.1, Math.min(0.9, score));
}

export interface FuzzySearchResult<T> {
  item: T;
  score: number;
}

/**
 * Searches a list of items using a query and a getter function to resolve search strings.
 */
export function fuzzySearch<T>(
  items: T[],
  query: string,
  getStrings: (item: T) => string[]
): FuzzySearchResult<T>[] {
  if (!query) {
    return items.map((item) => ({ item, score: 1.0 }));
  }

  return items
    .map((item) => {
      const strings = getStrings(item);
      const scores = strings.map((str) => fuzzyMatchScore(query, str));
      const maxScore = Math.max(...scores, 0);
      return { item, score: maxScore };
    })
    .filter((res) => res.score > 0.0)
    .sort((a, b) => b.score - a.score);
}
