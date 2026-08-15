import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/footer";
import { ArrowIcon } from "@/components/icons";
import { Nav } from "@/components/nav";
import { PageHeader } from "@/components/page-header";
import { getExamples } from "@/lib/docs";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Examples",
  description:
    "Worked examples that go from a question to an answer using Mound, with every command runnable as written.",
};

export default async function ExamplesPage() {
  const examples = await getExamples();

  return (
    <>
      <Nav />
      <main>
        <PageHeader eyebrow="Examples" title="Questions, worked all the way through.">
          <p>
            Each one starts with something you&rsquo;d actually wonder during a
            game and ends with an answer. Every command is runnable as written.
          </p>
        </PageHeader>

        <div className="mx-auto max-w-4xl px-5 py-14 sm:px-8 sm:py-20">
          <ul className="grid gap-6">
            {examples.map((example) => (
              <li key={example.slug}>
                <Link
                  href={`/examples/${example.slug}`}
                  className="group block rounded-xl border border-ink/12 bg-paper p-7 transition hover:border-grass-500/60 hover:bg-grass-50/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700 sm:p-8"
                >
                  <h2 className="text-xl font-semibold text-ink sm:text-2xl">
                    {example.title}
                  </h2>
                  <p className="mt-3 leading-relaxed text-muted">
                    {example.summary}
                  </p>
                  <span className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-grass-700">
                    Read the walkthrough
                    <ArrowIcon className="size-4 transition group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          <p className="mt-10 text-sm leading-relaxed text-muted">
            Got a question you&rsquo;d want worked through this way?{" "}
            <a
              href={`${site.repo}/issues/new`}
              className="text-grass-700 underline decoration-grass-700/30 underline-offset-4 transition hover:decoration-grass-700"
            >
              Open an issue
            </a>{" "}
            and it may end up here.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
