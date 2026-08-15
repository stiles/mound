import Link from "next/link";
import { site } from "@/lib/site";
import { GitHubIcon } from "@/components/icons";
import { ZoneMark } from "@/components/zone-mark";

const columns = [
  {
    heading: "Project",
    links: [
      { label: "Docs", href: site.docs },
      { label: "Examples", href: site.examples },
      { label: "Changelog", href: site.changelog },
    ],
  },
  {
    heading: "Install",
    links: [
      { label: "PyPI", href: site.pypi },
      { label: "Source on GitHub", href: site.repo },
      { label: "Report an issue", href: `${site.repo}/issues` },
      { label: "MIT license", href: `${site.repo}/blob/main/LICENSE` },
    ],
  },
  {
    heading: "Data",
    links: [
      { label: "MLB Stats API", href: "https://statsapi.mlb.com" },
      { label: "Baseball Savant", href: "https://baseballsavant.mlb.com" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="mt-auto bg-grass-900 text-chalk">
      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <div className="flex items-center gap-2.5">
              <ZoneMark className="h-6 w-auto text-grass-300" />
              <span className="font-mono text-lg font-semibold">mound</span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-chalk/60">
              {site.tagline}
            </p>
            <a
              href={site.repo}
              className="mt-5 inline-flex items-center gap-2 text-sm text-chalk/70 transition hover:text-chalk"
            >
              <GitHubIcon className="size-4" />
              stiles/mound
            </a>
          </div>

          {columns.map((column) => (
            <div key={column.heading}>
              <h2 className="font-mono text-xs tracking-widest text-grass-300 uppercase">
                {column.heading}
              </h2>
              <ul className="mt-4 space-y-2.5">
                {column.links.map((link) => (
                  <li key={link.label}>
                    {link.href.startsWith("/") ? (
                      <Link
                        href={link.href}
                        className="text-sm text-chalk/70 transition hover:text-chalk"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <a
                        href={link.href}
                        className="text-sm text-chalk/70 transition hover:text-chalk"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 border-t border-white/10 pt-8 text-xs leading-relaxed text-chalk/45">
          <p>
            Mound reads two public, unofficial MLB data services and is not
            affiliated with, endorsed by or sponsored by Major League Baseball.
          </p>
          <p className="mt-2">
            Built by{" "}
            <a
              href="https://mattstiles.me"
              className="text-chalk/70 underline decoration-white/25 underline-offset-4 transition hover:text-chalk"
            >
              {site.author}
            </a>
            . Released under the MIT license.
          </p>
        </div>
      </div>
    </footer>
  );
}
