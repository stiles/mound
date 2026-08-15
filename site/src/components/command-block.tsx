export function CommandBlock({
  commands,
  className = "",
}: {
  commands: readonly string[];
  className?: string;
}) {
  return (
    <div
      className={`overflow-x-auto rounded-xl border border-grass-800/60 bg-grass-900 px-4 py-4 sm:px-5 ${className}`}
    >
      <pre className="font-mono text-[11px] leading-loose text-chalk sm:text-xs lg:text-[13px]">
        <code>
          {commands.map((command) => (
            <span key={command} className="block whitespace-pre">
              <span className="text-grass-300 select-none">$ </span>
              {command}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
