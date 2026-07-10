import { useState, useEffect, useMemo } from "react";
import type { RefObject } from "react";

interface UseVirtualizerOptions {
  itemCount: number;
  itemHeight: number;
  overscan?: number;
  containerRef: RefObject<HTMLElement | null>;
}

export function useVirtualizer({
  itemCount,
  itemHeight,
  overscan = 5,
  containerRef
}: UseVirtualizerOptions) {
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    setScrollTop(container.scrollTop);
    setContainerHeight(container.clientHeight);

    const handleScroll = () => {
      setScrollTop(container.scrollTop);
    };

    const handleResize = () => {
      setContainerHeight(container.clientHeight);
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    
    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(container);
    } else {
      window.addEventListener("resize", handleResize);
    }

    return () => {
      container.removeEventListener("scroll", handleScroll);
      if (resizeObserver) {
        resizeObserver.disconnect();
      } else {
        window.removeEventListener("resize", handleResize);
      }
    };
  }, [containerRef]);

  const virtualItems = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      itemCount - 1,
      Math.floor((scrollTop + containerHeight) / itemHeight) + overscan
    );

    const items = [];
    for (let i = startIndex; i <= endIndex; i++) {
      items.push({
        index: i,
        offsetTop: i * itemHeight,
        height: itemHeight
      });
    }

    return items;
  }, [scrollTop, containerHeight, itemCount, itemHeight, overscan]);

  const totalHeight = itemCount * itemHeight;

  return {
    virtualItems,
    totalHeight,
    startIndex: virtualItems[0]?.index ?? 0,
    endIndex: virtualItems[virtualItems.length - 1]?.index ?? 0
  };
}
