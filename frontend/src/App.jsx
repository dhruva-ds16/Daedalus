import {
  useEffect,
  useRef,
  useState,
} from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  Prism as SyntaxHighlighter,
} from "react-syntax-highlighter";

import {
  vscDarkPlus,
} from "react-syntax-highlighter/dist/esm/styles/prism";

import "./App.css";


const API_URL = "/api";


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


function getErrorMessage(data) {
  if (!data) {
    return "Something went wrong.";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (item.msg) {
          return item.msg;
        }

        return "Invalid input.";
      })
      .join(" ");
  }

  return "Something went wrong.";
}


function CodeBlock({
  language,
  children,
}) {
  const [copied, setCopied] =
    useState(false);

  const code =
    String(children).replace(
      /\n$/,
      ""
    );


  async function copyCode() {
    try {
      await navigator.clipboard.writeText(
        code
      );

      setCopied(true);

      setTimeout(() => {
        setCopied(false);
      }, 1500);

    } catch {
      setCopied(false);
    }
  }


  return (
    <div className="code-block">

      <div className="code-header">

        <span className="code-language">
          {language || "text"}
        </span>

        <button
          className="copy-button"
          onClick={copyCode}
        >
          {copied
            ? "Copied"
            : "Copy"}
        </button>

      </div>

      <SyntaxHighlighter
        language={
          language || "text"
        }
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          borderRadius:
            "0 0 8px 8px",
          padding: "18px",
          background: "#0d1117",
          fontSize: "14px",
        }}
        wrapLongLines={true}
      >
        {code}
      </SyntaxHighlighter>

    </div>
  );
}


