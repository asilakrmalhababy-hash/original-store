import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { StoreProvider } from "./contexts/StoreContext";
import { CustomerProvider } from "./contexts/CustomerContext";
import Home from "./pages/Home";
import { lazy, Suspense } from "react";
const AdminLazy = lazy(() => import("./pages/Admin"));
function Admin(props: any) { return <Suspense fallback={<div style={{padding:40,textAlign:"center"}}>جاري تحميل لوحة الإدارة...</div>}><AdminLazy {...props} /></Suspense>; }

function Router() {
  return <Switch>
    <Route path="/admin/:section?" component={Admin} />
    <Route path="/Admin/:section?" component={Admin} />
    <Route path="/product/:id" component={Home} />
    <Route path="/products" component={Home} />
    <Route path="/categories" component={Home} />
    <Route path="/cart" component={Home} />
    <Route path="/favorites" component={Home} />
    <Route path="/orders" component={Home} />
    <Route path="/account" component={Home} />
    <Route path="/assistant" component={Home} />
    <Route path="/" component={Home} />
    <Route component={NotFound} />
  </Switch>;
}

export default function App() {
  return <ErrorBoundary>
    <ThemeProvider defaultTheme="light">
      <TooltipProvider>
        <StoreProvider>
          <CustomerProvider>
            <Toaster position="top-center" richColors />
            <Router />
          </CustomerProvider>
        </StoreProvider>
      </TooltipProvider>
    </ThemeProvider>
  </ErrorBoundary>;
}
