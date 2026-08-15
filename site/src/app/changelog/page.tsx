import type { Metadata } from "next";
import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";
import { PageHeader } from "@/components/page-header";
import { formatDate, getReleases } from "@/lib/docs";
import { renderMarkdown } from "@/lib/markdown";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Changelog",
  description: `Every release of Mound, from the initial prototype to the current version.`,
};

export default async function ChangelogPage() {
  const releases = await getReleases();
  const rendered = await Promise.all(
    releases.map(async (release) => ({
      ...release,
      html: await renderMarkdown(release.body),
    })),
  );

  return (
    <>
      <Nav />
      <main>
        <PageHeader eyebrow="Changelog" title="Every release, in order.">
          <p>
            Rendered from the repo&rsquo;s own{" "}
            <a
              href={`${site.repo}/blob/main/CHANGELOG.md`}
              className="text-grass-700 underline decoration-grass-700/30 underline-offset-4 transition hover:decoration-grass-700"
            >
              CHANGELOG.md
            </a>
            , so this page and the package can&rsquo;t disagree.
          </p>
        </PageHeader>

        <div className="mx-auto max-w-4xl px-5 py-14 sm:px-8 sm:py-20">
          {rendered.map((release, index) => (
            <section
              key={release.version}
              id={`v${release.version}`}
              className={
                index === 0
                  ? "scroll-mt-24"
                  : "mt-14 scroll-mt-24 border-t border-ink/10 pt-14"
              }
            >
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <h2 className="font-mono text-2xl font-semibold tracking-tight text-ink">
                  {release.version}
                </h2>
                <time className="font-mono text-sm text-muted">
                  {formatDate(release.date)}
                </time>
                {index === 0 ? (
                  <span className="rounded-full bg-grass-50 px-2.5 py-1 font-mono text-xs text-grass-700">
                    latest
                  </span>
                ) : null}
              </div>

              <div
                className="prose-mound prose mt-6 max-w-none"
                dangerouslySetInnerHTML={{ __html: release.html }}
              />
            </section>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
