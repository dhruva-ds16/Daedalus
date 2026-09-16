import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import CodeBlock from "./CodeBlock";


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


export default MarkdownMessage;