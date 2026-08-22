import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";

export const RAZORPAY_OFFICIAL_URL = "https://razorpay.com/";

export function RazorpayOfficialLink({ children = "Razorpay", compact = false }: { children?: ReactNode; compact?: boolean }) {
  return <a
    className={`razorpay-official-link ${compact ? "compact" : ""}`}
    href={RAZORPAY_OFFICIAL_URL}
    target="_blank"
    rel="noreferrer noopener"
    aria-label="Open the official Razorpay website"
  >
    {children}<ArrowUpRight aria-hidden="true" />
  </a>;
}
