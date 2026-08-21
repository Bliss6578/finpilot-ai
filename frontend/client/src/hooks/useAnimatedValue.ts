import { useEffect, useRef, useState } from "react";
import { useInView, useReducedMotion } from "framer-motion";

function renderValue(template: string, current: number, decimals: number) {
  const match = template.match(/[\d,.]+/);
  if (!match || match.index === undefined) return template;
  const prefix = template.slice(0, match.index);
  const suffix = template.slice(match.index + match[0].length);
  const formatted = current.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return `${prefix}${formatted}${suffix}`;
}

export function useAnimatedValue(value: string, duration = 850) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-8% 0px" });
  const reducedMotion = useReducedMotion();
  const match = value.match(/[\d,.]+/);
  const target = match ? Number(match[0].replace(/,/g, "")) : Number.NaN;
  const decimals = match?.[0].includes(".") ? match[0].split(".")[1].length : 0;
  const [display, setDisplay] = useState(() => Number.isFinite(target) ? renderValue(value, reducedMotion ? target : 0, decimals) : value);

  useEffect(() => {
    if (!inView || !Number.isFinite(target)) return;
    if (reducedMotion) { setDisplay(value); return; }
    const started = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(renderValue(value, target * eased, decimals));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [decimals, duration, inView, reducedMotion, target, value]);
  return { ref, display };
}
