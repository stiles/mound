import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";
import { PageHeader } from "@/components/page-header";
import { getExample, getExamples } from "@/lib/docs";
import { renderMarkdown } from "@/lib/markdown";
import { site } from "@/lib/site";

export async function generateStaticParams() {
  const examples = await getExamples();
  return examples.map((example) => ({ slug: example.slug }));
}

export async function generateMetadata({
  params,
}: PageProps<"/examples/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const example = await getExample(slug);
  if (!example) return {};

  return {
    title: example.title,
    description: example.summary,
    openGraph: { title: example.title, description: example.summary },
  };
}

export default async function ExamplePage({
  params,
}: PageProps<"/examples/[slug]">) {
  const { slug } = await params;
  const example = await getExample(slug);
  if (!example) notFound();

  const html = await renderMarkdown(example.body);

  return (
    <>
      <Nav />
      <main>
        <PageHeader
          eyebrow="← All examples"
          eyebrowHref="/examples"
          title={example.title}
        >
          <p>{example.summary}</p>
        </PageHeader>

        <article className="mx-auto max-w-4xl px-5 py-14 sm:px-8 sm:py-20">
          <div
            className="prose-mound prose max-w-none"
            dangerouslySetInnerHTML={{ __html: html }}
          />

          <div className="mt-16 rounded-xl border border-ink/12 bg-grass-50 p-7">
            <h2 className="font-semibold text-ink">Run it yourself</h2>
            <p className="mt-2 text-sm leading-relaxed text-grass-900/70">
              This walkthrough lives in the repo as{" "}
              <code className="font-mono">docs/examples/{example.slug}.md</code>
              , with a runnable companion script in{" "}
              <code className="font-mono">examples/</code>.
            </p>
            <a
              href={`${site.repo}/blob/main/docs/examples/${example.slug}.md`}
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
