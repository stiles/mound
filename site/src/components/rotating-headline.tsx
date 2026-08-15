import type { CSSProperties } from "react";

const SECONDS_PER_VERB = 2.4;

type RotatingHeadlineProps = {
  verbs: readonly string[];
  tail: string;
};

/** Reads as one sentence — "Find every pitch." — with only the verb cycling.
 *  The verbs share a single grid cell so the tail never reflows, and the
 *  whole stack is hidden from assistive tech in favor of one static reading. */
export function RotatingHeadline({ verbs, tail }: RotatingHeadlineProps) {
  const cycle = verbs.length * SECONDS_PER_VERB;
  const resting = verbs[verbs.length - 1];

  return (
    <>
      <span className="sr-only">{`${resting} ${tail}`}</span>

      <span aria-hidden="true" className="block">
        <span
          className="verb-cycle grid text-grass-700"
          style={{ "--cycle": `${cycle}s` } as CSSProperties}
        >
          {verbs.map((verb, index) => (
            <span
              key={verb}
              className="col-start-1 row-start-1 justify-self-start"
              style={{ animationDelay: `${index * SECONDS_PER_VERB}s` }}
            >
              {verb}
            </span>
          ))}
        </span>
        <span className="block">{tail}</span>
      </span>
    </>
  );
}
