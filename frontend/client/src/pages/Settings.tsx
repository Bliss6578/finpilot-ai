import { useEffect, useState } from "react";
import { Check, Link2, LogOut, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, Panel, SectionLabel } from "@/components/finpilot-ui";
import {
  fetchRazorpayStatus,
  beginRazorpayOAuth,
  syncRazorpay,
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
  const { session, logout } = useAuth();
  const [mode, setMode] = useState("Advisor");
  const [syncing, setSyncing] = useState(false);
  const [connection, setConnection] = useState<RazorpayStatus | null>(null);
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
  const refreshStatus = async () => {
    try {
      setConnection(await fetchRazorpayStatus());
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
        description: `${result.records_processed} payment record${result.records_processed === 1 ? "" : "s"} processed.`,
      });
    } catch {
      toast.error("Unable to sync Razorpay", {
        description:
          "Confirm that the FinPilot backend is running on port 8000.",
      });
    } finally {
      setSyncing(false);
    }
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
                </div>
              ) : (
                <button className="button-primary" onClick={() => void connectRazorpay()}>
                  <Link2 /> Connect Razorpay
                </button>
              )}
            </div>
            {!connection?.connected && !connection?.oauth_available && (
              <div className="connection-notice">
                FinPilot is ready for Razorpay OAuth. Add Partner development credentials to enable this button for client workspaces.
              </div>
            )}
          </Panel>
          <Panel className="settings-panel">
            <SectionLabel>Account access</SectionLabel>
            <h2>{session?.user.full_name}</h2>
            <p>{session?.user.email} · {session?.business.role} of {session?.business.name}</p>
            <button
              className="button-secondary"
              onClick={() => void signOut()}
            >
              <LogOut /> Sign out of FinPilot
            </button>
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
