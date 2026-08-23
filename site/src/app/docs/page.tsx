import type { Metadata } from "next";
import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";
import { PageHeader } from "@/components/page-header";
import { getDoc } from "@/lib/docs";
import { renderMarkdown } from "@/lib/markdown";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Docs",
  description: site.description,
};

export default async function DocsPage() {
  const doc = await getDoc();
  const html = await renderMarkdown(doc.body);

  return (
    <>
      <Nav />
      <main>
        <PageHeader eyebrow="Docs" title="Every command and every metric.">
          <p>{doc.summary}</p>
        </PageHeader>

        <article className="mx-auto max-w-4xl px-5 py-14 sm:px-8 sm:py-20">
          <div
            className="prose-mound prose max-w-none"
            dangerouslySetInnerHTML={{ __html: html }}
          />

          <div className="mt-16 rounded-xl border border-ink/12 bg-grass-50 p-7">
            <h2 className="font-semibold text-ink">One source, two places</h2>
            <p className="mt-2 text-sm leading-relaxed text-grass-900/70">
              This page renders the repo&rsquo;s own{" "}
              <code className="code-inline">README.md</code>, the same file that
              ships with the package on PyPI, so the two can&rsquo;t disagree
              about what a command does.
            </p>
            <a
              href={`${site.repo}#readme`}
              className="mt-4 inline-flex text-sm font-medium text-grass-700 underline decoration-grass-700/30 underline-offset-4 transition hover:decoration-grass-700"
            >
              View the source on GitHub
            </a>
          </div>
        </article>
      </main>
      <Footer />
    </>
  );
}
