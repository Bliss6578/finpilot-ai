import { type FormEvent, useEffect, useState } from "react";
import { Check, Copy, KeyRound, Link2, LogOut, MailCheck, RefreshCw, ShieldCheck, Unplug } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, Panel, SectionLabel } from "@/components/finpilot-ui";
import {
  fetchRazorpayStatus,
  beginRazorpayOAuth,
  connectRazorpayApiKeys,
  disconnectRazorpayApiKeys,
  revokeOtherSessions,
  requestEmailVerification,
  rotateRazorpayWebhookSecret,
  syncRazorpay,
  type RazorpayWebhookCredentials,
  type RazorpayStatus,
} from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";

const notifications = [
  "Cash flow risks",
  "Payment failures",
  "Refund spikes",
  "Settlement changes",
  "Unusual transactions",
  "Weekly finance report",
];
export default function Settings() {
  const { session, logout, changePassword, refresh: refreshSession } = useAuth();
  const [mode, setMode] = useState("Advisor");
  const [syncing, setSyncing] = useState(false);
  const [connection, setConnection] = useState<RazorpayStatus | null>(null);
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [changingPassword, setChangingPassword] = useState(false);
  const [revokingSessions, setRevokingSessions] = useState(false);
  const [sendingVerification, setSendingVerification] = useState(false);
  const [apiKeys, setApiKeys] = useState({ keyId: "", keySecret: "", confirmLive: false });
  const [connectingKeys, setConnectingKeys] = useState(false);
  const [disconnectingKeys, setDisconnectingKeys] = useState(false);
  const [rotatingWebhook, setRotatingWebhook] = useState(false);
  const [webhookCredentials, setWebhookCredentials] = useState<RazorpayWebhookCredentials | null>(null);
  const [toggles, setToggles] = useState<Record<string, boolean>>({
    "Cash flow risks": true,
    "Payment failures": true,
    "Refund spikes": true,
    "Settlement changes": false,
    "Unusual transactions": true,
    "Weekly finance report": true,
  });
  const signOut = async () => {
    try {
      await logout();
    } finally {
      window.location.assign("/signin");
    }
  };
  const updatePassword = async (event: FormEvent) => {
    event.preventDefault();
    if (passwords.next !== passwords.confirm) {
      toast.error("New passwords do not match");
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword(passwords.current, passwords.next);
      setPasswords({ current: "", next: "", confirm: "" });
      toast.success("Password updated", {
        description: "Other signed-in devices have been securely signed out.",
      });
    } catch (reason: any) {
      toast.error("Unable to change password", {
        description: reason?.response?.data?.detail ?? "Please check your current password and try again.",
      });
    } finally {
      setChangingPassword(false);
    }
  };
  const revokeSessions = async () => {
    setRevokingSessions(true);
    try {
      const result = await revokeOtherSessions();
      toast.success("Other sessions revoked", {
        description: result.revoked_sessions
          ? `${result.revoked_sessions} other session${result.revoked_sessions === 1 ? "" : "s"} signed out.`
          : "No other signed-in devices were found.",
      });
    } catch {
      toast.error("Unable to revoke other sessions");
    } finally {
      setRevokingSessions(false);
    }
  };
  const sendVerification = async () => {
    setSendingVerification(true);
    try {
      const result = await requestEmailVerification();
      toast.success(result.status === "recently_sent" ? "Verification email already sent" : "Verification email sent", {
        description: `Check ${session?.user.email}. The secure link expires after 24 hours.`,
      });
    } catch (reason: any) {
      toast.error("Unable to send verification email", {
        description: reason?.response?.data?.detail ?? "Please try again shortly.",
      });
    } finally {
      setSendingVerification(false);
    }
  };
  const refreshStatus = async () => {
    try {
      const next = await fetchRazorpayStatus();
      setConnection(next);
      if (next.connection_type === "api_key" && next.api_key_id) {
        setApiKeys(current => ({ ...current, keyId: current.keyId || next.api_key_id || "" }));
      }
    } catch {
      setConnection(null);
    }
  };
  useEffect(() => {
    void refreshStatus();
  }, []);
  const runSync = async () => {
    setSyncing(true);
    try {
      const result = await syncRazorpay();
      await refreshStatus();
      toast.success("Razorpay synchronized", {
        description: result.warnings?.length
          ? `${result.records?.payments ?? 0} payments imported. ${result.warnings.join(" ")}.`
          : result.records
          ? `${result.records.payments} payments, ${result.records.refunds} refunds and ${result.records.settlements} settlements processed.`
          : `${result.records_processed} Razorpay record${result.records_processed === 1 ? "" : "s"} processed.`,
      });
    } catch (reason: any) {
      toast.error("Unable to sync Razorpay", {
        description: reason?.response?.data?.detail ?? "Please try again shortly.",
      });
    } finally {
      setSyncing(false);
    }
  };
  const connectApiKeys = async (event: FormEvent) => {
    event.preventDefault();
    setConnectingKeys(true);
    try {
      const result = await connectRazorpayApiKeys(
        apiKeys.keyId.trim(),
        apiKeys.keySecret,
        apiKeys.confirmLive
      );
      setApiKeys({ keyId: result.key_id, keySecret: "", confirmLive: false });
      if (result.webhook_secret) {
        setWebhookCredentials({
          webhook_url: result.webhook_url,
          webhook_secret: result.webhook_secret,
        });
      }
      let initialSync = null;
      try {
        initialSync = await syncRazorpay();
      } catch (reason: any) {
        toast.warning("Razorpay connected, but the first import needs attention", {
          description: reason?.response?.data?.detail ?? "Use Sync now to retry the import.",
        });
      }
      await Promise.all([refreshStatus(), refreshSession()]);
      toast.success(`Razorpay ${result.mode === "live" ? "Live" : "Test"} Mode connected`, {
        description: initialSync
          ? `${initialSync.records?.payments ?? 0} existing payment${initialSync.records?.payments === 1 ? "" : "s"} imported. Copy the webhook details below for new events.`
          : result.webhook_secret
          ? "Copy the webhook URL and secret below, then use Sync now to import existing payments."
          : "The encrypted credentials were updated successfully.",
      });
    } catch (reason: any) {
      toast.error("Unable to connect Razorpay", {
        description: reason?.response?.data?.detail ?? "Check the Razorpay keys and try again.",
      });
    } finally {
      setConnectingKeys(false);
    }
  };
  const rotateWebhook = async () => {
    setRotatingWebhook(true);
    try {
      const result = await rotateRazorpayWebhookSecret();
      setWebhookCredentials(result);
      toast.success("New webhook secret generated", {
        description: "Update the webhook in Razorpay before sending more events.",
      });
    } catch (reason: any) {
      toast.error("Unable to rotate webhook secret", {
        description: reason?.response?.data?.detail ?? "Please try again shortly.",
      });
    } finally {
      setRotatingWebhook(false);
    }
  };
  const disconnectApiKeys = async () => {
    if (!window.confirm(`Disconnect Razorpay ${connection?.mode === "live" ? "Live" : "Test"} Mode from this FinPilot workspace?`)) return;
    setDisconnectingKeys(true);
    try {
      await disconnectRazorpayApiKeys();
      setWebhookCredentials(null);
      setApiKeys({ keyId: "", keySecret: "", confirmLive: false });
      await Promise.all([refreshStatus(), refreshSession()]);
      toast.success("Razorpay disconnected");
    } catch (reason: any) {
      toast.error("Unable to disconnect Razorpay", {
        description: reason?.response?.data?.detail ?? "Please try again shortly.",
      });
    } finally {
      setDisconnectingKeys(false);
    }
  };
  const copyValue = async (label: string, value: string) => {
    await navigator.clipboard.writeText(value);
    toast.success(`${label} copied`);
  };
  const connectRazorpay = async () => {
    try {
      const result = await beginRazorpayOAuth();
      window.location.assign(result.authorization_url);
    } catch (reason: any) {
      toast.error("Razorpay Partner connection is not ready", {
        description:
          reason?.response?.data?.detail ??
          "Add the Razorpay Partner OAuth credentials to the backend.",
      });
    }
  };
  const save = () =>
    toast.success("Preferences saved", {
      description: "FinPilot will use these settings in future analyses.",
    });
  const lastSync = connection?.last_sync
    ? new Date(connection.last_sync).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Never";
  const isLiveKey = apiKeys.keyId.trim().startsWith("rzp_live_");
  return (
    <>
      <PageHeader
        eyebrow="Operating controls"
        title="Your reserve policy is active"
        description="Razorpay connection and finance controls for this business."
      />
      <section className="settings-layout">
        <div className="settings-stack">
          <Panel className="settings-panel">
            <SectionLabel>Business profile</SectionLabel>
            <h2>Business context</h2>
            <p>This is used to make your finance insights more relevant.</p>
            <div className="setting-grid">
              <Setting label="Business name" value={session?.business.name ?? "Your business"} />
              <Setting label="Industry" value="E-commerce / Clothing" />
              <Setting label="Website" value="aurafashion.in" />
              <Setting label="Currency" value="INR — Indian Rupee" select />
            </div>
          </Panel>
          <Panel className="settings-panel">
            <SectionLabel>Data source</SectionLabel>
            <h2>Razorpay connection</h2>
            <p>
              FinPilot reads financial signals through your connected payment
              data.
            </p>
            <div className="connection-card">
              <div className="connection-mark">R</div>
              <div>
                <strong>Razorpay</strong>
                <span>
                  <Check />
                  {connection?.connected
                    ? `Connected · ${connection.mode} mode`
                    : "Not connected"}
                </span>
                <small>Last sync · {lastSync}</small>
              </div>
              {connection?.connected ? (
                <div className="connection-actions">
                  <button
                    className="button-secondary"
                    onClick={() => void runSync()}
                    disabled={syncing}
                  >
                    <RefreshCw className={syncing ? "spin" : ""} />
                    {syncing ? "Syncing…" : "Sync now"}
                  </button>
                  {connection.connection_type === "env_api_key" && connection.oauth_available && (
                    <button className="button-primary" onClick={() => void connectRazorpay()}>
                      <Link2 /> Connect your account
                    </button>
                  )}
                  {connection.connection_type === "api_key" && (
                    <button
                      className="button-secondary"
                      onClick={() => void disconnectApiKeys()}
                      disabled={disconnectingKeys}
                    >
                      <Unplug /> {disconnectingKeys ? "Disconnecting…" : "Disconnect"}
                    </button>
                  )}
                </div>
              ) : (
                connection?.oauth_available ? (
                  <button className="button-secondary" onClick={() => void connectRazorpay()}>
                    <Link2 /> Partner OAuth
                  </button>
                ) : null
              )}
            </div>
            {(!connection?.connected || connection.connection_type === "api_key") && (
              <form className="api-key-connect-form" onSubmit={connectApiKeys}>
                <div>
                  <SectionLabel>{connection?.connected ? "Update Razorpay credentials" : "Connect without Partner approval"}</SectionLabel>
                  <h3>Razorpay Test or Live API keys</h3>
                  <p>Credentials are verified by Razorpay and the Key Secret is encrypted before storage. FinPilot never displays it again.</p>
                </div>
                <div className="api-key-fields">
                  <label className="setting-field">
                    <span>Key ID</span>
                    <input
                      required
                      autoComplete="off"
                      placeholder="rzp_test_... or rzp_live_..."
                      value={apiKeys.keyId}
                      onChange={event => setApiKeys(current => ({ ...current, keyId: event.target.value, confirmLive: false }))}
                    />
                  </label>
                  <label className="setting-field">
                    <span>{connection?.connected ? "New Key Secret" : "Key Secret"}</span>
                    <input
                      required
                      type="password"
                      autoComplete="new-password"
                      placeholder={connection?.connected ? "Enter a replacement secret" : "Enter the secret shown by Razorpay"}
                      value={apiKeys.keySecret}
                      onChange={event => setApiKeys(current => ({ ...current, keySecret: event.target.value }))}
                    />
                  </label>
                </div>
                {isLiveKey && (
                  <label className="live-key-confirmation">
                    <input
                      type="checkbox"
                      checked={apiKeys.confirmLive}
                      onChange={event => setApiKeys(current => ({ ...current, confirmLive: event.target.checked }))}
                    />
                    <span>I own this Razorpay account and authorize FinPilot to read its real payment, refund and settlement data.</span>
                  </label>
                )}
                <button className="button-primary" type="submit" disabled={connectingKeys || (isLiveKey && !apiKeys.confirmLive)}>
                  <KeyRound /> {connectingKeys ? "Verifying…" : connection?.connected ? "Update encrypted keys" : "Verify and connect"}
                </button>
              </form>
            )}
            {connection?.connection_type === "api_key" && connection.webhook_url && (
              <div className="webhook-setup-card">
                <div>
                  <SectionLabel>Per-business webhook</SectionLabel>
                  <h3>Connect real-time events</h3>
                  <p>Add this URL and the secret below to Razorpay {connection.mode === "live" ? "Live" : "Test"} Mode. Razorpay keeps Test and Live webhooks separate.</p>
                </div>
                <div className="credential-row">
                  <span>Webhook URL</span>
                  <code>{connection.webhook_url}</code>
                  <button type="button" className="icon-button" aria-label="Copy webhook URL" onClick={() => void copyValue("Webhook URL", connection.webhook_url!)}><Copy /></button>
                </div>
                {webhookCredentials ? (
                  <div className="credential-row secret-row">
                    <span>Webhook Secret · shown once</span>
                    <code>{webhookCredentials.webhook_secret}</code>
                    <button type="button" className="icon-button" aria-label="Copy webhook secret" onClick={() => void copyValue("Webhook secret", webhookCredentials.webhook_secret)}><Copy /></button>
                  </div>
                ) : (
                  <p className="credential-hidden">The saved webhook secret is encrypted and hidden. Rotate it if you need a new one.</p>
                )}
                <button type="button" className="button-secondary" onClick={() => void rotateWebhook()} disabled={rotatingWebhook}>
                  <RefreshCw className={rotatingWebhook ? "spin" : ""} /> {rotatingWebhook ? "Generating…" : "Generate new webhook secret"}
                </button>
              </div>
            )}
            <div className="connection-notice">
              Direct Live keys are an owner-only transition option. Razorpay Partner OAuth remains the recommended production connection for a multi-client platform.
            </div>
          </Panel>
          <Panel className="settings-panel">
            <SectionLabel>Account access</SectionLabel>
            <h2>{session?.user.full_name}</h2>
            <p>{session?.user.email} · {session?.business.role} of {session?.business.name}</p>
            <div className={`email-verification-status ${session?.user.email_verified ? "verified" : "pending"}`}>
              <div><MailCheck /><span><strong>{session?.user.email_verified ? "Email verified" : "Email verification pending"}</strong><small>{session?.user.email_verified ? "Your account email has been confirmed." : "Verify your email to secure account recovery."}</small></span></div>
              {!session?.user.email_verified && <button type="button" className="button-secondary" onClick={() => void sendVerification()} disabled={sendingVerification}>{sendingVerification ? "Sending…" : "Send verification email"}</button>}
            </div>
            <form className="account-security-form" onSubmit={updatePassword}>
              <div className="setting-grid">
                <label className="setting-field">
                  <span>Current password</span>
                  <input required type="password" autoComplete="current-password" value={passwords.current} onChange={event => setPasswords(current => ({ ...current, current: event.target.value }))} />
                </label>
                <label className="setting-field">
                  <span>New password</span>
                  <input required minLength={10} type="password" autoComplete="new-password" value={passwords.next} onChange={event => setPasswords(current => ({ ...current, next: event.target.value }))} />
                </label>
                <label className="setting-field">
                  <span>Confirm new password</span>
                  <input required minLength={10} type="password" autoComplete="new-password" value={passwords.confirm} onChange={event => setPasswords(current => ({ ...current, confirm: event.target.value }))} />
                </label>
              </div>
              <div className="account-security-actions">
                <button className="button-primary" type="submit" disabled={changingPassword}>
                  <KeyRound /> {changingPassword ? "Updating…" : "Change password"}
                </button>
                <button className="button-secondary" type="button" onClick={() => void revokeSessions()} disabled={revokingSessions}>
                  <ShieldCheck /> {revokingSessions ? "Checking…" : "Sign out other devices"}
                </button>
                <button className="button-secondary" type="button" onClick={() => void signOut()}>
                  <LogOut /> Sign out of FinPilot
                </button>
              </div>
            </form>
          </Panel>
          <Panel className="settings-panel">
            <SectionLabel>Financial preferences</SectionLabel>
            <h2>Cash policy</h2>
            <p>
              FinPilot uses these thresholds when evaluating your future cash
              position.
            </p>
            <div className="setting-grid">
              <Setting label="Minimum cash reserve" value="₹1,00,000" />
              <Setting label="Forecast period" value="30 days" select />
              <Setting label="Monthly fixed expenses" value="₹2,10,000" />
              <Setting label="Risk sensitivity" value="Balanced" select />
            </div>
          </Panel>
          <Panel className="settings-panel">
            <SectionLabel>AI control mode</SectionLabel>
            <h2>How should FinPilot operate?</h2>
            <p>
              Choose the posture FinPilot takes when identifying financial
              opportunities and risks.
            </p>
            <div className="mode-grid">
              {[
                [
                  "Observer",
                  "FinPilot analyses data but does not suggest actions.",
                ],
                [
                  "Advisor",
                  "FinPilot provides recommendations and financial guidance.",
                ],
                [
                  "Autopilot",
                  "FinPilot prepares recommended actions for your approval.",
                ],
              ].map(([name, description]) => (
                <button
                  key={name}
                  onClick={() => setMode(name)}
                  className={`mode-option ${mode === name ? "active" : ""}`}
                >
                  <strong>{name}</strong>
                  <span>{description}</span>
                </button>
              ))}
            </div>
          </Panel>
          <Panel className="settings-panel">
            <SectionLabel>Notification preferences</SectionLabel>
            <h2>Keep Maya informed</h2>
            <div className="toggle-list">
              {notifications.map(name => (
                <button
                  className="toggle-row"
                  key={name}
                  onClick={() =>
                    setToggles(current => ({
                      ...current,
                      [name]: !current[name],
                    }))
                  }
                >
                  <span>{name}</span>
                  <i className={`switch ${toggles[name] ? "on" : ""}`}>
                    <i />
                  </i>
                </button>
              ))}
            </div>
          </Panel>
          <div className="save-bar">
            <button className="button-secondary">Discard</button>
            <button className="button-primary" onClick={save}>
              Save changes
            </button>
          </div>
        </div>
        <aside className="settings-rail">
          <Panel>
            <SectionLabel>Finance snapshot</SectionLabel>
            <h3>Current configuration</h3>
            <Preference label="Reserve" value="₹1,00,000" />
            <Preference label="Forecast horizon" value="30 days" />
            <Preference label="Risk sensitivity" value="Balanced" />
            <Preference label="AI mode" value={mode} />
          </Panel>
          <Panel>
            <SectionLabel>Data mode</SectionLabel>
            <h3>Live Razorpay Test Mode</h3>
            <p style={{ color: "#747D8E", fontSize: 11, lineHeight: 1.5 }}>
              Set VITE_DEMO_MODE=true only when you want sample records instead
              of backend data.
            </p>
          </Panel>
        </aside>
      </section>
    </>
  );
}
function Setting({
  label,
  value,
  select,
}: {
  label: string;
  value: string;
  select?: boolean;
}) {
  return (
    <label className="setting-field">
      <span>{label}</span>
      {select ? (
        <select defaultValue={value}>
          <option>{value}</option>
          <option>Conservative</option>
          <option>90 days</option>
        </select>
      ) : (
        <input defaultValue={value} />
      )}
    </label>
  );
}
function Preference({ label, value }: { label: string; value: string }) {
  return (
    <div className="preference-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
