import Markdown from "react-markdown";

type Props = { content: string };

export default function ChatMarkdown({ content }: Props) {
  const explanationHeadings = [
    "Overview",
    "Typical skills",
    "Typical qualifications",
    "Ways to build skills and qualifications",
  ];
  const isLegacyExplanation = explanationHeadings.every((heading) =>
    content.split("\n").includes(heading),
  );
  const markdown = isLegacyExplanation
    ? content.split("\n").map((line) => explanationHeadings.includes(line) ? `### ${line}` : line).join("\n")
    : content;

  return (
    <div className="space-y-3 wrap-break-word text-sm leading-6 text-neutral-700">
      <Markdown
        skipHtml
        allowedElements={["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "strong", "em", "blockquote", "code", "pre", "a", "br", "hr"]}
        unwrapDisallowed
        components={{
          h1: ({ children }) => <h3 className="mt-5 text-base font-semibold text-primary-950 first:mt-0">{children}</h3>,
          h2: ({ children }) => <h3 className="mt-5 text-base font-semibold text-primary-950 first:mt-0">{children}</h3>,
          h3: ({ children }) => <h3 className="mt-5 text-base font-semibold text-primary-950 first:mt-0">{children}</h3>,
          h4: ({ children }) => <h4 className="mt-4 font-semibold text-primary-950">{children}</h4>,
          ul: ({ children }) => <ul className="list-disc space-y-2 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-2 pl-5">{children}</ol>,
          strong: ({ children }) => <strong className="font-semibold text-primary-950">{children}</strong>,
          blockquote: ({ children }) => <blockquote className="border-l-2 border-primary-300 pl-3 text-neutral-600">{children}</blockquote>,
          pre: ({ children }) => <pre className="overflow-x-auto rounded-lg bg-primary-50 p-3 text-xs">{children}</pre>,
          a: ({ children, href }) => href
            ? <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-700 underline underline-offset-2 hover:text-primary-900">{children}</a>
            : <span>{children}</span>,
        }}
      >
        {markdown}
      </Markdown>
    </div>
  );
}
