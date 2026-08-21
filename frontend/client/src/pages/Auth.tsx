import { type FormEvent, useEffect, useState } from "react";
import axios from "axios";
import { ArrowRight, Eye, EyeOff, ShieldCheck, Sparkles } from "lucide-react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";

export default function AuthPage({ mode }: { mode: "signin" | "signup" }) {
  const { session, loading, login, signup } = useAuth();
  const [, navigate] = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [values, setValues] = useState({
    full_name: "",
    business_name: "",
    email: "",
    password: "",
  });

  useEffect(() => {
    if (!loading && session) navigate("/dashboard", { replace: true });
  }, [loading, session, navigate]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      if (mode === "signup") {
        await signup(values);
      } else {
        await login(values.email, values.password);
      }
      navigate("/dashboard", { replace: true });
    } catch (reason) {
      if (axios.isAxiosError(reason)) {
        if (reason.code === "ECONNABORTED") {
          setError("FinPilot's secure service is still waking up. Please try once more in a moment.");
        } else if (!reason.response) {
          setError("Unable to reach the secure service. Check your connection and try again.");
        } else {
          setError(reason.response.data?.detail ?? "Unable to continue. Please try again.");
        }
      } else {
        setError("Unable to continue. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link href="/" className="auth-logo">
          <span><Sparkles /></span>
          FinPilot
        </Link>
        <div className="auth-story-copy">
          <span>FINANCE INTELLIGENCE / FOR RAZORPAY BUSINESSES</span>
          <h1>Your numbers.<br />Your workspace.<br /><em>Your next move.</em></h1>
          <p>Every FinPilot business is isolated, encrypted and connected only after its owner grants access.</p>
        </div>
        <div className="auth-trust"><ShieldCheck /> Secure business workspace · Private by default</div>
      </section>
      <section className="auth-form-side">
        <div className="auth-form-card">
          <span className="auth-step">{mode === "signup" ? "01 — CREATE WORKSPACE" : "WELCOME BACK"}</span>
          <h2>{mode === "signup" ? "Start with your business" : "Sign in to FinPilot"}</h2>
          <p>{mode === "signup" ? "Create your account, then connect Razorpay securely." : "Continue to your financial command center."}</p>
          <form onSubmit={submit}>
            {mode === "signup" && (
              <div className="auth-grid">
                <label>
                  <span>Your name</span>
                  <input required minLength={2} autoComplete="name" value={values.full_name} onChange={event => setValues(current => ({ ...current, full_name: event.target.value }))} placeholder="Ishita Sarkar" />
                </label>
                <label>
                  <span>Business name</span>
                  <input required minLength={2} autoComplete="organization" value={values.business_name} onChange={event => setValues(current => ({ ...current, business_name: event.target.value }))} placeholder="Aura Fashion" />
                </label>
              </div>
            )}
            <label>
              <span>Work email</span>
              <input required type="email" autoComplete="email" value={values.email} onChange={event => setValues(current => ({ ...current, email: event.target.value }))} placeholder="you@business.com" />
            </label>
            <label>
              <span>Password</span>
              <div className="password-field">
                <input required minLength={mode === "signup" ? 10 : 1} type={showPassword ? "text" : "password"} autoComplete={mode === "signup" ? "new-password" : "current-password"} value={values.password} onChange={event => setValues(current => ({ ...current, password: event.target.value }))} placeholder={mode === "signup" ? "At least 10 characters" : "Your password"} />
                <button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff /> : <Eye />}</button>
              </div>
            </label>
            {error && <div className="auth-error">{error}</div>}
            <button className="auth-submit" disabled={submitting}>
              {submitting ? "Securing workspace…" : mode === "signup" ? "Create FinPilot account" : "Sign in"}
              {!submitting && <ArrowRight />}
            </button>
          </form>
          <div className="auth-switch">
            {mode === "signup" ? "Already have an account?" : "New to FinPilot?"}{" "}
            <Link href={mode === "signup" ? "/signin" : "/signup"}>{mode === "signup" ? "Sign in" : "Create an account"}</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
