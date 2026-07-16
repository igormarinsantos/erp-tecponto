import { type ReactNode, useEffect, useRef, useState } from "react";

export function HorizontalScroller({ children, className = "" }: { children: ReactNode; className?: string }) {
  const topRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [scrollWidth, setScrollWidth] = useState(0);

  useEffect(() => {
    const update = () => {
      const viewport = bottomRef.current;
      const content = contentRef.current;
      if (!viewport || !content) return;
      setScrollWidth(content.scrollWidth > viewport.clientWidth + 1 ? content.scrollWidth : 0);
    };
    update();
    const observer = new ResizeObserver(update);
    if (bottomRef.current) observer.observe(bottomRef.current);
    if (contentRef.current) observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, []);

  const sync = (source: HTMLDivElement, target: HTMLDivElement | null) => {
    if (target && target.scrollLeft !== source.scrollLeft) target.scrollLeft = source.scrollLeft;
  };

  return (
    <div className={`tp-horizontal-scroll ${className}`}>
      {scrollWidth ? <div aria-hidden="true" className="tp-horizontal-scroll-top" onScroll={(event) => sync(event.currentTarget, bottomRef.current)} ref={topRef}><div style={{ width: scrollWidth }} /></div> : null}
      <div className="tp-horizontal-scroll-bottom" onScroll={(event) => sync(event.currentTarget, topRef.current)} ref={bottomRef}>
        <div ref={contentRef}>{children}</div>
      </div>
    </div>
  );
}
