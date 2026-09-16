import {
  useEffect,
  useState,
} from "react";

import "./App.css";

import {
  API_URL,
} from "./config";

import AuthScreen from "./components/AuthScreen";
import TutorApp from "./components/TutorApp";

import AdminPage from "./pages/AdminPage";
import DashboardPage from "./pages/DashboardPage";
import ProgramPage from "./pages/ProgramPage";


function App() {
  const [user, setUser] =
    useState(null);

  const [
    checkingSession,
    setCheckingSession,
  ] = useState(true);

  const [
    backendOnline,
    setBackendOnline,
  ] = useState(false);

  const [page, setPage] =
    useState("dashboard");

  const [
    selectedProgram,
    setSelectedProgram,
  ] = useState(null);


  useEffect(() => {
    initializeApplication();
  }, []);


  async function initializeApplication() {
    setCheckingSession(true);

    let online = false;

    try {
      const response =
        await fetch(
          `${API_URL}/health`
        );

      if (response.ok) {
        const data =
          await response.json();

        online =
          data.backend === "online";
      }

    } catch {
      online = false;
    }


    setBackendOnline(
      online
    );


    if (!online) {
      setUser(null);
      setCheckingSession(false);

      return;
    }


    try {
      const response =
        await fetch(
          `${API_URL}/auth/me`,
          {
            credentials: "include",
          }
        );

      if (response.ok) {
        const currentUser =
          await response.json();

        setUser(currentUser);

      } else {
        setUser(null);
      }

    } catch {
      setUser(null);

    } finally {
      setCheckingSession(false);
    }
  }


  function handleAuthenticated(
    authenticatedUser
  ) {
    setUser(
      authenticatedUser
    );

    setPage(
      "dashboard"
    );
  }


  function openProgram(
    program
  ) {
    setSelectedProgram(
      program
    );

    setPage(
      "program"
    );
  }


  function returnToDashboard() {
    setSelectedProgram(null);
    setPage("dashboard");
  }


  async function logout() {
    try {
      await fetch(
        `${API_URL}/auth/logout`,
        {
          method: "POST",
          credentials: "include",
        }
      );

    } finally {
      setUser(null);
      setSelectedProgram(null);
      setPage("dashboard");
    }
  }


  if (checkingSession) {
    return (
      <div className="startup-screen">

        <div className="startup-content">

          <div className="auth-logo">
            D
          </div>

          <h1>
            DAEDALUS
          </h1>

          <p>
            Restoring your session...
          </p>

        </div>

      </div>
    );
  }


  if (!user) {
    return (
      <AuthScreen
        backendOnline={
          backendOnline
        }
        onAuthenticated={
          handleAuthenticated
        }
      />
    );
  }


  return (
    <div className="app">

      <header className="header">

        <div
          className="brand brand-clickable"
          onClick={
            returnToDashboard
          }
        >

          <h1>
            DAEDALUS
          </h1>

          <p>
            Adaptive Windows Internals
            & Rust Tutor
          </p>

        </div>


        <nav className="main-nav">

          <button
            className={
              page === "dashboard"
                ? "nav-button active"
                : "nav-button"
            }
            onClick={
              returnToDashboard
            }
          >
            Dashboard
          </button>


          <button
            className={
              page === "tutor"
                ? "nav-button active"
                : "nav-button"
            }
            onClick={() =>
              setPage("tutor")
            }
          >
            Ask Daedalus
          </button>


          {user.is_admin && (

            <button
              className={
                page === "admin"
                  ? "nav-button active"
                  : "nav-button"
              }
              onClick={() =>
                setPage("admin")
              }
            >
              Admin
            </button>

          )}

        </nav>


        <div className="header-user">

          <div>

            <div className="header-username">
              {user.username}
            </div>

            <div className="header-role">
              {user.is_admin
                ? "Administrator"
                : "Learner"}
            </div>

          </div>


          <button
            className="logout-button"
            onClick={logout}
          >
            Logout
          </button>

        </div>

      </header>


      {page === "dashboard" && (

        <DashboardPage
          user={user}
          onOpenTutor={() =>
            setPage("tutor")
          }
          onOpenProgram={
            openProgram
          }
        />

      )}


      {page === "tutor" && (
        <TutorApp />
      )}


      {page === "program" && (

        <ProgramPage
          program={
            selectedProgram
          }
          onBack={
            returnToDashboard
          }
        />

      )}


      {page === "admin" &&
        user.is_admin && (

        <AdminPage
          currentUser={user}
        />

      )}

    </div>
  );
}


export default App;