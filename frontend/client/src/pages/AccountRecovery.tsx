import axios from "axios";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { ArrowRight, CheckCircle2, KeyRound, MailCheck, Sparkles } from "lucide-react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import {
  confirmEmailVerification,
  requestPasswordReset,
  resetPassword,
} from "@/services/api";

function queryToken() {
  return new URLSearchParams(window.location.search).get("token") ?? "";
}

function RecoveryShell({ children }: { children: ReactNode }) {
  return (
    <main className="recovery-page">
      <section className="recovery-card">
        <Link href="/" className="auth-logo recovery-logo"><span><Sparkles /></span>Paymentor</Link>
        {children}
      </section>
    </main>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (reason) {
      setError(axios.isAxiosError(reason) ? reason.response?.data?.detail ?? "Unable to send the email." : "Unable to send the email.");
    } finally {
      setSubmitting(false);
    }
  };
  return <RecoveryShell>{sent ? <RecoveryResult icon={<MailCheck />} title="Check your email" text="If this address belongs to an active Paymentor account, a secure reset link has been sent." /> : <><span className="auth-step">ACCOUNT RECOVERY</span><h1>Reset your password</h1><p>Enter your account email. The reset link expires after one hour.</p><form className="recovery-form" onSubmit={submit}><label><span>Work email</span><input required type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} /></label>{error && <div className="auth-error">{error}</div>}<button className="auth-submit" disabled={submitting}>{submitting ? "Sending…" : "Send reset link"}<ArrowRight /></button></form></>}<Link href="/signin" className="recovery-back">Back to sign in</Link></RecoveryShell>;
}

export function ResetPasswordPage() {
  const [, navigate] = useLocation();
  const [passwords, setPasswords] = useState({ next: "", confirm: "" });
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (passwords.next !== passwords.confirm) return setError("Passwords do not match");
    const token = queryToken();
    if (!token) return setError("This reset link is missing its secure token");
    setSubmitting(true);
    setError("");
    try {
      await resetPassword(token, passwords.next);
      setComplete(true);
      window.setTimeout(() => navigate("/signin", { replace: true }), 1800);
    } catch (reason) {
      setError(axios.isAxiosError(reason) ? reason.response?.data?.detail ?? "Unable to reset the password." : "Unable to reset the password.");
    } finally {
      setSubmitting(false);
    }
  };
  return <RecoveryShell>{complete ? <RecoveryResult icon={<CheckCircle2 />} title="Password updated" text="Every previous session has been signed out. Redirecting you to sign in…" /> : <><span className="auth-step">SECURE RESET</span><KeyRound className="recovery-mark" /><h1>Choose a new password</h1><p>Use at least 10 characters. This link works only once.</p><form className="recovery-form" onSubmit={submit}><label><span>New password</span><input required minLength={10} type="password" autoComplete="new-password" value={passwords.next} onChange={event => setPasswords(current => ({ ...current, next: event.target.value }))} /></label><label><span>Confirm password</span><input required minLength={10} type="password" autoComplete="new-password" value={passwords.confirm} onChange={event => setPasswords(current => ({ ...current, confirm: event.target.value }))} /></label>{error && <div className="auth-error">{error}</div>}<button className="auth-submit" disabled={submitting}>{submitting ? "Updating…" : "Update password"}<ArrowRight /></button></form></>}<Link href="/signin" className="recovery-back">Back to sign in</Link></RecoveryShell>;
}

export function VerifyEmailPage() {
  const { session, loading, refresh } = useAuth();
  const [, navigate] = useLocation();
  const started = useRef(false);
  const [state, setState] = useState<"working" | "success" | "error">("working");
  const [error, setError] = useState("");
  useEffect(() => {
    if (loading) return;
    if (!session) {
      navigate(`/signin?next=${encodeURIComponent(window.location.pathname + window.location.search)}`, { replace: true });
      return;
    }
    if (started.current) return;
    started.current = true;
    const token = queryToken();
    if (!token) {
      setError("This verification link is missing its secure token");
      setState("error");
      return;
    }
    void confirmEmailVerification(token).then(async () => {
      await refresh();
      setState("success");
    }).catch(reason => {
      setError(axios.isAxiosError(reason) ? reason.response?.data?.detail ?? "Unable to verify this email." : "Unable to verify this email.");
      setState("error");
    });
  }, [loading, session, navigate, refresh]);
  return <RecoveryShell>{state === "working" ? <RecoveryResult icon={<MailCheck />} title="Verifying your email" text="Confirming this secure link…" /> : state === "success" ? <RecoveryResult icon={<CheckCircle2 />} title="Email verified" text="Your Paymentor account is now verified." /> : <RecoveryResult icon={<MailCheck />} title="Verification failed" text={error} />}<Link href={state === "success" ? "/dashboard" : "/settings"} className="recovery-back">Continue to Paymentor</Link></RecoveryShell>;
}

function RecoveryResult({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="recovery-result"><span>{icon}</span><h1>{title}</h1><p>{text}</p></div>;
}
