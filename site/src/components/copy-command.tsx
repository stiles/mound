"use client";

import { useEffect, useState } from "react";

export function CopyCommand({
  command,
  className = "",
}: {
  command: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1800);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
    } catch {
      // Clipboard is unavailable over plain HTTP and when permission is
      // denied; the command is selectable either way.
    }
  }

  return (
    <div
      className={`group flex items-center gap-3 rounded-lg border border-ink/15 bg-paper py-2.5 pr-2.5 pl-4 ${className}`}
    >
      <code className="flex-1 font-mono text-sm text-ink sm:text-base">
        <span className="mr-2 text-grass-700 select-none">$</span>
        {command}
      </code>
      <button
        type="button"
        onClick={copy}
        aria-label={`Copy "${command}" to the clipboard`}
        className="rounded-md px-2.5 py-1.5 font-mono text-xs font-medium text-muted transition hover:bg-grass-50 hover:text-grass-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700"
      >
        {copied ? "copied" : "copy"}
      </button>
    </div>
  );
}
