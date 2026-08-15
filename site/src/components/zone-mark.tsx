/** The strike zone plot_zone() draws, reduced to a mark: a 3x3 grid and one
 *  pitch low and away. Doubles as the logo and the favicon. */
export function ZoneMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 28"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <rect
        x="1"
        y="1"
        width="22"
        height="26"
        rx="1.25"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M8.33 1v26M15.67 1v26M1 9.67h22M1 18.33h22"
        stroke="currentColor"
        strokeWidth="1"
        opacity="0.4"
      />
      <circle cx="17.4" cy="22.2" r="3.1" fill="currentColor" />
    </svg>
  );
}
