import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useEffect } from "react";
import AppShell from "./components/layout/AppShell";
import { useAuth } from "./stores/auth";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import IntakePage from "./pages/IntakePage";
import ManifestDetailPage from "./pages/ManifestDetailPage";
import AccessionPage from "./pages/AccessionPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import ShipmentDetailPage from "./pages/ShipmentDetailPage";
import SamplesPage from "./pages/SamplesPage";
import Sample360Page from "./pages/Sample360Page";
import InventoryPage from "./pages/InventoryPage";
import LineagePage from "./pages/LineagePage";
import ExceptionsPage from "./pages/ExceptionsPage";
import ReportsPage from "./pages/ReportsPage";
import TraceabilityPage from "./pages/TraceabilityPage";
import ApiExplorerPage from "./pages/ApiExplorerPage";
import AdminPage from "./pages/AdminPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

function Guard({ children }) {
  const { user, loading, hydrate } = useAuth();
  useEffect(() => {
    hydrate();
  }, [hydrate]);
  if (loading) return <div className="flex h-screen items-center justify-center text-sm text-slate-500">Loading session…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <Guard>
                <AppShell />
              </Guard>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="intake" element={<IntakePage />} />
            <Route path="intake/:id" element={<ManifestDetailPage />} />
            <Route path="accession" element={<AccessionPage />} />
            <Route path="shipments" element={<ShipmentsPage />} />
            <Route path="shipments/:id" element={<ShipmentDetailPage />} />
            <Route path="samples" element={<SamplesPage />} />
            <Route path="samples/:id" element={<Sample360Page />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="lineage" element={<LineagePage />} />
            <Route path="lineage/:id" element={<LineagePage />} />
            <Route path="exceptions" element={<ExceptionsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="traceability" element={<TraceabilityPage />} />
            <Route path="api-explorer" element={<ApiExplorerPage />} />
            <Route path="admin" element={<AdminPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
