import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom';

import {
  OfficerLayout,
  PublicLayout,
} from './components/shared';

import LoginPage from './pages/LoginPage';
import UploadPage from './pages/UploadPage';
import ReviewPage from './pages/ReviewPage';
import QueuePage from './pages/QueuePage';
import AdminPage from './pages/AdminPage';
import RecordDetailPage from './pages/RecordDetailPage';
import DiscrepancyPage from './pages/DiscrepancyPage';
import MultilingualPage from './pages/MultilingualPage';
import MapPage from './pages/MapPage';
import LookupPage from './pages/LookupPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* ═══════════════════════════════════════
            PUBLIC / CITIZEN ROUTES
        ═══════════════════════════════════════ */}

        <Route element={<PublicLayout />}>

          <Route
            path="/login"
            element={<LoginPage />}
          />

          <Route
            path="/lookup"
            element={<LookupPage />}
          />

        </Route>

        {/* ═══════════════════════════════════════
            OFFICER / ADMIN WORKSPACE
        ═══════════════════════════════════════ */}

        <Route element={<OfficerLayout />}>

          <Route
            path="/upload"
            element={<UploadPage />}
          />

          <Route
            path="/review"
            element={<ReviewPage />}
          />

          <Route
            path="/queue"
            element={<QueuePage />}
          />

          <Route
            path="/admin"
            element={<AdminPage />}
          />

          <Route
            path="/records/:id"
            element={<RecordDetailPage />}
          />

          <Route
            path="/discrepancy/:id"
            element={<DiscrepancyPage />}
          />

          <Route
            path="/records/:id/multilingual"
            element={<MultilingualPage />}
          />

          <Route
            path="/map"
            element={<MapPage />}
          />

        </Route>

        {/* ═══════════════════════════════════════
            DEFAULT / UNKNOWN ROUTES
        ═══════════════════════════════════════ */}

        <Route
          path="/"
          element={
            <Navigate
              to="/login"
              replace
            />
          }
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/login"
              replace
            />
          }
        />

      </Routes>
    </BrowserRouter>
  );
}