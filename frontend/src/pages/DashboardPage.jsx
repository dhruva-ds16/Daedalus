import {
  useEffect,
  useState,
} from "react";

import {
  API_URL,
} from "../config";


const PROGRAM_INFO = {
  rust: {
    icon: "R",
    title: "Rust Programming",
    description:
      "Learn Rust from fundamentals through advanced systems programming.",
  },

  windows: {
    icon: "W",
    title: "Windows Internals",
    description:
      "Understand Windows architecture, processes, memory, objects, security, and kernel internals.",
  },

  integrated: {
    icon: "R+W",
    title: "Windows + Rust",
    description:
      "Learn Windows Internals and Rust together through practical systems programming.",
  },
};


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


function DashboardPage({
  user,
  onOpenTutor,
  onOpenProgram,
}) {
  const [profile, setProfile] =
    useState(null);

  const [programs, setPrograms] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [
    showCreateProgram,
    setShowCreateProgram,
  ] = useState(false);

  const [
    selectedProgramType,
    setSelectedProgramType,
  ] = useState(null);

  const [goal, setGoal] =
    useState("");

  const [
    startingStrategy,
    setStartingStrategy,
  ] = useState("assessment");

  const [
    selectedLevel,
    setSelectedLevel,
  ] = useState("beginner");

  const [
    creating,
    setCreating,
  ] = useState(false);


  useEffect(() => {
    loadDashboard();
  }, []);


  async function request(
    path,
    options = {},
  ) {
    const response = await fetch(
      `${API_URL}${path}`,
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


  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const [
        profileData,
        programsData,
      ] = await Promise.all([
        request("/profile"),
        request("/programs"),
      ]);

      setProfile(profileData);
      setPrograms(programsData);

    } catch (loadError) {
      setError(
        loadError.message
      );

    } finally {
      setLoading(false);
    }
  }


  function hasProgram(
    programType
  ) {
    return programs.some(
      (program) =>
        program.program_type ===
        programType
    );
  }


  function beginProgramCreation(
    programType
  ) {
    setSelectedProgramType(
      programType
    );

    setGoal("");
    setStartingStrategy(
      "assessment"
    );
    setSelectedLevel(
      "beginner"
    );

    setError("");
    setShowCreateProgram(true);
  }


  function closeCreateProgram() {
    if (creating) {
      return;
    }

    setShowCreateProgram(false);
    setSelectedProgramType(null);
  }


  async function createProgram(
    event
  ) {
    event.preventDefault();

    if (!selectedProgramType) {
      return;
    }

    setCreating(true);
    setError("");

    try {
      const payload = {
        program_type:
          selectedProgramType,

        goal:
          goal.trim()
            ? goal.trim()
            : null,

        starting_strategy:
          startingStrategy,

        selected_level:
          startingStrategy ===
          "selected_level"
            ? selectedLevel
            : null,
      };


      const program =
        await request(
          "/programs",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              payload
            ),
          }
        );


      setPrograms(
        (current) => [
          ...current,
          program,
        ]
      );

      setShowCreateProgram(false);
      setSelectedProgramType(null);

    } catch (createError) {
      setError(
        createError.message
      );

    } finally {
      setCreating(false);
    }
  }


  function displayName() {
    if (
      profile?.display_name
    ) {
      return profile.display_name;
    }

    return user.username;
  }


  function statusLabel(
    status
  ) {
    switch (status) {
      case "setup":
        return "Setup required";

      case "active":
        return "In progress";

      case "paused":
        return "Paused";

      case "completed":
        return "Completed";

      default:
        return status;
    }
  }


  function renderProgramCard(
    programType
  ) {
    const info =
      PROGRAM_INFO[
        programType
      ];

    const program =
      programs.find(
        (item) =>
          item.program_type ===
          programType
      );


    if (program) {
      return (
        <div
          className="program-card"
          key={programType}
        >

          <div className="program-card-top">

            <div className="program-icon">
              {info.icon}
            </div>

            <span
              className={
                `program-status ${
                  program.status
                }`
              }
            >
              {statusLabel(
                program.status
              )}
            </span>

          </div>


          <h3>
            {program.title}
          </h3>

          <p>
            {program.goal ||
              info.description}
          </p>


          <div className="program-meta">

            <span>
              Starting point
            </span>

            <strong>
              {program.starting_strategy ===
              "beginning"
                ? "From beginning"
                : program.starting_strategy ===
                  "assessment"
                  ? "Assessment"
                  : program.selected_level}
            </strong>

          </div>


          <button
            className="program-open-button"
            onClick={() =>
              onOpenProgram(
                program
              )
            }
          >
            {program.status ===
            "setup"
              ? "Set up program"
              : "Continue"}
          </button>

        </div>
      );
    }


    return (
      <div
        className="program-card available"
        key={programType}
      >

        <div className="program-card-top">

          <div className="program-icon">
            {info.icon}
          </div>

          <span className="program-status available">
            Available
          </span>

        </div>


        <h3>
          {info.title}
        </h3>

        <p>
          {info.description}
        </p>


        <button
          className="program-create-button"
          onClick={() =>
            beginProgramCreation(
              programType
            )
          }
        >
          Start Program
        </button>

      </div>
    );
  }


  if (loading) {
    return (
      <main className="dashboard-page">

        <div className="dashboard-loading">
          Loading your learning state...
        </div>

      </main>
    );
  }


  return (
    <main className="dashboard-page">

      <section className="dashboard-hero">

        <div>

          <span className="dashboard-eyebrow">
            Your Learning
          </span>

          <h2>
            Welcome back,{" "}
            {displayName()}.
          </h2>

          <p>
            Choose a learning program
            or ask Daedalus a standalone
            question.
          </p>

        </div>


        <button
          className="dashboard-ask-button"
          onClick={onOpenTutor}
        >
          Ask Daedalus
        </button>

      </section>


      {error && (
        <div className="admin-alert error">
          {error}
        </div>
      )}


      <section className="dashboard-section">

        <div className="section-heading">

          <div>

            <h3>
              Learning Programs
            </h3>

            <p>
              Each program keeps its own
              curriculum and progress.
            </p>

          </div>

          <div className="program-count">
            {programs.length}/3 active
          </div>

        </div>


        <div className="program-grid">

          {renderProgramCard(
            "rust"
          )}

          {renderProgramCard(
            "windows"
          )}

          {renderProgramCard(
            "integrated"
          )}

        </div>

      </section>


      <section className="dashboard-section">

        <div className="section-heading">

          <div>

            <h3>
              Learner Profile
            </h3>

            <p>
              Daedalus uses this
              information when planning
              your learning.
            </p>

          </div>

        </div>


        <div className="profile-summary">

          <div>
            <span>
              Programming experience
            </span>

            <strong>
              {
                profile
                  ?.programming_experience
              }
            </strong>
          </div>


          <div>
            <span>
              Explanation depth
            </span>

            <strong>
              {
                profile
                  ?.preferred_depth
              }
            </strong>
          </div>


          <div>
            <span>
              Study intensity
            </span>

            <strong>
              {
                profile
                  ?.study_intensity
              }
            </strong>
          </div>

        </div>

      </section>


      {showCreateProgram &&
        selectedProgramType && (

        <div className="modal-backdrop">

          <div className="program-modal">

            <div className="modal-heading">

              <div>

                <span className="modal-eyebrow">
                  New Learning Program
                </span>

                <h3>
                  {
                    PROGRAM_INFO[
                      selectedProgramType
                    ].title
                  }
                </h3>

              </div>

              <button
                className="modal-close"
                onClick={
                  closeCreateProgram
                }
              >
                ×
              </button>

            </div>


            <form
              className="program-form"
              onSubmit={
                createProgram
              }
            >

              <label>
                What do you want
                to achieve?

                <textarea
                  value={goal}
                  onChange={(event) =>
                    setGoal(
                      event.target.value
                    )
                  }
                  placeholder={
                    selectedProgramType ===
                    "rust"
                      ? "Example: Become comfortable building systems software in Rust."
                      : selectedProgramType ===
                        "windows"
                        ? "Example: Develop a deep understanding of Windows Internals."
                        : "Example: Learn Windows Internals while applying concepts through Rust."
                  }
                  rows={4}
                />
              </label>


              <fieldset>

                <legend>
                  Where should Daedalus
                  start?
                </legend>


                <label className="strategy-option">

                  <input
                    type="radio"
                    name="strategy"
                    value="beginning"
                    checked={
                      startingStrategy ===
                      "beginning"
                    }
                    onChange={(event) =>
                      setStartingStrategy(
                        event.target.value
                      )
                    }
                  />

                  <div>
                    <strong>
                      Start from beginning
                    </strong>

                    <span>
                      Follow the complete
                      learning path.
                    </span>
                  </div>

                </label>


                <label className="strategy-option">

                  <input
                    type="radio"
                    name="strategy"
                    value="assessment"
                    checked={
                      startingStrategy ===
                      "assessment"
                    }
                    onChange={(event) =>
                      setStartingStrategy(
                        event.target.value
                      )
                    }
                  />

                  <div>
                    <strong>
                      Assess my knowledge
                    </strong>

                    <span>
                      Daedalus will determine
                      an appropriate starting
                      point.
                    </span>
                  </div>

                </label>


                <label className="strategy-option">

                  <input
                    type="radio"
                    name="strategy"
                    value="selected_level"
                    checked={
                      startingStrategy ===
                      "selected_level"
                    }
                    onChange={(event) =>
                      setStartingStrategy(
                        event.target.value
                      )
                    }
                  />

                  <div>
                    <strong>
                      Choose a level
                    </strong>

                    <span>
                      Manually select your
                      starting level.
                    </span>
                  </div>

                </label>

              </fieldset>


              {startingStrategy ===
                "selected_level" && (

                <label>
                  Starting level

                  <select
                    value={
                      selectedLevel
                    }
                    onChange={(event) =>
                      setSelectedLevel(
                        event.target.value
                      )
                    }
                  >
                    <option value="beginner">
                      Beginner
                    </option>

                    <option value="intermediate">
                      Intermediate
                    </option>

                    <option value="advanced">
                      Advanced
                    </option>
                  </select>

                </label>

              )}


              <div className="modal-actions">

                <button
                  type="button"
                  onClick={
                    closeCreateProgram
                  }
                  disabled={creating}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="admin-primary-button"
                  disabled={creating}
                >
                  {creating
                    ? "Creating..."
                    : "Create Program"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </main>
  );
}


export default DashboardPage;