import {
  useEffect,
  useState,
} from "react";

import {
  API_URL,
} from "../config";


function getErrorMessage(data) {
  if (
    typeof data?.detail === "string"
  ) {
    return data.detail;
  }

  if (
    Array.isArray(data?.detail)
  ) {
    return data.detail
      .map((item) =>
        item.msg ||
        "Invalid input."
      )
      .join(" ");
  }

  return "Request failed.";
}


function AdminPage({
  currentUser,
}) {
  const [users, setUsers] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [message, setMessage] =
    useState("");

  const [
    showCreateUser,
    setShowCreateUser,
  ] = useState(false);

  const [
    createUsername,
    setCreateUsername,
  ] = useState("");

  const [
    createPassword,
    setCreatePassword,
  ] = useState("");

  const [
    createAdmin,
    setCreateAdmin,
  ] = useState(false);

  const [
    resetUser,
    setResetUser,
  ] = useState(null);

  const [
    resetPassword,
    setResetPassword,
  ] = useState("");


  useEffect(() => {
    loadUsers();
  }, []);


  async function request(
    url,
    options = {},
  ) {
    const response = await fetch(
      `${API_URL}${url}`,
      {
        credentials: "include",
        ...options,
      }
    );

    let data = null;

    try {
      data =
        await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data)
      );
    }

    return data;
  }


  async function loadUsers() {
    setLoading(true);
    setError("");

    try {
      const data =
        await request(
          "/admin/users"
        );

      setUsers(data);

    } catch (loadError) {
      setError(
        loadError.message
      );

    } finally {
      setLoading(false);
    }
  }


  async function createUser(
    event
  ) {
    event.preventDefault();

    setError("");
    setMessage("");

    try {
      const user =
        await request(
          "/admin/users",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              username:
                createUsername,

              password:
                createPassword,

              is_admin:
                createAdmin,
            }),
          }
        );

      setMessage(
        `Created ${user.username}.`
      );

      setCreateUsername("");
      setCreatePassword("");
      setCreateAdmin(false);
      setShowCreateUser(false);

      await loadUsers();

    } catch (createError) {
      setError(
        createError.message
      );
    }
  }


  async function submitPasswordReset(
    event
  ) {
    event.preventDefault();

    if (!resetUser) {
      return;
    }

    setError("");
    setMessage("");

    try {
      const data =
        await request(
          `/admin/users/${resetUser.id}/reset-password`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              password:
                resetPassword,
            }),
          }
        );

      setMessage(
        data.message
      );

      setResetUser(null);
      setResetPassword("");

    } catch (resetError) {
      setError(
        resetError.message
      );
    }
  }


  async function toggleUser(
    user
  ) {
    setError("");
    setMessage("");

    const action =
      user.is_active
        ? "disable"
        : "enable";

    if (
      !window.confirm(
        `${action} ${user.username}?`
      )
    ) {
      return;
    }

    try {
      const updated =
        await request(
          `/admin/users/${user.id}/active`,
          {
            method: "PATCH",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              is_active:
                !user.is_active,
            }),
          }
        );

      setMessage(
        `${updated.username} ${
          updated.is_active
            ? "enabled"
            : "disabled"
        }.`
      );

      await loadUsers();

    } catch (toggleError) {
      setError(
        toggleError.message
      );
    }
  }


  async function deleteUser(
    user
  ) {
    setError("");
    setMessage("");

    const confirmed =
      window.confirm(
        `Delete ${user.username}? ` +
        "This action cannot be undone."
      );

    if (!confirmed) {
      return;
    }

    try {
      const data =
        await request(
          `/admin/users/${user.id}`,
          {
            method: "DELETE",
          }
        );

      setMessage(
        data.message
      );

      await loadUsers();

    } catch (deleteError) {
      setError(
        deleteError.message
      );
    }
  }


  return (
    <main className="admin-page">

      <div className="admin-heading">

        <div>
          <h2>
            User Administration
          </h2>

          <p>
            Manage Daedalus accounts
            and access.
          </p>
        </div>

        <button
          className="admin-primary-button"
          onClick={() =>
            setShowCreateUser(true)
          }
        >
          + Create User
        </button>

      </div>


      {error && (
        <div className="admin-alert error">
          {error}
        </div>
      )}


      {message && (
        <div className="admin-alert success">
          {message}
        </div>
      )}


      {loading ? (

        <div className="admin-loading">
          Loading users...
        </div>

      ) : (

        <div className="admin-table-wrapper">

          <table className="admin-table">

            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>

              {users.map((user) => {

                const isSelf =
                  user.id ===
                  currentUser.id;

                return (
                  <tr key={user.id}>

                    <td>
                      <div className="admin-username">
                        {user.username}

                        {isSelf && (
                          <span className="self-label">
                            You
                          </span>
                        )}
                      </div>
                    </td>

                    <td>
                      <span
                        className={
                          user.is_admin
                            ? "role-badge admin"
                            : "role-badge"
                        }
                      >
                        {user.is_admin
                          ? "Admin"
                          : "User"}
                      </span>
                    </td>

                    <td>
                      <span
                        className={
                          user.is_active
                            ? "account-status active"
                            : "account-status inactive"
                        }
                      >
                        {user.is_active
                          ? "Active"
                          : "Disabled"}
                      </span>
                    </td>

                    <td>
                      {new Date(
                        user.created_at
                      ).toLocaleDateString()}
                    </td>

                    <td>
                      <div className="admin-actions">

                        <button
                          onClick={() => {
                            setResetUser(
                              user
                            );

                            setResetPassword(
                              ""
                            );
                          }}
                        >
                          Reset Password
                        </button>

                        <button
                          onClick={() =>
                            toggleUser(user)
                          }
                          disabled={isSelf}
                        >
                          {user.is_active
                            ? "Disable"
                            : "Enable"}
                        </button>

                        <button
                          className="danger"
                          onClick={() =>
                            deleteUser(user)
                          }
                          disabled={isSelf}
                        >
                          Delete
                        </button>

                      </div>
                    </td>

                  </tr>
                );
              })}

            </tbody>

          </table>

        </div>
      )}


      {showCreateUser && (

        <div className="modal-backdrop">

          <div className="admin-modal">

            <div className="modal-heading">

              <h3>
                Create User
              </h3>

              <button
                className="modal-close"
                onClick={() =>
                  setShowCreateUser(
                    false
                  )
                }
              >
                ×
              </button>

            </div>

            <form
              className="admin-form"
              onSubmit={createUser}
            >

              <label>
                Username

                <input
                  value={
                    createUsername
                  }
                  onChange={(event) =>
                    setCreateUsername(
                      event.target.value
                    )
                  }
                  required
                />
              </label>

              <label>
                Temporary Password

                <input
                  type="password"
                  value={
                    createPassword
                  }
                  onChange={(event) =>
                    setCreatePassword(
                      event.target.value
                    )
                  }
                  required
                />
              </label>

              <label className="checkbox-field">

                <input
                  type="checkbox"
                  checked={
                    createAdmin
                  }
                  onChange={(event) =>
                    setCreateAdmin(
                      event.target.checked
                    )
                  }
                />

                Administrator
              </label>

              <div className="modal-actions">

                <button
                  type="button"
                  onClick={() =>
                    setShowCreateUser(
                      false
                    )
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="admin-primary-button"
                >
                  Create User
                </button>

              </div>

            </form>

          </div>

        </div>
      )}


      {resetUser && (

        <div className="modal-backdrop">

          <div className="admin-modal">

            <div className="modal-heading">

              <h3>
                Reset Password
              </h3>

              <button
                className="modal-close"
                onClick={() =>
                  setResetUser(null)
                }
              >
                ×
              </button>

            </div>

            <p className="modal-description">
              Set a new password for{" "}
              <strong>
                {resetUser.username}
              </strong>.
              Existing sessions will be
              revoked.
            </p>

            <form
              className="admin-form"
              onSubmit={
                submitPasswordReset
              }
            >

              <label>
                New Password

                <input
                  type="password"
                  value={
                    resetPassword
                  }
                  onChange={(event) =>
                    setResetPassword(
                      event.target.value
                    )
                  }
                  required
                />
              </label>

              <div className="modal-actions">

                <button
                  type="button"
                  onClick={() =>
                    setResetUser(null)
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="admin-primary-button"
                >
                  Reset Password
                </button>

              </div>

            </form>

          </div>

        </div>
      )}

    </main>
  );
}


export default AdminPage;