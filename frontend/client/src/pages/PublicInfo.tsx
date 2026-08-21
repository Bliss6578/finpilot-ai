import type { ReactNode } from "react";
import {
  ArrowRight,
  BadgeIndianRupee,
  Clock3,
  DatabaseZap,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link } from "wouter";
import "./public-pages.css";

const contactEmail = "ishita.hustlelab@gmail.com";
const updated = "21 August 2026";

type PublicShellProps = {
  index: string;
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
};

function PublicShell({ index, eyebrow, title, intro, children }: PublicShellProps) {
  return (
    <div className="public-site">
      <header className="public-nav">
        <Link href="/" className="public-logo">
          <span><Sparkles /></span>
          FinPilot
        </Link>
        <nav aria-label="Public navigation">
          <Link href="/about">About</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/contact">Contact</Link>
          <Link href="/signin">Sign in</Link>
        </nav>
        <Link href="/signup" className="public-nav-cta">
          Get started <ArrowRight />
        </Link>
      </header>

      <main>
        <section className="public-hero">
          <div className="public-hero-copy">
            <span>{index} — {eyebrow}</span>
            <h1>{title}</h1>
            <p>{intro}</p>
          </div>
          <div className="public-hero-mark" aria-hidden="true"><Sparkles /></div>
        </section>
        <article className="public-content">{children}</article>
      </main>

      <footer className="public-footer">
        <div>
          <Link href="/" className="public-logo"><span><Sparkles /></span>FinPilot</Link>
          <p>Finance intelligence for Razorpay businesses.</p>
        </div>
        <div className="public-footer-links">
          <Link href="/about">About</Link>
          <Link href="/contact">Contact</Link>
          <Link href="/pricing">Pricing</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <Link href="/refund-policy">Refund policy</Link>
          <Link href="/delivery-policy">Digital delivery</Link>
        </div>
        <small>© 2026 FinPilot AI · Private beta</small>
      </footer>
    </div>
  );
}

function PolicySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="policy-section">
      <h2>{title}</h2>
      <div>{children}</div>
    </section>
  );
}

function Updated() {
  return <p className="policy-updated">Last updated: {updated}</p>;
}

export function AboutPage() {
  return (
    <PublicShell index="01" eyebrow="ABOUT" title="A clearer financial operating picture." intro="FinPilot is a private-beta finance intelligence workspace being built for businesses that use Razorpay.">
      <div className="public-feature-grid">
        <section><DatabaseZap /><span>01</span><h2>Observe</h2><p>Bring payment, refund, fee and settlement signals into one continuous view.</p></section>
        <section><ShieldCheck /><span>02</span><h2>Understand</h2><p>Organise operating data so changes in revenue and cash are easier to investigate.</p></section>
        <section><Sparkles /><span>03</span><h2>Decide</h2><p>Develop forecasts and explainable recommendations that keep the evidence in view.</p></section>
      </div>
      <PolicySection title="What FinPilot is">
        <p>FinPilot is software for financial visibility and operational decision support. It is not a bank, payment aggregator, lender, accounting firm, or investment adviser. Razorpay remains the payment service provider for connected merchants.</p>
      </PolicySection>
      <PolicySection title="Private-beta status">
        <p>The product is currently under development and available only to approved testers. Some forecasting, anomaly detection, and AI features may be experimental, use sample data, or change before commercial release.</p>
      </PolicySection>
      <div className="public-callout"><span>Build with the signal in view.</span><Link href="/signup">Request beta access <ArrowRight /></Link></div>
    </PublicShell>
  );
}

export function ContactPage() {
  return (
    <PublicShell index="02" eyebrow="CONTACT" title="Talk to the FinPilot team." intro="Questions about beta access, privacy, security, or your connected Razorpay data can be sent to one place.">
      <div className="contact-card">
        <div className="contact-icon"><Mail /></div>
        <div><span>GENERAL, SUPPORT & PRIVACY</span><h2>{contactEmail}</h2><p>Include your FinPilot account email and a short description. Never send passwords, OTPs, Razorpay key secrets, or full card details.</p></div>
        <a href={`mailto:${contactEmail}`}>Write an email <ArrowRight /></a>
      </div>
      <div className="public-feature-grid compact">
        <section><ShieldCheck /><h2>Security</h2><p>Use the subject “Security report” for suspected vulnerabilities or unauthorised account access.</p></section>
        <section><DatabaseZap /><h2>Data request</h2><p>Use the subject “Privacy request” to ask for access, correction, export, or deletion.</p></section>
        <section><Clock3 /><h2>Private beta</h2><p>Support availability may be limited while the product remains in private beta.</p></section>
      </div>
      <p className="contact-warning"><strong>Before Razorpay review:</strong> make sure this mailbox exists and is monitored, or replace it with your verified business support email.</p>
    </PublicShell>
  );
}

