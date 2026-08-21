import type { ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useEffect } from "react";
import { Route, Switch, useLocation } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import AppShell from "./components/layout/AppShell";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Alerts from "./pages/Alerts";
import AICFO from "./pages/AICFO";
import CashFlow from "./pages/CashFlow";
import Dashboard from "./pages/Dashboard";
import NotFound from "./pages/NotFound";
import ScenarioLab from "./pages/ScenarioLab";
import Settings from "./pages/Settings";
import Transactions from "./pages/Transactions";
import Home from "./pages/Home";
import AuthPage from "./pages/Auth";
import { ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage } from "./pages/AccountRecovery";
import {
  AboutPage,
  ContactPage,
  DeliveryPolicyPage,
  PricingPage,
  PrivacyPolicyPage,
  RefundPolicyPage,
  TermsPage,
} from "./pages/PublicInfo";

/** Flight Deck design reminder: persistent navigation keeps every page inside one coherent financial decision workspace. */
function RoutedPage({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const [, navigate] = useLocation();
  useEffect(() => {
    if (!loading && !session) navigate("/signin", { replace: true });
  }, [loading, session, navigate]);
  if (loading) {
    return <div className="auth-loading"><SparkLoader /> Securing your workspace…</div>;
  }
  if (!session) return null;
  return <AppShell>{children}</AppShell>;
}

function SparkLoader() {
  return <span className="auth-loading-mark">✦</span>;
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/signin" component={() => <AuthPage mode="signin" />} />
      <Route path="/signup" component={() => <AuthPage mode="signup" />} />
      <Route path="/forgot-password" component={ForgotPasswordPage} />
      <Route path="/reset-password" component={ResetPasswordPage} />
      <Route path="/verify-email" component={VerifyEmailPage} />
      <Route path="/about" component={AboutPage} />
      <Route path="/contact" component={ContactPage} />
      <Route path="/pricing" component={PricingPage} />
      <Route path="/privacy" component={PrivacyPolicyPage} />
      <Route path="/terms" component={TermsPage} />
      <Route path="/refund-policy" component={RefundPolicyPage} />
      <Route path="/delivery-policy" component={DeliveryPolicyPage} />
      <Route
        path="/dashboard"
        component={() => (
          <RoutedPage>
            <Dashboard />
          </RoutedPage>
        )}
      />
      <Route
        path="/transactions"
        component={() => (
          <RoutedPage>
            <Transactions />
          </RoutedPage>
        )}
      />
      <Route
        path="/cash-flow"
        component={() => (
          <RoutedPage>
            <CashFlow />
          </RoutedPage>
        )}
      />
      <Route
        path="/ai-cfo"
        component={() => (
          <RoutedPage>
            <AICFO />
          </RoutedPage>
        )}
      />
      <Route
        path="/scenario-lab"
        component={() => (
          <RoutedPage>
            <ScenarioLab />
          </RoutedPage>
        )}
      />
      <Route
        path="/alerts"
        component={() => (
          <RoutedPage>
            <Alerts />
          </RoutedPage>
        )}
      />
      <Route
        path="/settings"
        component={() => (
          <RoutedPage>
            <Settings />
          </RoutedPage>
        )}
      />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <AuthProvider>
            <Toaster richColors position="top-right" />
            <Router />
          </AuthProvider>
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
