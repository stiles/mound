import type { CSSProperties } from "react";

type TerminalProps = {
  command: string;
  output: string;
  className?: string;
};

export function Terminal({ command, output, className = "" }: TerminalProps) {
  return (
    <div
      className={`overflow-hidden rounded-xl border border-grass-800/60 bg-grass-900 shadow-2xl shadow-grass-900/25 ${className}`}
    >
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="size-2.5 rounded-full bg-white/20" />
        <span className="ml-2 font-mono text-xs text-grass-300/70">
          zsh — mound
        </span>
      </div>

      <div className="overflow-x-auto px-4 py-4 sm:px-5">
        <pre className="font-mono text-[11px] leading-relaxed text-chalk sm:text-xs lg:text-[13px]">
          <code>
            <span className="text-grass-300 select-none">$ </span>
            <span
              className="type-out"
              style={{ "--chars": command.length } as CSSProperties}
            >
              {command}
            </span>
            <span className="type-caret text-grass-300" aria-hidden="true">
              ▊
            </span>
            {"\n"}
            <span className="type-output block pt-3 text-chalk/85">
              {output}
            </span>
          </code>
        </pre>
      </div>
    </div>
  );
}
