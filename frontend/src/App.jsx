import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import PatientDashboard from "./pages/PatientDashboard.jsx";
import PatientProfileForm from "./pages/PatientProfileForm.jsx";
import Predict from "./pages/Predict.jsx";
import History from "./pages/History.jsx";
import DoctorDashboard from "./pages/DoctorDashboard.jsx";
import DoctorProfileForm from "./pages/DoctorProfileForm.jsx";
import ChangePassword from "./pages/ChangePassword.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import "./App.css";

function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <nav className="navbar">
      <Link to="/" className="brand">P.H.D. Prediction</Link>
      <div className="nav-links">
        {!user && <Link to="/login">Login</Link>}
        {!user && <Link to="/register">Register</Link>}
        {user && user.role === "patient" && <Link to="/patient">Dashboard</Link>}
        {user && user.role === "doctor" && <Link to="/doctor">Dashboard</Link>}
        {user && user.role === "admin" && <Link to="/admin">Dashboard</Link>}
        {user && <Link to="/change-password">Change Password</Link>}
        {user && (
          <button type="button" className="link-button" onClick={handleLogout}>
            Logout ({user.username})
          </button>
        )}
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/patient"
              element={
                <ProtectedRoute role="patient">
                  <PatientDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/patient"
              element={
                <ProtectedRoute role="patient">
                  <PatientProfileForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/predict/:disease"
              element={
                <ProtectedRoute roles={["patient", "doctor"]}>
                  <Predict />
                </ProtectedRoute>
              }
            />
            <Route
              path="/history"
              element={
                <ProtectedRoute roles={["patient", "doctor"]}>
                  <History />
                </ProtectedRoute>
              }
            />
            <Route
              path="/doctor"
              element={
                <ProtectedRoute role="doctor">
                  <DoctorDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/doctor"
              element={
                <ProtectedRoute role="doctor">
                  <DoctorProfileForm />
                </ProtectedRoute>
              }
            />
            <Route
              path="/change-password"
              element={
                <ProtectedRoute>
                  <ChangePassword />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute role="admin">
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </AuthProvider>
    </BrowserRouter>
  );
}
