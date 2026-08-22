import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
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
  ShieldAlert,
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
import { useDateRange, type DateRangeDays } from "@/contexts/DateRangeContext";

const navigation = [
  { href: "/dashboard", label: "Command Center", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: ReceiptIndianRupee },
  { href: "/cash-flow", label: "Cash Flow", icon: ChartNoAxesCombined },
  { href: "/ai-cfo", label: "AI CFO", icon: Sparkles },
  { href: "/scenario-lab", label: "Scenario Lab", icon: FlaskConical },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/intelligence", label: "Intelligence", icon: ShieldAlert },
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
  "/intelligence": "Intelligence",
  "/settings": "Settings",
};

const pageDescriptions: Record<string, string> = {
  "/dashboard": "Read the business signal and decide what needs attention.",
  "/transactions": "Trace every payment behind the financial picture.",
  "/cash-flow": "Look forward before the balance becomes a constraint.",
  "/ai-cfo": "Turn live evidence into a clear financial recommendation.",
  "/scenario-lab": "Test the cash impact before committing to a decision.",
  "/alerts": "Prioritize the signals that can materially change cash.",
  "/intelligence": "Detect leakage, reconcile settlements and approve safe actions.",
  "/settings": "Control the data, thresholds and operating posture.",
};

export default function AppShell({ children }: { children: ReactNode }) {
  const [location, navigate] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [compact, setCompact] = useState(false);
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const [dateOpen, setDateOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInput = useRef<HTMLInputElement>(null);
  const { days, setDays } = useDateRange();
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
  const searchResults = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const searchable = navigation.map(item => ({
      ...item,
      description: pageDescriptions[item.href] ?? "Open this Paymentor workspace page.",
    }));
    return query
      ? searchable.filter(item => `${item.label} ${item.description}`.toLowerCase().includes(query))
      : searchable;
  }, [searchQuery]);
  useEffect(() => {
    if (!session) return;
    fetchFinancialAlerts(false).then(result => setUnreadAlerts(result.unread)).catch(() => setUnreadAlerts(0));
  }, [session, location]);
  useEffect(() => {
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [location, reducedMotion]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setDateOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
  useEffect(() => {
    if (!searchOpen) return;
    const frame = requestAnimationFrame(() => searchInput.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [searchOpen]);

  const chooseRange = (nextDays: DateRangeDays) => {
    setDays(nextDays);
    setDateOpen(false);
  };

  const openSearchResult = (href: string) => {
    setSearchOpen(false);
    setSearchQuery("");
    navigate(href);
  };
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
        <Link href="/" className="sidebar-brand" aria-label="Paymentor home">
          <div className="brand-mark" aria-hidden="true">
            <Sparkles />
          </div>
          <div>
            <strong>
              Paymentor
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
              <span className="mobile-kicker">PAYMENTOR</span>
              <strong>
                {String(activeIndex + 1).padStart(2, "0")} /{" "}
                {pageTitles[activePath] ?? "Paymentor"}
              </strong>
            </div>
          </div>
          <div className="topbar-actions">
            <div className="topbar-popover-wrap">
              <button
                className="topbar-button date-button"
                aria-haspopup="menu"
                aria-expanded={dateOpen}
                onClick={() => setDateOpen(value => !value)}
              >
                <CalendarDays />
                Last {days} days
              </button>
              {dateOpen && (
                <div className="date-range-menu" role="menu" aria-label="Financial date range">
                  <span>Workspace period</span>
                  {([7, 30, 90] as DateRangeDays[]).map(option => (
                    <button key={option} role="menuitemradio" aria-checked={days === option} className={days === option ? "active" : ""} onClick={() => chooseRange(option)}>
                      Last {option} days
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button className="icon-button search-button" aria-label="Search Paymentor" title="Search (⌘K)" onClick={() => setSearchOpen(true)}>
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
              Ask Paymentor
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
              {String(activeIndex + 1).padStart(2, "0")} — PAYMENTOR OPERATING
              SYSTEM
            </span>
            <p>{pageDescriptions[activePath]}</p>
          </div>
          {children}
          <Link href={nextPage.href} className="route-continuation">
            <span>Continue through Paymentor</span>
            <strong>{nextPage.label}</strong>
            <i>
              <ChevronRight />
            </i>
          </Link>
        </motion.main>
      </div>
      {searchOpen && (
        <div className="global-search-backdrop" role="presentation" onMouseDown={() => setSearchOpen(false)}>
          <section className="global-search-dialog" role="dialog" aria-modal="true" aria-label="Search Paymentor" onMouseDown={event => event.stopPropagation()}>
            <div className="global-search-input">
              <Search />
              <input ref={searchInput} value={searchQuery} onChange={event => setSearchQuery(event.target.value)} placeholder="Search pages, tools and financial workflows…" />
              <kbd>ESC</kbd>
            </div>
            <div className="global-search-results">
              <small>{searchQuery ? "MATCHING WORKFLOWS" : "PAYMENTOR WORKSPACE"}</small>
              {searchResults.length ? searchResults.map(({ href, label, icon: Icon, description }) => (
                <button key={href} onClick={() => openSearchResult(href)}>
                  <i><Icon /></i>
                  <span><strong>{label}</strong><small>{description}</small></span>
                  <ChevronRight />
                </button>
              )) : <p>No Paymentor page matches “{searchQuery}”.</p>}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
