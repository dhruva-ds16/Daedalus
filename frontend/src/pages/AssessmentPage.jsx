import {
  useEffect,
  useState,
} from "react";

import {
  API_URL,
} from "../config";

import MarkdownMessage from "../components/MarkdownMessage";


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


function AssessmentPage({
  program,
  selectedModel,
  onBack,
  onComplete,
}) {
  const [
    assessment,
    setAssessment,
  ] = useState(null);

  const [
    question,
    setQuestion,
  ] = useState(null);

  const [
    answer,
    setAnswer,
  ] = useState("");

  const [
    evaluation,
    setEvaluation,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    planning,
    setPlanning,
  ] = useState(false);

  const [
    evaluating,
    setEvaluating,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  useEffect(() => {
    initializeAssessment();
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


  async function initializeAssessment() {
    setLoading(true);
    setError("");

    try {
      let current =
        await request(
          `/assessments/program/${program.id}/current`
        );

      if (!current) {
        current =
          await request(
            "/assessments",
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                program_id:
                  program.id,

                max_questions:
                  12,
              }),
            }
          );
      }

      setAssessment(
        current
      );

      const questions =
        await request(
          `/assessments/${current.id}/questions`
        );

      if (
        questions.length > 0
      ) {
        const latest =
          questions[
            questions.length - 1
          ];

        if (!latest.answered) {
          setQuestion(
            latest
          );

          setLoading(false);
          return;
        }
      }

      if (
        current.questions_answered
        >= current.max_questions
      ) {
        setLoading(false);
        return;
      }

      await generateQuestion(
        current.id
      );

    } catch (loadError) {
      setError(
        loadError.message
      );

    } finally {
      setLoading(false);
    }
  }


  async function generateQuestion(
    assessmentId = assessment?.id
  ) {
    if (
      !assessmentId ||
      !selectedModel
    ) {
      return;
    }

    setPlanning(true);
    setError("");
    setEvaluation(null);
    setAnswer("");

    try {
      const nextQuestion =
        await request(
          `/assessments/${assessmentId}/questions`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              model:
                selectedModel,
            }),
          }
        );

      setQuestion(
        nextQuestion
      );

    } catch (planningError) {
      setError(
        planningError.message
      );

    } finally {
      setPlanning(false);
    }
  }


  async function submitAnswer(
    event
  ) {
    event.preventDefault();

    if (
      !answer.trim() ||
      !question ||
      !assessment ||
      evaluating
    ) {
      return;
    }

    setEvaluating(true);
    setError("");

    try {
      const result =
        await request(
          `/assessments/${assessment.id}/questions/${question.id}/answer`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              model:
                selectedModel,

              answer:
                answer.trim(),
            }),
          }
        );

      setEvaluation(
        result
      );

      setAssessment(
        (current) => ({
          ...current,

          questions_answered:
            result.questions_answered,

          status:
            result.assessment_complete
              ? "completed"
              : current.status,
        })
      );

    } catch (evaluationError) {
      setError(
        evaluationError.message
      );

    } finally {
      setEvaluating(false);
    }
  }


  async function nextQuestion() {
    if (
      evaluation
        ?.assessment_complete
    ) {
      onComplete();
      return;
    }

    await generateQuestion();
  }


  async function abandonAssessment() {
    if (!assessment) {
      onBack();
      return;
    }

    const confirmed =
      window.confirm(
        "Abandon this assessment? " +
        "Your completed answers will remain in your history, " +
        "but this attempt will end."
      );

    if (!confirmed) {
      return;
    }

    try {
      await request(
        `/assessments/${assessment.id}/abandon`,
        {
          method: "POST",
        }
      );

      onBack();

    } catch (abandonError) {
      setError(
        abandonError.message
      );
    }
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


  function classificationLabel(
    classification
  ) {
    switch (
      classification
    ) {
      case "weak":
        return "Needs reinforcement";

      case "developing":
        return "Developing";

      case "competent":
        return "Good understanding";

      case "strong":
        return "Strong understanding";

      default:
        return classification;
    }
  }


  const answered =
    assessment?.questions_answered
    || 0;

  const maximum =
    assessment?.max_questions
    || 12;

  const displayQuestionNumber =
    evaluation
      ? answered
      : Math.min(
          answered + 1,
          maximum
        );

  const progress =
    maximum > 0
      ? (
          answered /
          maximum
        ) * 100
      : 0;


  if (loading) {
    return (
      <main className="assessment-page">

        <div className="assessment-loading">

          <div className="assessment-spinner" />

          <h2>
            Preparing your assessment
          </h2>

          <p>
            Restoring your learning state...
          </p>

        </div>

      </main>
    );
  }


  return (
    <main className="assessment-page">

      <div className="assessment-shell">

        <header className="assessment-header">

          <div>

            <button
              className="assessment-back"
              onClick={onBack}
            >
              ← Program
            </button>

            <div className="assessment-title-row">

              <div>

                <span className="dashboard-eyebrow">
                  Knowledge Assessment
                </span>

                <h1>
                  {programLabel()}
                </h1>

              </div>


              <div className="assessment-counter">

                <strong>
                  {displayQuestionNumber}
                </strong>

                <span>
                  / {maximum}
                </span>

              </div>

            </div>

          </div>


          <div className="assessment-progress">

            <div
              className="assessment-progress-fill"
              style={{
                width:
                  `${progress}%`,
              }}
            />

          </div>

        </header>


        {error && (
          <div className="assessment-error">
            {error}
          </div>
        )}


        {planning && (

          <section className="assessment-thinking">

            <div className="assessment-spinner" />

            <h2>
              Planning the next question
            </h2>

            <p>
              Daedalus is using your previous
              answers to choose the most useful
              diagnostic question.
            </p>

          </section>

        )}


        {!planning &&
          question &&
          !evaluation && (

          <section className="assessment-content">

            <div className="assessment-question-meta">

              <span className="assessment-concept">
                {question.concept}
              </span>

              <span
                className={
                  `assessment-difficulty ${
                    question.difficulty
                  }`
                }
              >
                {question.difficulty}
              </span>

            </div>


            <div className="assessment-question">

              <MarkdownMessage
                content={
                  question.question_text
                }
              />

            </div>


            <form
              className="assessment-answer-form"
              onSubmit={
                submitAnswer
              }
            >

              <label
                htmlFor="assessment-answer"
              >
                Your answer
              </label>

              <textarea
                id="assessment-answer"
                value={answer}
                onChange={(event) =>
                  setAnswer(
                    event.target.value
                  )
                }
                placeholder={
                  "Explain your understanding in your own words..."
                }
                rows={8}
                disabled={
                  evaluating
                }
              />


              <div className="assessment-answer-footer">

                <span>
                  Focus on what you understand.
                  Concise answers are fine.
                </span>

                <button
                  type="submit"
                  className="assessment-primary"
                  disabled={
                    evaluating ||
                    !answer.trim()
                  }
                >
                  {evaluating
                    ? "Evaluating..."
                    : "Submit answer"}
                </button>

              </div>

            </form>

          </section>

        )}


        {evaluating && (

          <div className="assessment-evaluating">

            <div className="assessment-spinner" />

            <span>
              Evaluating your answer...
            </span>

          </div>

        )}


        {!evaluating &&
          evaluation && (

          <section className="assessment-feedback">

            <div
              className={
                `assessment-result ${
                  evaluation.classification
                }`
              }
            >

              <div className="assessment-result-heading">

                <div>

                  <span className="dashboard-eyebrow">
                    Assessment Evidence
                  </span>

                  <h2>
                    {classificationLabel(
                      evaluation.classification
                    )}
                  </h2>

                </div>


                <div className="assessment-score">

                  {Math.round(
                    evaluation.score
                    * 100
                  )}

                  <span>
                    %
                  </span>

                </div>

              </div>


              <p className="assessment-feedback-text">
                {evaluation.feedback}
              </p>

            </div>


            <div className="assessment-evidence-grid">

              <div className="evidence-card demonstrated">

                <h3>
                  Demonstrated
                </h3>

                {evaluation
                  .demonstrated
                  .length > 0 ? (

                  <ul>

                    {evaluation
                      .demonstrated
                      .map(
                        (
                          item,
                          index
                        ) => (

                        <li key={index}>
                          {item}
                        </li>

                      )
                    )}

                  </ul>

                ) : (

                  <p>
                    No strong evidence was
                    identified yet.
                  </p>

                )}

              </div>


              <div className="evidence-card gaps">

                <h3>
                  Areas to strengthen
                </h3>

                {evaluation
                  .gaps
                  .length > 0 ? (

                  <ul>

                    {evaluation
                      .gaps
                      .map(
                        (
                          item,
                          index
                        ) => (

                        <li key={index}>
                          {item}
                        </li>

                      )
                    )}

                  </ul>

                ) : (

                  <p>
                    No significant gaps were
                    identified in this answer.
                  </p>

                )}

              </div>

            </div>


            <div className="assessment-next">

              <div>

                <span>
                  Progress
                </span>

                <strong>
                  {evaluation.questions_answered}
                  {" "}
                  of
                  {" "}
                  {evaluation.max_questions}
                  {" "}
                  questions completed
                </strong>

              </div>


              <button
                className="assessment-primary"
                onClick={
                  nextQuestion
                }
              >
                {evaluation
                  .assessment_complete
                  ? "Finish assessment"
                  : "Next question →"}
              </button>

            </div>

          </section>

        )}


        {!planning &&
          !question &&
          !evaluation &&
          assessment?.status ===
            "completed" && (

          <section className="assessment-finished">

            <span className="dashboard-eyebrow">
              Assessment Complete
            </span>

            <h2>
              Diagnostic assessment finished
            </h2>

            <p>
              Your responses have been saved.
              Daedalus can now use this evidence
              to build your knowledge profile.
            </p>

            <button
              className="assessment-primary"
              onClick={onComplete}
            >
              Return to program
            </button>

          </section>

        )}


        <footer className="assessment-footer">

          <div className="assessment-model">

            <span>
              Model
            </span>

            <strong>
              {selectedModel}
            </strong>

          </div>


          <button
            className="assessment-abandon"
            onClick={
              abandonAssessment
            }
          >
            Abandon assessment
          </button>

        </footer>

      </div>

    </main>
  );
}


export default AssessmentPage;