export function PricingPage() {
  return (
    <PublicShell index="03" eyebrow="PRICING" title="Private beta. No subscription charge." intro="FinPilot is not currently collecting subscription payments. Approved beta users can test the workspace at ₹0.">
      <div className="pricing-card">
        <div><span>PRIVATE BETA</span><h2>Early access</h2><p>Explore the connected finance workspace while core product and security controls are being completed.</p></div>
        <strong><small>₹</small>0 <em>/ beta period</em></strong>
        <ul>
          <li>Razorpay connection and transaction visibility</li>
          <li>Dashboard and cash-flow workspace</li>
          <li>Experimental alerts, scenarios, and AI insights</li>
          <li>No automatic renewal or hidden charge</li>
        </ul>
        <Link href="/signup">Request access <ArrowRight /></Link>
      </div>
      <PolicySection title="Before paid plans begin">
        <p>Any future paid plan, taxes, billing frequency, renewal terms, and cancellation conditions will be displayed clearly before a user is asked to pay. FinPilot will not convert a beta account into a paid subscription without the account owner’s express confirmation.</p>
      </PolicySection>
      <PolicySection title="Razorpay charges">
        <p>Fees charged by Razorpay for a merchant’s own payment services are separate from FinPilot and are governed by the merchant’s agreement with Razorpay.</p>
      </PolicySection>
    </PublicShell>
  );
}

export function PrivacyPolicyPage() {
  return (
    <PublicShell index="04" eyebrow="PRIVACY POLICY" title="Your business data stays in context." intro="This policy explains what FinPilot collects, why it is used, and the choices available to account owners.">
      <Updated />
      <PolicySection title="1. Scope"><p>This policy applies to the FinPilot website, accounts, dashboard, and private-beta services. “FinPilot”, “we”, and “us” refer to the operator of this service.</p></PolicySection>
      <PolicySection title="2. Information we collect"><p>We may collect account details such as name, business name, work email, password hash, authentication and session records, support messages, product usage, device and log data. When an account owner connects Razorpay, we may receive authorised merchant, payment, refund, fee, settlement, and related transaction data.</p></PolicySection>
      <PolicySection title="3. How we use information"><p>We use information to create and secure accounts, provide dashboards, synchronise authorised Razorpay data, calculate product metrics, develop forecasts and alerts, troubleshoot the service, communicate about the account, prevent abuse, and comply with legal obligations.</p></PolicySection>
      <PolicySection title="4. Razorpay connection"><p>FinPilot should request only the permissions required for the connected features. Razorpay credentials and tokens must be handled server-side. Users can disconnect Razorpay from FinPilot settings or through their Razorpay account, subject to available integration controls.</p></PolicySection>
      <PolicySection title="5. Sharing"><p>We do not sell personal information. Information may be processed by infrastructure, database, monitoring, email, analytics, and AI service providers only as required to operate the service. We may also disclose information when required by law, to protect users, or during a business reorganisation with appropriate safeguards.</p></PolicySection>
      <PolicySection title="6. Security and retention"><p>We use reasonable technical and organisational safeguards, including access controls, encrypted transport, password hashing, and tenant separation. No system is completely secure. We retain data only for as long as needed for the service, legal obligations, dispute resolution, security, and legitimate business purposes, then delete or anonymise it where practical.</p></PolicySection>
      <PolicySection title="7. Your choices"><p>Subject to applicable law, you may request access, correction, export, or deletion of your account information. You may also withdraw a Razorpay connection. Some records may be retained where legally required or needed to prevent fraud and maintain security.</p></PolicySection>
      <PolicySection title="8. Children and changes"><p>FinPilot is a business service and is not intended for children. We may update this policy as the product changes; the updated date will appear above and material changes will be communicated where required.</p></PolicySection>
      <PolicySection title="9. Contact"><p>Send privacy questions or requests to <a href={`mailto:${contactEmail}`}>{contactEmail}</a>.</p></PolicySection>
    </PublicShell>
  );
}

