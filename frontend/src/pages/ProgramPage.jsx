function ProgramPage({
  program,
  onBack,
  onStartAssessment,
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


  function strategyLabel() {
    switch (
      program.starting_strategy
    ) {
      case "assessment":
        return "Knowledge assessment";

      case "beginning":
        return "Start from beginning";

      case "selected_level":
        return (
          program.selected_level ||
          "Selected level"
        );

      default:
        return program.starting_strategy;
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
          {program.starting_strategy ===
          "assessment"
            ? "Start with a knowledge assessment"
            : "Ready for curriculum generation"}
        </h3>


        {program.starting_strategy ===
        "assessment" ? (

          <p>
            Daedalus will adaptively assess
            your current understanding before
            creating your personalized
            curriculum. Each question is
            selected using evidence from your
            previous answers.
          </p>

        ) : (

          <p>
            This program does not require an
            assessment. Your curriculum will
            be generated from your learner
            profile, goals, and selected
            starting strategy.
          </p>

        )}


        <div className="program-details">

          <div>
            <span>
              Starting strategy
            </span>

            <strong>
              {strategyLabel()}
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


        {program.starting_strategy ===
          "assessment" && (

          <div className="program-primary-action">

            <button
              className="assessment-primary"
              onClick={() =>
                onStartAssessment(
                  program
                )
              }
            >
              Start / Resume Assessment →
            </button>

          </div>

        )}

      </div>

    </main>
  );
}


export default ProgramPage;