function ProgramPage({
  program,
  onBack,
}) {
  if (!program) {
    return null;
  }


  function programLabel() {
    switch (
      program.program_type
    ) {
      case "rust":
        return "Rust Programming";

      case "windows":
        return "Windows Internals";

      case "integrated":
        return "Windows + Rust";

      default:
        return program.title;
    }
  }


  return (
    <main className="program-page">

      <button
        className="back-button"
        onClick={onBack}
      >
        ← Dashboard
      </button>


      <div className="program-page-header">

        <span className="dashboard-eyebrow">
          Learning Program
        </span>

        <h2>
          {programLabel()}
        </h2>

        <p>
          {program.goal ||
            "No learning goal has been set."}
        </p>

      </div>


      <div className="program-setup-card">

        <div className="program-setup-status">
          Setup
        </div>

        <h3>
          Program created successfully
        </h3>

        <p>
          Your learning program is now
          persistent. The next Daedalus
          milestone will use your starting
          strategy to determine how the
          curriculum should be created.
        </p>


        <div className="program-details">

          <div>
            <span>
              Starting strategy
            </span>

            <strong>
              {
                program
                  .starting_strategy
              }
            </strong>
          </div>


          <div>
            <span>
              Curriculum
            </span>

            <strong>
              Not generated
            </strong>
          </div>


          <div>
            <span>
              Curriculum version
            </span>

            <strong>
              {
                program
                  .curriculum_version
              }
            </strong>
          </div>

        </div>

      </div>

    </main>
  );
}


export default ProgramPage;