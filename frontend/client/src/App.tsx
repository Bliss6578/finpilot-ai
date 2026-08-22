import { lazy, Suspense, type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useEffect } from "react";
import { Route, Switch, useLocation } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import AppShell from "./components/layout/AppShell";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
const Home = lazy(() => import("./pages/Home"));
const AuthPage = lazy(() => import("./pages/Auth"));
const ForgotPasswordPage = lazy(() => import("./pages/AccountRecovery").then(module => ({ default: module.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import("./pages/AccountRecovery").then(module => ({ default: module.ResetPasswordPage })));
const VerifyEmailPage = lazy(() => import("./pages/AccountRecovery").then(module => ({ default: module.VerifyEmailPage })));
const AboutPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.AboutPage })));
const ContactPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.ContactPage })));
const DeliveryPolicyPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.DeliveryPolicyPage })));
const PricingPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.PricingPage })));
const PrivacyPolicyPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.PrivacyPolicyPage })));
const RefundPolicyPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.RefundPolicyPage })));
const TermsPage = lazy(() => import("./pages/PublicInfo").then(module => ({ default: module.TermsPage })));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Transactions = lazy(() => import("./pages/Transactions"));
const CashFlow = lazy(() => import("./pages/CashFlow"));
const AICFO = lazy(() => import("./pages/AICFO"));
const ScenarioLab = lazy(() => import("./pages/ScenarioLab"));
const Alerts = lazy(() => import("./pages/Alerts"));
const Intelligence = lazy(() => import("./pages/Intelligence"));
const Settings = lazy(() => import("./pages/Settings"));
const NotFound = lazy(() => import("./pages/NotFound"));

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
      <Route path="/intelligence" component={() => <RoutedPage><Intelligence /></RoutedPage>} />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider>
          <AuthProvider>
            <Toaster richColors position="top-right" />
            <Suspense fallback={<div className="auth-loading"><SparkLoader /> Loading workspace…</div>}><Router /></Suspense>
          </AuthProvider>
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
