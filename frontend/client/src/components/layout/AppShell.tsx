import { type ReactNode, useEffect, useState } from "react";
import {
  Bell,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronRight,
  FlaskConical,
  LayoutDashboard,
  Menu,
  ReceiptIndianRupee,
  Search,
  Settings,
  Sparkles,
  ArrowUpRight,
  LogOut,
  X,
} from "lucide-react";
import { Link, useLocation } from "wouter";
import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { fetchFinancialAlerts } from "@/services/api";
import { RazorpayOfficialLink } from "@/components/RazorpayOfficialLink";

const navigation = [
  { href: "/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: ReceiptIndianRupee },
  { href: "/cash-flow", label: "Cash Flow", icon: ChartNoAxesCombined },
  { href: "/ai-cfo", label: "AI CFO", icon: Sparkles },
  { href: "/scenario-lab", label: "Scenario Lab", icon: FlaskConical },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

const pageTitles: Record<string, string> = {
  "/": "Command Center",
  "/dashboard": "Command Center",
  "/transactions": "Transactions",
  "/cash-flow": "Cash Flow",
  "/ai-cfo": "AI CFO",
  "/scenario-lab": "Scenario Lab",
  "/alerts": "Financial Alerts",
  "/settings": "Settings",
};

const pageDescriptions: Record<string, string> = {
  "/dashboard": "Read the business signal and decide what needs attention.",
  "/transactions": "Trace every payment behind the financial picture.",
  "/cash-flow": "Look forward before the balance becomes a constraint.",
  "/ai-cfo": "Turn live evidence into a clear financial recommendation.",
  "/scenario-lab": "Test the cash impact before committing to a decision.",
  "/alerts": "Prioritize the signals that can materially change cash.",
  "/settings": "Control the data, thresholds and operating posture.",
};

export default function AppShell({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [compact, setCompact] = useState(false);
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const { session, logout } = useAuth();
  const businessName = session?.business.name ?? "Business";
  const userName = session?.user.full_name ?? "User";
  const initials = businessName.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
  const userInitial = userName[0]?.toUpperCase() ?? "U";
  const signOut = async () => {
    try {
      await logout();
    } finally {
      window.location.assign("/signin");
    }
  };
  const reducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, {
    stiffness: 180,
    damping: 28,
    mass: 0.25,
  });
  const activePath = location === "/" ? "/dashboard" : location;
  const activeIndex = Math.max(
    0,
    navigation.findIndex(item => item.href === activePath)
  );
  const nextPage = navigation[(activeIndex + 1) % navigation.length];
  useEffect(() => {
    if (!session) return;
    fetchFinancialAlerts(false).then(result => setUnreadAlerts(result.unread)).catch(() => setUnreadAlerts(0));
  }, [session, location]);
  useEffect(() => {
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [location, reducedMotion]);
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      setCompact(window.scrollY > 56);
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);
  useEffect(() => {
    if (reducedMotion) return;
    let observer: IntersectionObserver | undefined;
    const frame = requestAnimationFrame(() => {
      const nodes = document.querySelectorAll(
        ".page-content > *:not(.drawer-backdrop):not(.transaction-drawer), .metrics-grid > *, .summary-cards > *, .decision-stack > *, .two-up > *, .alerts-list > *"
      );
      observer = new IntersectionObserver(
        entries =>
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              entry.target.classList.add("motion-visible");
              observer?.unobserve(entry.target);
            }
          }),
        { threshold: 0.12, rootMargin: "0px 0px -7%" }
      );
      nodes.forEach((node, index) => {
        node.classList.add("reveal-item");
        (node as HTMLElement).style.setProperty(
          "--reveal-order",
          String(index % 4)
        );
        observer?.observe(node);
      });
    });
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [location, reducedMotion]);

  return (
    <div className={`app-shell ${reducedMotion ? "" : "motion-enabled"}`}>
      <motion.div
        className="scroll-progress"
        style={{ scaleX: reducedMotion ? 0 : progress }}
      />
      <button
        className={`mobile-backdrop ${mobileOpen ? "open" : ""}`}
        aria-label="Close navigation"
        onClick={() => setMobileOpen(false)}
      />
      <aside
        className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}
        aria-label="Primary navigation"
      >
        <Link href="/" className="sidebar-brand" aria-label="FinPilot home">
          <div className="brand-mark" aria-hidden="true">
            <Sparkles />
          </div>
          <div>
            <strong>
              FinPilot <em>AI</em>
            </strong>
            <span>Finance Intelligence</span>
          </div>
          <button
            className="mobile-close"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          >
            <X />
          </button>
        </Link>
        <nav>
          {navigation.map(({ href, label, icon: Icon }, index) => (
            <Link
              key={href}
              href={href}
              className={`nav-item ${activePath === href ? "active" : ""}`}
            >
              <Icon />
              <small>{String(index + 1).padStart(2, "0")}</small>
              <span>{label}</span>
              {href === "/alerts" && unreadAlerts ? <b>{unreadAlerts}</b> : null}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Link href="/" className="site-return">
            Public experience <ArrowUpRight />
          </Link>
          <div className="source-status">
            <span>
              <i />
              <RazorpayOfficialLink compact>{session?.razorpay_connected ? "Razorpay Connected" : "Razorpay not connected"}</RazorpayOfficialLink>
            </span>
            <small>
              {session?.razorpay_connected
                ? `${session.razorpay_mode === "live" ? "Live" : "Test"} business data`
                : "Connect in Settings"}
            </small>
          </div>
          <div className="business-card">
            <div className="avatar">{initials}</div>
            <div>
              <strong>{businessName}</strong>
              <span>{session?.business.role ?? "Member"} · {userName}</span>
            </div>
            <ChevronRight />
          </div>
          <button
            className="sidebar-logout"
            onClick={() => void signOut()}
          >
            <LogOut /> Sign out
          </button>
          <span className={`demo-badge ${session?.razorpay_mode === "live" ? "live" : ""}`}>
            {session?.razorpay_mode === "live" ? "LIVE MODE" : "TEST MODE"}
          </span>
        </div>
      </aside>
      <div className="workspace">
        <header className={`topbar ${compact ? "compact" : ""}`}>
          <div className="topbar-title">
            <button
              className="mobile-menu"
              aria-label="Open menu"
              onClick={() => setMobileOpen(true)}
            >
              <Menu />
            </button>
            <div>
              <span className="mobile-kicker">FINPILOT AI</span>
              <strong>
                {String(activeIndex + 1).padStart(2, "0")} /{" "}
                {pageTitles[activePath] ?? "FinPilot AI"}
              </strong>
            </div>
          </div>
          <div className="topbar-actions">
            <button className="topbar-button date-button">
              <CalendarDays />
              Last 30 days
            </button>
            <button className="icon-button search-button" aria-label="Search">
              <Search />
            </button>
            <Link
              href="/alerts"
              className="icon-button notification-button"
              aria-label="Notifications"
            >
              <Bell />
              {unreadAlerts ? <i /> : null}
            </Link>
            <Link href="/ai-cfo" className="ask-button">
              <Sparkles />
              Ask FinPilot
            </Link>
            <div className="top-avatar" aria-label={`${userName}'s profile`}>
              {userInitial}
            </div>
          </div>
        </header>
        <motion.main
          key={location}
          className="page-content"
          initial={reducedMotion ? false : { opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.48, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="product-chapter" aria-hidden="true">
            <span>
              {String(activeIndex + 1).padStart(2, "0")} — FINPILOT OPERATING
              SYSTEM
            </span>
            <p>{pageDescriptions[activePath]}</p>
          </div>
          {children}
          <Link href={nextPage.href} className="route-continuation">
            <span>Continue through FinPilot</span>
            <strong>{nextPage.label}</strong>
            <i>
              <ChevronRight />
            </i>
          </Link>
        </motion.main>
      </div>
    </div>
  );
}
