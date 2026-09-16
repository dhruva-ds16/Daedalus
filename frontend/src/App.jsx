import { useState } from "react";
import "./App.css";

const MODEL = "FieldMouse-AI/qwen3.5:9b-Q3_K_S-instruct";
const API_URL = "http://127.0.0.1:8000";

function App() {
  const [message, setMessage] = useState("");
  const [submittedMessage, setSubmittedMessage] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    const question = message.trim();

    if (!question || loading) {
      return;
    }

    setSubmittedMessage(question);
    setMessage("");
    setResponse("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: question,
          model: MODEL,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      if (!res.body) {
        throw new Error("Streaming response is unavailable.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value, {
          stream: true,
        });

        setResponse((previous) => previous + chunk);
      }
    } catch (error) {
      setResponse(
        `Unable to communicate with Daedalus: ${error.message}`
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>DAEDALUS</h1>
          <p>Windows Internals & Rust Tutor</p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          Local AI
        </div>
      </header>

      <main className="chat">
        {!submittedMessage && (
          <div className="welcome">
            <div className="logo">D</div>

            <h2>What are we learning today?</h2>

            <p>
              Ask about Windows Internals, Rust, or systems
              programming.
            </p>
          </div>
        )}

        {submittedMessage && (
          <div className="conversation">
            <div className="message user-message">
              <div className="message-label">You</div>

              <div className="message-content">
                {submittedMessage}
              </div>
            </div>

            <div className="message tutor-message">
              <div className="message-label">Daedalus</div>

              <div className="message-content">
                {response}

                {loading && <span className="cursor">▋</span>}
              </div>
            </div>
          </div>
        )}
      </main>

      <div className="composer-container">
        <div className="composer">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Daedalus..."
            disabled={loading}
            rows={2}
          />

          <button
            onClick={sendMessage}
            disabled={loading || !message.trim()}
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>

        <div className="model-name">{MODEL}</div>
      </div>
    </div>
  );
}

export default App;
