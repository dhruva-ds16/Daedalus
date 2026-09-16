import { useState } from "react";

import {
  Prism as SyntaxHighlighter,
} from "react-syntax-highlighter";

import {
  vscDarkPlus,
} from "react-syntax-highlighter/dist/esm/styles/prism";


function CodeBlock({
  language,
  children,
}) {
  const [copied, setCopied] =
    useState(false);

  const code = String(
    children
  ).replace(/\n$/, "");


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
      language={language || "text"}
      style={vscDarkPlus}
      customStyle={{
        margin: 0,
        borderRadius: "0 0 8px 8px",
        padding: "20px",
        background: "#0d1117",
        fontSize: "15px",
        lineHeight: "1.65",
      }}
      wrapLongLines={true}
    >
      {code}
    </SyntaxHighlighter>
    </div>
  );
}


export default CodeBlock;