import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuditoriaPage } from "./pages/AuditoriaPage";
import { AccesosPage } from "./pages/AccesosPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ContenedoresPage } from "./pages/ContenedoresPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { LoginPage } from "./pages/LoginPage";
import { MovimientosPage } from "./pages/MovimientosPage";
import { UbicacionesPage } from "./pages/UbicacionesPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="contenedores" element={<ContenedoresPage />} />
          <Route path="movimientos" element={<MovimientosPage />} />
          <Route path="ubicaciones" element={<UbicacionesPage />} />
          <Route element={<ProtectedRoute roles={["supervisor"]} />}>
            <Route path="auditoria" element={<AuditoriaPage />} />
            <Route path="accesos" element={<AccesosPage />} />
          </Route>
          <Route path="sin-permiso" element={<ForbiddenPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