function MarkdownMessage({
  content,
}) {
  return (
    <ReactMarkdown
      remarkPlugins={[
        remarkGfm,
      ]}
      components={{
        code({
          inline,
          className,
          children,
          ...props
        }) {
          const match =
            /language-(\w+)/.exec(
              className || ""
            );

          const language =
            match
              ? match[1]
              : "";

          if (!inline && match) {
            return (
              <CodeBlock
                language={language}
              >
                {children}
              </CodeBlock>
            );
          }

          return (
            <code
              className="inline-code"
              {...props}
            >
              {children}
            </code>
          );
        },

        table({
          children,
        }) {
          return (
            <div className="table-wrapper">
              <table>
                {children}
              </table>
            </div>
          );
        },

        a({
          children,
          href,
          ...props
        }) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              {...props}
            >
              {children}
            </a>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
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
      password !== confirmPassword
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


  async function handleSubmit(event) {
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

        <h1>
          DAEDALUS
        </h1>

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
              switchMode("register")
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

              <label htmlFor="confirm-password">
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
              Minimum 10 characters with
              at least one letter and one number.
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
          >
          </span>

          {backendOnline
            ? "Daedalus backend online"
            : "Daedalus backend offline"}

        </div>

      </div>

    </div>
  );
}


function TutorApp({
  user,
  onLogout,
}) {
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
        throw new Error(
          `HTTP ${response.status}`
        );
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

      if (
        response.status === 401
      ) {
        onLogout();

        return;
      }

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data =
        await response.json();

      const availableModels =
        data.models || [];

      setModels(
        availableModels
      );

      if (
        availableModels.length === 0
      ) {
        setStartupError(
          "No Ollama models are installed."
        );

        return;
      }

      const savedModel =
        localStorage.getItem(
          "daedalus-selected-model"
        );

      const savedModelExists =
        availableModels.some(
          (model) =>
            model.name ===
            savedModel
        );

      if (
        savedModel &&
        savedModelExists
      ) {
        setSelectedModel(
          savedModel
        );

      } else {
        const firstModel =
          availableModels[0].name;

        setSelectedModel(
          firstModel
        );

        localStorage.setItem(
          "daedalus-selected-model",
          firstModel
        );
      }

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

    const conversationForRequest = [
      ...messages,
      userMessage,
    ];

    setMessages([
      ...conversationForRequest,
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

    const requestStart =
      performance.now();

    let receivedFirstToken =
      false;

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
                conversationForRequest,
            }),

            signal:
              controller.signal,
          }
        );


      if (
        response.status === 401
      ) {
        onLogout();

        return;
      }


      if (!response.ok) {
        throw new Error(
          `Server returned HTTP ${response.status}`
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

        buffer +=
          decoder.decode(
            value,
            {
              stream: true,
            }
          );

        const lines =
          buffer.split("\n");

        buffer =
          lines.pop() || "";


        for (
          const line of lines
        ) {
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
            event.type ===
            "token"
          ) {
            if (
              !receivedFirstToken
            ) {
              receivedFirstToken =
                true;

              const elapsed =
                performance.now()
                - requestStart;

              setFirstTokenMs(
                Math.round(
                  elapsed
                )
              );
            }


            setMessages(
              (
                currentMessages
              ) => {
                const updatedMessages =
                  [
                    ...currentMessages,
                  ];

                const lastIndex =
                  updatedMessages.length
                  - 1;

                const assistantMessage =
                  {
                    ...updatedMessages[
                      lastIndex
                    ],
                  };

                assistantMessage.content +=
                  event.content;

                updatedMessages[
                  lastIndex
                ] =
                  assistantMessage;

                return updatedMessages;
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
            event.type ===
            "error"
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
          (
            currentMessages
          ) => {
            const updatedMessages =
              [
                ...currentMessages,
              ];

            const lastIndex =
              updatedMessages.length
              - 1;

            if (
              updatedMessages[
                lastIndex
              ]?.role ===
              "assistant"
            ) {
              updatedMessages[
                lastIndex
              ] = {
                ...updatedMessages[
                  lastIndex
                ],

                content:
                  updatedMessages[
                    lastIndex
                  ].content +
                  "\n\n*Generation stopped.*",
              };
            }

            return updatedMessages;
          }
        );

      } else {
        setMessages(
          (
            currentMessages
          ) => {
            const updatedMessages =
              [
                ...currentMessages,
              ];

            const lastIndex =
              updatedMessages.length
              - 1;

            updatedMessages[
              lastIndex
            ] = {
              role: "assistant",

              content:
                `Unable to communicate with Daedalus: ${error.message}`,
            };

            return updatedMessages;
          }
        );

        await checkHealth();
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


  async function logout() {
    if (loading) {
      return;
    }

    try {
      await fetch(
        `${API_URL}/auth/logout`,
        {
          method: "POST",
          credentials: "include",
        }
      );

    } finally {
      onLogout();
    }
  }


  const ready =
    backendOnline &&
    ollamaOnline &&
    selectedModel;


  return (
    <div className="app">

      <header className="header">

        <div className="brand">

          <h1>
            DAEDALUS
          </h1>

          <p>
            Windows Internals
            & Rust Tutor
          </p>

        </div>


        <div className="header-actions">

          <div className="model-selector-container">

            <span className="model-selector-label">
              Model
            </span>

            <select
              className="model-selector"
              value={
                selectedModel
              }
              onChange={
                handleModelChange
              }
              disabled={
                loading ||
                models.length === 0
              }
            >

              {models.length ===
                0 && (
                <option value="">
                  No models
                </option>
              )}

              {models.map(
                (model) => (
                  <option
                    key={
                      model.name
                    }
                    value={
                      model.name
                    }
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


          {messages.length > 0 && (
            <button
              className="clear-button"
              onClick={
                clearConversation
              }
              disabled={loading}
            >
              Clear
            </button>
          )}


          <div className="service-status">

            <div className="status">

              <span
                className={
                  `status-dot ${
                    backendOnline
                      ? "online"
                      : "offline"
                  }`
                }
              >
              </span>

              Backend

            </div>

            <div className="status">

              <span
                className={
                  `status-dot ${
                    ollamaOnline
                      ? "online"
                      : "offline"
                  }`
                }
              >
              </span>

              Ollama

            </div>

          </div>


          <div className="user-menu">

            <span className="username">
              {user.username}
            </span>

            <button
              className="logout-button"
              onClick={logout}
              disabled={loading}
            >
              Logout
            </button>

          </div>

        </div>

      </header>


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
              Checking local AI
              services...
            </p>

          </div>
        )}


        {!initializing &&
          startupError &&
          messages.length ===
            0 && (

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

            <button
              className="retry-button"
              onClick={
                initializeDaedalus
              }
            >
              Retry
            </button>

          </div>
        )}


        {!initializing &&
          !startupError &&
          messages.length ===
            0 && (

          <div className="welcome">

            <div className="logo">
              D
            </div>

            <h2>
              What are we
              learning today?
            </h2>

            <p>
              Ask about Windows
              Internals, Rust,
              or systems programming.
            </p>

          </div>
        )}


        {messages.length > 0 && (
          <div className="conversation">

            {messages.map(
              (
                message,
                index
              ) => (

                <div
                  key={index}
                  className={
                    `message ${
                      message.role ===
                      "user"
                        ? "user-message"
                        : "tutor-message"
                    }`
                  }
                >

                  <div className="message-label">

                    {message.role ===
                    "user"
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
                        messages.length
                        - 1 &&
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
                        firstTokenMs
                        / 1000
                      ).toFixed(2)}s`
                    : "—"}
                </span>

                <span>
                  {
                    currentMetrics.generated_tokens
                  }{" "}
                  tokens
                </span>

                <span>
                  {
                    currentMetrics.tokens_per_second
                  }{" "}
                  tok/s
                </span>

                <span>
                  {formatDuration(
                    currentMetrics.total_duration_ms
                  )}
                </span>

              </div>

            )}


            <div
              ref={bottomRef}
            >
            </div>

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
              loading ||
              !ready
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
              onClick={
                sendMessage
              }
              disabled={
                !input.trim() ||
                !ready
              }
            >
              Send
            </button>

          )}

        </div>


        <div className="composer-info">

          <span>
            {selectedModel ||
              "No model selected"}
          </span>

          <span>
            Enter to send
            {" · "}
            Shift+Enter for newline
          </span>

        </div>

      </div>

    </div>
  );
}


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


  useEffect(() => {
    initializeApplication();
  }, []);


  async function initializeApplication() {
    setCheckingSession(true);

    let backendIsOnline = false;

    try {
      const healthResponse =
        await fetch(
          `${API_URL}/health`,
          {
            credentials: "include",
          }
        );

      if (healthResponse.ok) {
        const health =
          await healthResponse.json();

        backendIsOnline =
          health.backend === "online";
      }

    } catch {
      backendIsOnline = false;
    }


    setBackendOnline(
      backendIsOnline
    );


    if (!backendIsOnline) {
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
  }


  function handleLogout() {
    setUser(null);
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
    <TutorApp
      user={user}
      onLogout={
        handleLogout
      }
    />
  );
}


export default App;