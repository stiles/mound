import type { CSSProperties } from "react";

type TerminalProps = {
  command: string;
  output: string;
  className?: string;
  /** The typing animation is keyed to a fixed delay from page load, so it only
   *  reads as typing above the fold. Further down it has long since finished
   *  and leaves a caret blinking at a command nobody watched arrive. */
  animate?: boolean;
};

export function Terminal({
  command,
  output,
  className = "",
  animate = true,
}: TerminalProps) {
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
            {animate ? (
              <>
                <span
                  className="type-out"
                  style={{ "--chars": command.length } as CSSProperties}
                >
                  {command}
                </span>
                <span className="type-caret text-grass-300" aria-hidden="true">
                  ▊
                </span>
              </>
            ) : (
              <span className="whitespace-pre">{command}</span>
            )}
            {"\n"}
            <span
              className={`block pt-3 text-chalk/85 ${animate ? "type-output" : ""}`}
            >
              {output}
            </span>
          </code>
        </pre>
      </div>
    </div>
  );
}
