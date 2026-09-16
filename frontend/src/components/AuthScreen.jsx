import {
  useState,
} from "react";

import {
  API_URL,
} from "../config";


function getErrorMessage(data) {
  if (!data) {
    return "Something went wrong.";
  }

  if (
    typeof data.detail === "string"
  ) {
    return data.detail;
  }

  if (
    Array.isArray(data.detail)
  ) {
    return data.detail
      .map((item) => {
        return (
          item.msg ||
          "Invalid input."
        );
      })
      .join(" ");
  }

  return "Something went wrong.";
}


function AuthScreen({
  backendOnline,
  onAuthenticated,
}) {
  const [mode, setMode] =
    useState("login");

  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [
    confirmPassword,
    setConfirmPassword,
  ] = useState("");

  const [error, setError] =
    useState("");

  const [submitting, setSubmitting] =
    useState(false);


  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    setPassword("");
    setConfirmPassword("");
  }


  async function login() {
    const response = await fetch(
      `${API_URL}/auth/login`,
      {
        method: "POST",
        credentials: "include",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          username,
          password,
        }),
      }
    );

    const data =
      await response.json();

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data)
      );
    }

    return data;
  }


  async function register() {
    if (
      password !==
      confirmPassword
    ) {
      throw new Error(
        "Passwords do not match."
      );
    }

    const response = await fetch(
      `${API_URL}/auth/register`,
      {
        method: "POST",
        credentials: "include",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          username,
          password,
        }),
      }
    );

    const data =
      await response.json();

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data)
      );
    }

    return data;
  }


  async function handleSubmit(
    event
  ) {
    event.preventDefault();

    if (!backendOnline) {
      setError(
        "Daedalus backend is offline."
      );

      return;
    }

    setSubmitting(true);
    setError("");

    try {
      if (mode === "register") {
        await register();
      }

      const user =
        await login();

      onAuthenticated(user);

    } catch (submitError) {
      setError(
        submitError.message
      );

    } finally {
      setSubmitting(false);
    }
  }


  return (
    <div className="auth-page">

      <div className="auth-brand">

        <div className="auth-logo">
          D
        </div>

        <h1>DAEDALUS</h1>

        <p>
          Adaptive Windows Internals
          & Rust Tutor
        </p>

      </div>

      <div className="auth-card">

        <div className="auth-tabs">

          <button
            type="button"
            className={
              mode === "login"
                ? "auth-tab active"
                : "auth-tab"
            }
            onClick={() =>
              switchMode("login")
            }
          >
            Sign in
          </button>

          <button
            type="button"
            className={
              mode === "register"
                ? "auth-tab active"
                : "auth-tab"
            }
            onClick={() =>
              switchMode(
                "register"
              )
            }
          >
            Create account
          </button>

        </div>

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >

          <div className="auth-field">

            <label htmlFor="username">
              Username
            </label>

            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) =>
                setUsername(
                  event.target.value
                )
              }
              autoComplete="username"
              disabled={submitting}
              required
            />

          </div>

          <div className="auth-field">

            <label htmlFor="password">
              Password
            </label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
              autoComplete={
                mode === "login"
                  ? "current-password"
                  : "new-password"
              }
              disabled={submitting}
              required
            />

          </div>

          {mode === "register" && (
            <div className="auth-field">

              <label
                htmlFor="confirm-password"
              >
                Confirm password
              </label>

              <input
                id="confirm-password"
                type="password"
                value={
                  confirmPassword
                }
                onChange={(event) =>
                  setConfirmPassword(
                    event.target.value
                  )
                }
                autoComplete="new-password"
                disabled={submitting}
                required
              />

            </div>
          )}

          {mode === "register" && (
            <div className="password-hint">
              Minimum 10 characters
              with at least one letter
              and one number.
            </div>
          )}

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button
            className="auth-submit"
            type="submit"
            disabled={
              submitting ||
              !username.trim() ||
              !password ||
              !backendOnline
            }
          >
            {submitting
              ? "Please wait..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>

        </form>

        <div className="auth-service-status">

          <span
            className={
              `status-dot ${
                backendOnline
                  ? "online"
                  : "offline"
              }`
            }
          />

          {backendOnline
            ? "Daedalus backend online"
            : "Daedalus backend offline"}

        </div>

      </div>

    </div>
  );
}


export default AuthScreen;