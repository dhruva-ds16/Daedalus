import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

import "./App.css";


const MODEL = "FieldMouse-AI/qwen3.5:9b-Q3_K_S-instruct";
const API_URL = "http://127.0.0.1:8000";


function CodeBlock({
  language,
  children,
}) {
  const [copied, setCopied] = useState(false);

  const code = String(children).replace(/\n$/, "");

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);

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
          {copied ? "Copied" : "Copy"}
        </button>

      </div>

      <SyntaxHighlighter
        language={language || "text"}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          borderRadius: "0 0 8px 8px",
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
      remarkPlugins={[remarkGfm]}
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

          const language = match
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

        table({ children }) {
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


function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef(null);


  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);


  async function sendMessage() {
    const question = input.trim();

    if (!question || loading) {
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

    try {
      const res = await fetch(
        `${API_URL}/chat/stream`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            model: MODEL,
            messages: conversationForRequest,
          }),
        }
      );

      if (!res.ok) {
        throw new Error(
          `Server returned HTTP ${res.status}`
        );
      }

      if (!res.body) {
        throw new Error(
          "Streaming response is unavailable."
        );
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const {
          value,
          done,
        } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(
          value,
          {
            stream: true,
          }
        );

        setMessages(
          (currentMessages) => {
            const updatedMessages = [
              ...currentMessages,
            ];

            const lastIndex =
              updatedMessages.length - 1;

            const assistantMessage = {
              ...updatedMessages[lastIndex],
            };

            assistantMessage.content +=
              chunk;

            updatedMessages[lastIndex] =
              assistantMessage;

            return updatedMessages;
          }
        );
      }
    } catch (error) {
      setMessages(
        (currentMessages) => {
          const updatedMessages = [
            ...currentMessages,
          ];

          const lastIndex =
            updatedMessages.length - 1;

          updatedMessages[lastIndex] = {
            role: "assistant",
            content:
              `Unable to communicate with Daedalus: ${error.message}`,
          };

          return updatedMessages;
        }
      );
    } finally {
      setLoading(false);
    }
  }


  function clearConversation() {
    if (loading) {
      return;
    }

    setMessages([]);
  }


  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  }


  return (
    <div className="app">

      <header className="header">

        <div>
          <h1>DAEDALUS</h1>

          <p>
            Windows Internals & Rust Tutor
          </p>
        </div>

        <div className="header-actions">

          {messages.length > 0 && (
            <button
              className="clear-button"
              onClick={clearConversation}
              disabled={loading}
            >
              Clear
            </button>
          )}

          <div className="status">
            <span className="status-dot">
            </span>

            Local AI
          </div>

        </div>

      </header>


      <main className="chat">

        {messages.length === 0 && (
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

            <div ref={bottomRef}></div>

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
            onKeyDown={handleKeyDown}
            placeholder="Ask Daedalus..."
            disabled={loading}
            rows={2}
          />

          <button
            onClick={sendMessage}
            disabled={
              loading ||
              !input.trim()
            }
          >
            {loading
              ? "Thinking..."
              : "Send"}
          </button>

        </div>

        <div className="model-name">
          {MODEL}
        </div>

      </div>

    </div>
  );
}


export default App;