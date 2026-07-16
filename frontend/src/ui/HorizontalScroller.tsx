import { type ReactNode, useLayoutEffect, useRef, useState } from "react";

export function HorizontalScroller({ children, className = "" }: { children: ReactNode; className?: string }) {
  const topRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [scrollWidth, setScrollWidth] = useState(0);

  useLayoutEffect(() => {
    const update = () => {
      const viewport = bottomRef.current;
      const content = contentRef.current;
      if (!viewport || !content) return;
      setScrollWidth(viewport.scrollWidth > viewport.clientWidth + 1 ? viewport.scrollWidth : 0);
    };
    update();
    const animationFrame = window.requestAnimationFrame(update);
    const postLayoutTimeouts = [0, 120, 360].map((delay) => window.setTimeout(update, delay));
    const resizeObserver = new ResizeObserver(update);
    if (bottomRef.current) resizeObserver.observe(bottomRef.current);
    if (contentRef.current) resizeObserver.observe(contentRef.current);

    // Child content can grow after an async list/Kanban request without
    // changing the wrapper's own dimensions. Observe that change too.
    const mutationObserver = new MutationObserver(update);
    if (contentRef.current) {
      mutationObserver.observe(contentRef.current, { attributes: true, childList: true, subtree: true });
    }
    window.addEventListener("resize", update);

    return () => {
      resizeObserver.disconnect();
      mutationObserver.disconnect();
      window.removeEventListener("resize", update);
      window.cancelAnimationFrame(animationFrame);
      postLayoutTimeouts.forEach((timeout) => window.clearTimeout(timeout));
    };
  }, [children]);

  useLayoutEffect(() => {
    const top = topRef.current;
    const bottom = bottomRef.current;
    if (!top || !bottom) return;

    const syncTopToBottom = () => {
      if (bottom.scrollLeft !== top.scrollLeft) bottom.scrollLeft = top.scrollLeft;
    };
    const syncBottomToTop = () => {
      if (top.scrollLeft !== bottom.scrollLeft) top.scrollLeft = bottom.scrollLeft;
    };
    top.addEventListener("scroll", syncTopToBottom, { passive: true });
    bottom.addEventListener("scroll", syncBottomToTop, { passive: true });
    return () => {
      top.removeEventListener("scroll", syncTopToBottom);
      bottom.removeEventListener("scroll", syncBottomToTop);
    };
  }, [scrollWidth]);

  return (
    <div className={`tp-horizontal-scroll ${className}`}>
      {scrollWidth ? <div aria-label="Rolagem horizontal superior" className="tp-horizontal-scroll-top" ref={topRef}><div className="tp-horizontal-scroll-spacer" style={{ width: scrollWidth }} /></div> : null}
      <div aria-label="Rolagem horizontal inferior" className="tp-horizontal-scroll-bottom" ref={bottomRef}>
        <div ref={contentRef}>{children}</div>
      </div>
    </div>
  );
}
