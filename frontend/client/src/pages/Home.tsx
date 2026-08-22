import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  BellRing,
  BrainCircuit,
  ChartNoAxesCombined,
  CircleCheck,
  Menu,
  ReceiptIndianRupee,
  Sparkles,
  WalletCards,
} from "lucide-react";
import { Link } from "wouter";
import { CashFlowChart } from "@/components/finance-charts";
import "./landing.css";
import { RazorpayOfficialLink } from "@/components/RazorpayOfficialLink";
import { api } from "@/services/api";

const ease = [0.22, 1, 0.36, 1] as const;
const stages = [
  {
    number: "01",
    label: "Observe",
    title: "Every financial signal. One continuous view.",
    copy: "Payments, refunds, fees and settlements flow into FinPilot automatically.",
    icon: ReceiptIndianRupee,
    stat: "₹2,000",
    meta: "Captured via Razorpay",
  },
  {
    number: "02",
    label: "Understand",
    title: "Noise becomes operating intelligence.",
    copy: "FinPilot categorizes transactions and explains what changed across revenue, costs and cash.",
    icon: BrainCircuit,
    stat: "100%",
    meta: "Payment success",
  },
  {
    number: "03",
    label: "Predict",
    title: "See the cash position before it happens.",
    copy: "A forward-looking model combines settlement timing, spending and recurring obligations.",
    icon: ChartNoAxesCombined,
    stat: "18 days",
    meta: "Until reserve risk",
  },
  {
    number: "04",
    label: "Recommend",
    title: "Every warning arrives with a next move.",
    copy: "The AI CFO turns forecasts and anomalies into clear, explainable recommendations.",
    icon: Sparkles,
    stat: "₹3.8L",
    meta: "Receivables to collect",
  },
  {
    number: "05",
    label: "Act",
    title: "Move from insight to decision—without losing context.",
    copy: "Review evidence, run a scenario and prepare the right action from one workspace.",
    icon: CircleCheck,
    stat: "Ready",
    meta: "Decision plan",
  },
];

const capabilities = [
  {
    number: "01",
    title: "Cash flow forecasting",
    copy: "Know when your balance changes—and why.",
    icon: ChartNoAxesCombined,
  },
  {
    number: "02",
    title: "Payment intelligence",
    copy: "See failures, refunds and fees in context.",
    icon: ReceiptIndianRupee,
  },
  {
    number: "03",
    title: "Financial risk detection",
    copy: "Catch anomalies before they become losses.",
    icon: BellRing,
  },
  {
    number: "04",
    title: "AI CFO recommendations",
    copy: "Turn evidence into an executable next step.",
    icon: Sparkles,
  },
];

