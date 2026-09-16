import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  API_URL,
} from "../config";

import MarkdownMessage from "./MarkdownMessage";


function formatModelSize(bytes) {
  if (!bytes) {
    return "";
  }

  const gigabytes =
    bytes / 1024 / 1024 / 1024;

  return `${gigabytes.toFixed(1)} GB`;
}


function formatDuration(milliseconds) {
  if (!milliseconds) {
    return "0.0s";
  }

  return `${(
    milliseconds / 1000
  ).toFixed(1)}s`;
}


function TutorApp() {
  const [input, setInput] =
    useState("");

  const [messages, setMessages] =
    useState([]);

  const [loading, setLoading] =
    useState(false);

  const [models, setModels] =
    useState([]);

  const [
    selectedModel,
    setSelectedModel,
  ] = useState("");

  const [
    backendOnline,
    setBackendOnline,
  ] = useState(true);

  const [
    ollamaOnline,
    setOllamaOnline,
  ] = useState(false);

  const [
    initializing,
    setInitializing,
  ] = useState(true);

  const [
    startupError,
    setStartupError,
  ] = useState("");

  const [
    currentMetrics,
    setCurrentMetrics,
  ] = useState(null);

  const [
    firstTokenMs,
    setFirstTokenMs,
  ] = useState(null);

  const bottomRef =
    useRef(null);

  const abortControllerRef =
    useRef(null);


  useEffect(() => {
    initializeDaedalus();

    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);


  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);


  async function initializeDaedalus() {
    setInitializing(true);
    setStartupError("");

    const healthOkay =
      await checkHealth();

    if (healthOkay) {
      await loadModels();
    }

    setInitializing(false);
  }


  async function checkHealth() {
    try {
      const response =
        await fetch(
          `${API_URL}/health`,
          {
            credentials: "include",
          }
        );

      if (!response.ok) {
        throw new Error();
      }

      const data =
        await response.json();

      setBackendOnline(
        data.backend === "online"
      );

      setOllamaOnline(
        data.ollama === "online"
      );

      return (
        data.backend === "online"
      );

    } catch {
      setBackendOnline(false);
      setOllamaOnline(false);

      return false;
    }
  }


  async function loadModels() {
    try {
      const response =
        await fetch(
          `${API_URL}/models`,
          {
            credentials: "include",
          }
        );

      if (!response.ok) {
        throw new Error();
      }

      const data =
        await response.json();

      const available =
        data.models || [];

      setModels(available);

      if (available.length === 0) {
        setStartupError(
          "No Ollama models are installed."
        );

        return;
      }

      const saved =
        localStorage.getItem(
          "daedalus-selected-model"
        );

      const exists =
        available.some(
          (model) =>
            model.name === saved
        );

      const model =
        saved && exists
          ? saved
          : available[0].name;

      setSelectedModel(model);

      localStorage.setItem(
        "daedalus-selected-model",
        model
      );

    } catch {
      setStartupError(
        "Unable to retrieve Ollama models."
      );
    }
  }


  function handleModelChange(
    event
  ) {
    const model =
      event.target.value;

    if (
      messages.length > 0 &&
      model !== selectedModel
    ) {
      const confirmed =
        window.confirm(
          "Changing models will clear the current conversation. Continue?"
        );

      if (!confirmed) {
        return;
      }
    }

    setSelectedModel(model);

    localStorage.setItem(
      "daedalus-selected-model",
      model
    );

    setMessages([]);
    setCurrentMetrics(null);
    setFirstTokenMs(null);
  }


  async function sendMessage() {
    const question =
      input.trim();

    if (
      !question ||
      loading ||
      !selectedModel ||
      !backendOnline ||
      !ollamaOnline
    ) {
      return;
    }

    const userMessage = {
      role: "user",
      content: question,
    };

    const conversation = [
      ...messages,
      userMessage,
    ];

    setMessages([
      ...conversation,
      {
        role: "assistant",
        content: "",
      },
    ]);

    setInput("");
    setLoading(true);
    setCurrentMetrics(null);
    setFirstTokenMs(null);

    const controller =
      new AbortController();

    abortControllerRef.current =
      controller;

    const start =
      performance.now();

    let firstToken = false;


    try {
      const response =
        await fetch(
          `${API_URL}/chat/stream`,
          {
            method: "POST",
            credentials: "include",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              model:
                selectedModel,

              messages:
                conversation,
            }),

            signal:
              controller.signal,
          }
        );


      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }


      if (!response.body) {
        throw new Error(
          "Streaming response is unavailable."
        );
      }


      const reader =
        response.body.getReader();

      const decoder =
        new TextDecoder();

      let buffer = "";


      while (true) {
        const {
          value,
          done,
        } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(
          value,
          {
            stream: true,
          }
        );

        const lines =
          buffer.split("\n");

        buffer =
          lines.pop() || "";


        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }

          let event;

          try {
            event =
              JSON.parse(line);
          } catch {
            continue;
          }


          if (
            event.type === "token"
          ) {
            if (!firstToken) {
              firstToken = true;

              setFirstTokenMs(
                Math.round(
                  performance.now()
                  - start
                )
              );
            }

            setMessages(
              (current) => {
                const updated = [
                  ...current,
                ];

                const index =
                  updated.length - 1;

                updated[index] = {
                  ...updated[index],

                  content:
                    updated[index]
                      .content
                    + event.content,
                };

                return updated;
              }
            );
          }


          if (
            event.type ===
            "metrics"
          ) {
            setCurrentMetrics(
              event.metrics
            );
          }


          if (
            event.type === "error"
          ) {
            throw new Error(
              event.message
            );
          }
        }
      }

    } catch (error) {

      if (
        error.name ===
        "AbortError"
      ) {
        setMessages(
          (current) => {
            const updated = [
              ...current,
            ];

            const index =
              updated.length - 1;

            if (
              updated[index]?.role ===
              "assistant"
            ) {
              updated[index] = {
                ...updated[index],

                content:
                  updated[index].content
                  + "\n\n*Generation stopped.*",
              };
            }

            return updated;
          }
        );

      } else {
        setMessages(
          (current) => {
            const updated = [
              ...current,
            ];

            const index =
              updated.length - 1;

            updated[index] = {
              role: "assistant",

              content:
                `Unable to communicate with Daedalus: ${error.message}`,
            };

            return updated;
          }
        );
      }

    } finally {
      setLoading(false);

      abortControllerRef.current =
        null;
    }
  }


  function stopGeneration() {
    abortControllerRef.current?.abort();
  }


  function clearConversation() {
    if (loading) {
      return;
    }

    setMessages([]);
    setCurrentMetrics(null);
    setFirstTokenMs(null);
  }


  function handleKeyDown(
    event
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage();
    }
  }


  const ready =
    backendOnline &&
    ollamaOnline &&
    selectedModel;


  return (
    <>

      <main className="chat">

        {initializing && (
          <div className="welcome">

            <div className="logo">
              D
            </div>

            <h2>
              Starting Daedalus
            </h2>

            <p>
              Discovering local models...
            </p>

          </div>
        )}


        {!initializing &&
          startupError &&
          messages.length === 0 && (

          <div className="welcome">

            <div className="logo error-logo">
              !
            </div>

            <h2>
              Daedalus is not ready
            </h2>

            <p>
              {startupError}
            </p>

          </div>
        )}


        {!initializing &&
          !startupError &&
          messages.length === 0 && (

          <div className="welcome">

            <div className="logo">
              D
            </div>

            <h2>
              What are we learning today?
            </h2>

            <p>
              Ask about Windows Internals,
              Rust, or systems programming.
            </p>

          </div>
        )}


        {messages.length > 0 && (
          <div className="conversation">

            {messages.map(
              (message, index) => (

                <div
                  key={index}
                  className={
                    `message ${
                      message.role === "user"
                        ? "user-message"
                        : "tutor-message"
                    }`
                  }
                >

                  <div className="message-label">
                    {message.role === "user"
                      ? "You"
                      : "Daedalus"}
                  </div>

                  <div className="message-content">

                    {message.role ===
                    "assistant" ? (

                      <MarkdownMessage
                        content={
                          message.content
                        }
                      />

                    ) : (
                      message.content
                    )}

                    {loading &&
                      index ===
                        messages.length - 1 &&
                      message.role ===
                        "assistant" && (

                        <span className="cursor">
                          ▋
                        </span>

                      )}

                  </div>

                </div>
              )
            )}


            {!loading &&
              currentMetrics && (

              <div className="metrics">

                <span>
                  TTFT{" "}
                  {firstTokenMs
                    ? `${(
                        firstTokenMs / 1000
                      ).toFixed(2)}s`
                    : "—"}
                </span>

                <span>
                  {
                    currentMetrics
                      .generated_tokens
                  }{" "}
                  tokens
                </span>

                <span>
                  {
                    currentMetrics
                      .tokens_per_second
                  }{" "}
                  tok/s
                </span>

                <span>
                  {formatDuration(
                    currentMetrics
                      .total_duration_ms
                  )}
                </span>

              </div>

            )}

            <div ref={bottomRef} />

          </div>
        )}

      </main>


      <div className="composer-container">

        <div className="composer">

          <textarea
            value={input}
            onChange={(event) =>
              setInput(
                event.target.value
              )
            }
            onKeyDown={
              handleKeyDown
            }
            placeholder={
              ready
                ? "Ask Daedalus..."
                : "Daedalus is not ready..."
            }
            disabled={
              loading || !ready
            }
            rows={2}
          />


          {loading ? (

            <button
              className="stop-button"
              onClick={
                stopGeneration
              }
            >
              Stop
            </button>

          ) : (

            <button
              onClick={sendMessage}
              disabled={
                !input.trim() ||
                !ready
              }
            >
              Send
            </button>

          )}

        </div>


        <div className="composer-toolbar">

          <div className="composer-model">

            <label
              htmlFor="model-selector"
            >
              Model
            </label>

            <select
              id="model-selector"
              value={selectedModel}
              onChange={
                handleModelChange
              }
              disabled={
                loading ||
                models.length === 0
              }
            >

              {models.length === 0 && (
                <option value="">
                  No models available
                </option>
              )}

              {models.map(
                (model) => (

                  <option
                    key={model.name}
                    value={model.name}
                  >
                    {model.name}

                    {model.size
                      ? ` (${formatModelSize(
                          model.size
                        )})`
                      : ""}
                  </option>

                )
              )}

            </select>

          </div>


          <div className="composer-toolbar-right">

            <div className="mini-service-status">

              <span
                className={
                  `status-dot ${
                    backendOnline
                      ? "online"
                      : "offline"
                  }`
                }
              />

              Backend

              <span
                className={
                  `status-dot ${
                    ollamaOnline
                      ? "online"
                      : "offline"
                  }`
                }
              />

              Ollama

            </div>


            {messages.length > 0 && (

              <button
                className="text-button"
                onClick={
                  clearConversation
                }
                disabled={loading}
              >
                Clear conversation
              </button>

            )}

          </div>

        </div>

      </div>

    </>
  );
}


export default TutorApp;