export function TermsPage() {
  return (
    <PublicShell index="05" eyebrow="TERMS & CONDITIONS" title="Terms for using FinPilot." intro="These terms set the rules for private-beta access and use of the FinPilot service.">
      <Updated />
      <PolicySection title="1. Eligibility and acceptance"><p>You must be at least 18 years old, authorised to act for the business you register, and capable of entering a binding agreement. By creating or using an account, you agree to these terms and the Privacy Policy.</p></PolicySection>
      <PolicySection title="2. Accounts"><p>You are responsible for accurate registration information, protecting sign-in credentials, activity under your account, and promptly reporting suspected unauthorised access. One business must not access another business’s workspace without permission.</p></PolicySection>
      <PolicySection title="3. Razorpay and third-party services"><p>Connecting Razorpay authorises FinPilot to access data within the permissions shown during connection. Razorpay is a separate service with its own terms and privacy practices. FinPilot is not responsible for Razorpay availability, payment processing, settlements, disputes, or fees.</p></PolicySection>
      <PolicySection title="4. Financial information disclaimer"><p>FinPilot provides software-generated information and decision support. Outputs may be incomplete, delayed, experimental, or incorrect and are not financial, investment, accounting, tax, or legal advice. You remain responsible for verifying data and business decisions with qualified professionals where appropriate.</p></PolicySection>
      <PolicySection title="5. Acceptable use"><p>You must not misuse the service, violate law, upload malicious code, probe or bypass security, interfere with other users, reverse engineer restricted portions, access data without authority, or use FinPilot to facilitate fraud or prohibited activity.</p></PolicySection>
      <PolicySection title="6. Beta availability"><p>The service is provided as a private beta and may change, experience interruptions, contain errors, or have features removed. We may limit or suspend beta access for security, maintenance, abuse prevention, legal compliance, or product changes.</p></PolicySection>
      <PolicySection title="7. Intellectual property"><p>FinPilot and its original software, interface, branding, and content are owned by or licensed to the service operator. You retain rights in your business data and grant us the limited permission needed to process it to provide and improve the service.</p></PolicySection>
      <PolicySection title="8. Liability"><p>To the maximum extent permitted by law, the beta service is provided without warranties of uninterrupted operation or fitness for a particular purpose. FinPilot is not liable for decisions made solely from automated outputs, indirect losses, or failures of third-party services. Nothing here excludes rights or liabilities that cannot legally be excluded.</p></PolicySection>
      <PolicySection title="9. Termination and law"><p>You may stop using the service and request account deletion. We may end access for breach or legitimate operational reasons. These terms are governed by the laws of India, and disputes will be handled by courts with lawful jurisdiction.</p></PolicySection>
      <PolicySection title="10. Contact"><p>Questions about these terms can be sent to <a href={`mailto:${contactEmail}`}>{contactEmail}</a>.</p></PolicySection>
    </PublicShell>
  );
}

export function RefundPolicyPage() {
  return (
    <PublicShell index="06" eyebrow="CANCELLATION & REFUND" title="A simple policy for the beta period." intro="FinPilot currently charges ₹0 for approved private-beta access, so there is no FinPilot subscription payment to cancel or refund.">
      <Updated />
      <div className="policy-highlight"><BadgeIndianRupee /><div><span>CURRENT PRICE</span><strong>₹0</strong><p>No automatic billing during private beta.</p></div></div>
      <PolicySection title="Cancel beta access"><p>You may stop using FinPilot at any time. You can disconnect Razorpay and request account closure by contacting support. Access may remain available until the closure request is completed.</p></PolicySection>
      <PolicySection title="Future paid services"><p>Before paid subscriptions are offered, FinPilot will publish the price, billing frequency, renewal, cancellation deadline, refund eligibility, and processing timeline. Users will be asked to accept those terms before any charge is made.</p></PolicySection>
      <PolicySection title="Razorpay merchant fees"><p>This policy covers charges made by FinPilot only. It does not cover payment processing fees, reversals, disputes, or other amounts charged by Razorpay under a merchant’s separate Razorpay agreement.</p></PolicySection>
      <PolicySection title="Contact"><p>For billing or cancellation questions, email <a href={`mailto:${contactEmail}`}>{contactEmail}</a>.</p></PolicySection>
    </PublicShell>
  );
}

export function DeliveryPolicyPage() {
  return (
    <PublicShell index="07" eyebrow="DIGITAL DELIVERY" title="Delivered online. Nothing is shipped." intro="FinPilot is a software service. Access and product features are delivered electronically through a secured web account.">
      <Updated />
      <div className="public-feature-grid compact">
        <section><Mail /><h2>Account access</h2><p>After registration is accepted, users receive access through the FinPilot sign-in page.</p></section>
        <section><DatabaseZap /><h2>Data connection</h2><p>Razorpay data becomes available only after the authorised business owner completes the connection.</p></section>
        <section><ShieldCheck /><h2>No physical shipping</h2><p>FinPilot does not sell or ship physical goods. Shipping charges and tracking do not apply.</p></section>
      </div>
      <PolicySection title="Delivery timing"><p>Private-beta account access is normally available after successful registration, subject to approval, service availability, and any required verification. Connected data may take time to synchronise depending on Razorpay and system availability.</p></PolicySection>
      <PolicySection title="Delivery problems"><p>If you cannot sign in, connect an authorised account, or see expected data, contact <a href={`mailto:${contactEmail}`}>{contactEmail}</a>. Do not email passwords, OTPs, key secrets, or full payment credentials.</p></PolicySection>
      <PolicySection title="Changes during beta"><p>Features, access limits, and availability may change while FinPilot is in private beta. Material changes affecting a user’s access will be communicated where practical.</p></PolicySection>
    </PublicShell>
  );
}
