import Link from "next/link";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  eyebrowHref,
  title,
  children,
}: {
  eyebrow: string;
  eyebrowHref?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="relative overflow-hidden border-b border-ink/10">
      <div
        aria-hidden="true"
        className="zone-grid pointer-events-none absolute inset-0 text-ink [mask-image:linear-gradient(to_bottom,black,transparent_85%)]"
      />
      <div className="relative mx-auto max-w-4xl px-5 pt-16 pb-12 sm:px-8 sm:pt-20 sm:pb-14">
        {eyebrowHref ? (
          <Link
            href={eyebrowHref}
            className="font-mono text-xs tracking-widest text-grass-700 uppercase transition hover:text-grass-800"
          >
            {eyebrow}
          </Link>
        ) : (
          <p className="font-mono text-xs tracking-widest text-grass-700 uppercase">
            {eyebrow}
          </p>
        )}

        <h1 className="mt-5 text-section font-semibold text-balance">{title}</h1>

        {children ? (
          <div className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
            {children}
          </div>
        ) : null}
      </div>
    </div>
  );
}
