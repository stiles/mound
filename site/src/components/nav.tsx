import Link from "next/link";
import { site } from "@/lib/site";
import { GitHubIcon } from "@/components/icons";
import { ZoneMark } from "@/components/zone-mark";

const links = [
  { label: "Docs", href: site.docs },
  { label: "Examples", href: site.examples },
  { label: "Changelog", href: site.changelog },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-ink/10 bg-paper-warm/85 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-grass-700"
        >
          <ZoneMark className="h-6 w-auto text-grass-700" />
          <span className="font-mono text-lg font-semibold tracking-tight text-ink">
            mound
          </span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => {
            const className =
              "rounded-md px-3 py-2 text-sm font-medium text-muted transition hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700";

            return link.href.startsWith("/") ? (
              <Link key={link.label} href={link.href} className={className}>
                {link.label}
              </Link>
            ) : (
              <a key={link.label} href={link.href} className={className}>
                {link.label}
              </a>
            );
          })}
          <a
            href={site.repo}
            aria-label="Mound on GitHub"
            className="ml-1 rounded-md p-2 text-muted transition hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700"
          >
            <GitHubIcon className="size-5" />
          </a>
        </div>
      </nav>
    </header>
  );
}