export default function Home() {
  const reduced = useReducedMotion();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    // Wake the API while visitors read the landing page so authentication is
    // normally ready by the time they choose Sign in or Get started.
    void api.get("/api/health", { timeout: 75_000 }).catch(() => undefined);
  }, []);

  return (
    <div className="landing">
      <header className="landing-nav">
        <Link href="/" className="landing-logo">
          <span>
            <Sparkles />
          </span>
          FinPilot
        </Link>
        <nav>
          <a href="#story">How it works</a>
          <Link href="/pricing">Pricing</Link>
          <Link href="/about">About</Link>
          <Link href="/contact">Contact</Link>
          <Link href="/signin">Sign in</Link>
        </nav>
        <Link href="/signup" className="landing-nav-cta">
          <span>Get started</span>
          <i>
            <ArrowRight />
          </i>
        </Link>
        <button
          className="landing-menu"
          aria-label="Open navigation"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(value => !value)}
        >
          <Menu />
        </button>
      </header>
      <AnimatePresence>
        {menuOpen && (
          <motion.nav
            className="landing-mobile-nav"
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
          >
            <a href="#story" onClick={() => setMenuOpen(false)}>
              How it works
            </a>
            <Link href="/pricing">Pricing</Link>
            <Link href="/about">About</Link>
            <Link href="/contact">Contact</Link>
            <Link href="/signin">Sign in</Link>
            <Link href="/signup">
              Get started <ArrowRight />
            </Link>
          </motion.nav>
        )}
      </AnimatePresence>
      <main>
        <section className="landing-hero">
          <div className="hero-wave-motion" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
          <div className="hero-kicker">
            <span>AI FINANCE CONTROLLER</span>
            <span><RazorpayOfficialLink compact>RAZORPAY CONNECTED · INDIA</RazorpayOfficialLink></span>
          </div>
          <h1>
            {["Finance", "that thinks", "ahead."].map((line, index) => (
              <span className={index === 2 ? "accent" : ""} key={line}>
                <motion.i
                  initial={reduced ? false : { y: "110%" }}
                  animate={{ y: 0 }}
                  transition={{
                    duration: 0.9,
                    delay: 0.08 + index * 0.1,
                    ease,
                  }}
                >
                  {line}
                </motion.i>
              </span>
            ))}
          </h1>
          <motion.div
            className="hero-bottom"
            initial={reduced ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.52, ease }}
          >
            <p>
              FinPilot watches the financial pulse of your business, predicts
              what comes next, and turns every signal into a decision.
            </p>
          </motion.div>
          <Link href="/signup" className="round-cta">
            <span>
              Explore
              <br />
              FinPilot
            </span>
            <ArrowRight />
          </Link>
          <motion.div
            className="hero-product"
            initial={reduced ? false : { opacity: 0, y: 70, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 1.05, delay: 0.62, ease }}
          >
            <div className="product-top">
              <div>
                <i />
                <i />
                <i />
              </div>
              <span>FINPILOT / COMMAND CENTER</span>
              <b>LIVE</b>
            </div>
            <div className="product-shell">
              <aside>
                <span className="mini-brand">
                  <Sparkles />
                </span>
                {[
                  WalletCards,
                  ReceiptIndianRupee,
                  ChartNoAxesCombined,
                  BrainCircuit,
                  BellRing,
                ].map((Icon, i) => (
                  <i className={i === 0 ? "active" : ""} key={i}>
                    <Icon />
                  </i>
                ))}
              </aside>
              <div className="product-main">
                <div className="mini-heading">
                  <div>
                    <small>FINANCIAL COMMAND CENTER</small>
                    <strong>Razorpay revenue ₹2,000</strong>
                  </div>
                  <span>Signals are live</span>
                </div>
                <div className="mini-metrics">
                  <div>
                    <small>CAPTURED</small>
                    <strong>₹2,000</strong>
                    <em>Live</em>
                  </div>
                  <div>
                    <small>SUCCESS RATE</small>
                    <strong>100%</strong>
                    <em>Healthy</em>
                  </div>
                  <div>
                    <small>PAYMENTS</small>
                    <strong>1</strong>
                    <em>Test mode</em>
                  </div>
                </div>
                <div className="mini-chart">
                  <CashFlowChart />
                </div>
              </div>
            </div>
          </motion.div>
        </section>
        <div className="landing-ticker">
          <div>
            OBSERVE <i /> UNDERSTAND <i /> PREDICT <i /> RECOMMEND <i /> ACT{" "}
            <i /> OBSERVE <i /> UNDERSTAND <i /> PREDICT <i /> RECOMMEND <i />{" "}
            ACT
          </div>
        </div>
        <ProductStory />
        <section className="statement" id="intelligence">
          <span>02 — THE DIFFERENCE</span>
          <h2>
            Traditional finance software tells you <em>what happened.</em>
            <br />
            FinPilot tells you <strong>what happens next.</strong>
          </h2>
          <div className="statement-foot">
            <p>
              Not another accounting dashboard.
              <br />A controller that never stops watching.
            </p>
            <Link href="/ai-cfo">
              Meet your AI CFO <ArrowRight />
            </Link>
          </div>
        </section>
        <section className="capabilities" id="product">
          <div className="section-index">
            <span>03 — INTELLIGENCE</span>
            <p>
              One connected system.
              <br />
              Four decisive capabilities.
            </p>
          </div>
          <h2>
            Built for the moment
            <br />
            after the numbers arrive.
          </h2>
          <div className="capability-list">
            {capabilities.map(({ number, title, copy, icon: Icon }) => (
              <Link href="/signup" className="capability-row" key={number}>
                <span>{number}</span>
                <h3>{title}</h3>
                <p>{copy}</p>
                <i>
                  <Icon />
                </i>
                <b>
                  <ArrowRight />
                </b>
              </Link>
            ))}
          </div>
        </section>
        <section className="landing-cta">
          <span>04 — START PREDICTING</span>
          <h2>
            Stop reacting
            <br />
            to your finances.
          </h2>
          <p>Connect Razorpay. See the signal. Make the next move.</p>
          <Link href="/signup" className="cta-pill">
            <span>Launch FinPilot</span>
            <i>
              <ArrowRight />
            </i>
          </Link>
          <div className="cta-orbit">
            <Sparkles />
          </div>
        </section>
      </main>
      <footer className="landing-footer">
        <Link href="/" className="landing-logo">
          <span>
            <Sparkles />
          </span>
          FinPilot
        </Link>
        <p>
          Your AI Finance Controller
          <br />
          for Razorpay businesses.
        </p>
        <div>
          <Link href="/about">About</Link>
          <Link href="/contact">Contact</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/refund-policy">Refunds</Link>
          <Link href="/delivery-policy">Digital delivery</Link>
          <Link href="/signin">Sign in</Link>
        </div>
        <small>© 2026 FinPilot AI</small>
      </footer>
    </div>
  );
}

function ProductStory() {
  const reduced = useReducedMotion();
  return (
    <section className="product-story story-flowing" id="story">
      <div className="story-flow-head">
        <span>01 — HOW FINPILOT WORKS</span>
        <h2>
          From financial data
          <br />
          to the next decision.
        </h2>
        <p>
          Five connected stages turn every payment signal into a confident next
          move.
        </p>
      </div>
      <div className="story-flow-grid">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <motion.article
              className="stage-card story-flow-card"
              key={stage.label}
              initial={reduced ? false : { opacity: 0, y: 38 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.18 }}
              transition={{ duration: 0.65, delay: (index % 2) * 0.08, ease }}
            >
              <div className="stage-icon">
                <Icon />
              </div>
              <span>
                {stage.number} / {stage.label}
              </span>
              <h3>{stage.title}</h3>
              <p>{stage.copy}</p>
              <div className="stage-stat">
                <strong>{stage.stat}</strong>
                <small>{stage.meta}</small>
              </div>
            </motion.article>
          );
        })}
      </div>
    </section>
  );
}
