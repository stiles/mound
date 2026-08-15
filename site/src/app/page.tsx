import Image from "next/image";
import { CopyCommand } from "@/components/copy-command";
import { Footer } from "@/components/footer";
import { ArrowIcon, GitHubIcon } from "@/components/icons";
import { Nav } from "@/components/nav";
import { RotatingHeadline } from "@/components/rotating-headline";
import { Terminal } from "@/components/terminal";
import {
  arsenal,
  features,
  heroCommand,
  heroOutput,
  plots,
  questions,
  splitPlot,
} from "@/lib/content";
import { site } from "@/lib/site";

const headlineVerbs = ["Find", "Analyze", "Plot", "Understand"] as const;

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Questions />
        <Features />
        <Arsenal />
        <Plots />
        <GetStarted />
      </main>
      <Footer />
    </>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-ink/10">
      <div
        aria-hidden="true"
        className="zone-grid pointer-events-none absolute inset-0 text-ink [mask-image:linear-gradient(to_bottom,black,transparent_78%)]"
      />

      <div className="relative mx-auto max-w-6xl px-5 pt-20 pb-16 sm:px-8 sm:pt-28 sm:pb-20">

        <h1 className="mt-6 max-w-4xl text-display font-semibold">
          <RotatingHeadline verbs={headlineVerbs} tail="every pitch." />
        </h1>

        <p className="mt-7 max-w-2xl text-lg leading-relaxed text-muted sm:text-xl">
          Mound retrieves, analyzes and visualizes MLB pitch-level data from the
          command line or a few lines of Python. Start from a player&rsquo;s
          name. No MLB IDs to look up, no undocumented APIs to learn.
        </p>

        <div className="mt-9 flex flex-col gap-4 sm:flex-row sm:items-center">
          <CopyCommand command="pip install mound" className="sm:min-w-80" />
          <div className="flex items-center gap-3">
            <a
              href={site.docs}
              className="inline-flex items-center gap-2 rounded-lg bg-grass-700 px-5 py-3 text-sm font-medium text-chalk transition hover:bg-grass-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700"
            >
              Read the docs
              <ArrowIcon className="size-4" />
            </a>
            <a
              href={site.repo}
              className="inline-flex items-center gap-2 rounded-lg border border-ink/15 px-5 py-3 text-sm font-medium text-ink transition hover:border-ink/30 hover:bg-paper focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700"
            >
              <GitHubIcon className="size-4" />
              GitHub
            </a>
          </div>
        </div>

        <div className="mt-16">
          <Terminal command={heroCommand} output={heroOutput} />
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted">
            One start, one table. The four-seamer lives in the zone and gets
            missed when hitters swing at it; the splitter&rsquo;s whole job is
            to be chased below it, and it was, 57.9% of the time.
          </p>
        </div>
      </div>
    </section>
  );
}

function Questions() {
  return (
    <section className="relative overflow-hidden bg-grass-900 text-chalk">
      <div
        aria-hidden="true"
        className="zone-grid pointer-events-none absolute inset-0 text-chalk opacity-70"
      />

      <div className="relative mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
        <h2 className="max-w-3xl text-section font-semibold text-balance">
          Find answers to questions about a pitcher&rsquo;s arsenal.
        </h2>

        <ul className="mt-12 divide-y divide-white/12 border-y border-white/12">
          {questions.map((question, index) => (
            <li key={question} className="flex gap-5 py-6 sm:gap-8">
              <span className="mt-1 shrink-0 font-mono text-sm text-grass-300 tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="text-lg leading-snug font-medium text-balance sm:text-2xl">
                {question}
              </p>
            </li>
          ))}
        </ul>

        <p className="mt-10 max-w-2xl text-base leading-relaxed text-chalk/65">
          Mound answers all four with a few CLI commands or a few lines of
          Python, and it never asks you for an MLB player ID to get there.
        </p>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
      <h2 className="max-w-2xl text-section font-semibold text-balance">
        A small surface, pointed at one job.
      </h2>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
        Eight commands and one Python object, sharing the same implementation
        underneath. Anything you can do in the shell, you can also do in a script.
      </p>

      <div className="mt-14 grid gap-px overflow-hidden rounded-xl border border-ink/12 bg-ink/12 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((feature) => (
          <div key={feature.title} className="bg-paper-warm p-6 lg:p-7">
            <code className="font-mono text-xs text-grass-700">
              {feature.code}
            </code>
            <h3 className="mt-3 text-base font-semibold text-ink">
              {feature.title}
            </h3>
            <p className="mt-2.5 text-sm leading-relaxed text-muted">
              {feature.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Arsenal() {
  return (
    <section className="border-y border-ink/10 bg-paper">
      <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
        <div className="grid gap-14 lg:grid-cols-[1.55fr_1fr] lg:gap-20">
          <div>
            <h2 className="text-section font-semibold text-balance">
              Three angles on &ldquo;how nasty was it?&rdquo;
            </h2>

            <div className="mt-10 overflow-x-auto">
              <table className="w-full min-w-lg border-collapse text-sm">
                <caption className="mb-4 text-left font-mono text-xs tracking-widest text-muted uppercase">
                  {arsenal.caption}
                </caption>
                <thead>
                  <tr className="border-b border-ink/20 text-left">
                    <th className="pb-3 font-medium text-muted">Pitch</th>
                    <th className="pb-3 text-right font-medium text-muted">
                      No.
                    </th>
                    <th className="pb-3 text-right font-medium text-muted">
                      Velo
                    </th>
                    <th className="pb-3 text-right font-medium text-muted">
                      Spin
                    </th>
                    <th className="pb-3 text-right font-medium text-muted">
                      Whiff
                    </th>
                    <th className="pb-3 text-right font-medium text-muted">
                      Chase
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/8">
                  {arsenal.rows.map((row) => (
                    <tr key={row.pitch}>
                      <td className="py-3.5">
                        <span className="flex items-center gap-2.5">
                          <span
                            className="size-2.5 shrink-0 rounded-full"
                            style={{ backgroundColor: row.color }}
                          />
                          <span className="font-medium text-ink">
                            {row.pitch}
                          </span>
                        </span>
                      </td>
                      <td className="py-3.5 text-right font-mono tabular-nums text-ink">
                        {row.pitches}
                      </td>
                      <td className="py-3.5 text-right font-mono tabular-nums text-ink">
                        {row.velocity.toFixed(1)}
                      </td>
                      <td className="py-3.5 text-right font-mono tabular-nums text-muted">
                        {row.spin.toFixed(1)}
                      </td>
                      <td className="py-3.5 text-right font-mono tabular-nums text-ink">
                        {row.whiff.toFixed(1)}%
                      </td>
                      <td className="py-3.5 text-right font-mono tabular-nums text-ink">
                        {row.chase.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="lg:pt-4">
            <dl className="space-y-7 border-l-2 border-seam pl-6">
              <div>
                <dt className="font-semibold text-ink">Swing rate</dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-muted">
                  Swings over every pitch thrown. How often hitters were
                  tempted at all.
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-ink">Whiff rate</dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-muted">
                  Swings that missed, over swings — Baseball Savant&rsquo;s own
                  convention, not misses over every pitch. A pitch rarely swung
                  at can still post a high number.
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-ink">Chase rate</dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-muted">
                  Swings over pitches outside the zone. Read from location
                  geometry rather than the strike ruling, because those are
                  genuinely different things.
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </section>
  );
}

function Plots() {
  return (
    <section className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
      <h2 className="max-w-2xl text-section font-semibold text-balance">
        Charts that arrive finished.
      </h2>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
        A headline, a dek and a source line render around the strike zone
        itself, so a plot is publishable the moment it comes out of the
        function. All three are generated for you and all three are
        overridable.
      </p>

      <div className="mt-14 grid gap-8 sm:grid-cols-2">
        {plots.map((plot) => (
          <figure
            key={plot.src}
            className="overflow-hidden rounded-xl border border-ink/12 bg-paper"
          >
            <Image
              src={plot.src}
              width={plot.width}
              height={plot.height}
              alt={plot.alt}
              sizes="(min-width: 640px) 45vw, 90vw"
              className="h-auto w-full"
            />
            <figcaption className="border-t border-ink/10 px-6 py-5">
              <code className="font-mono text-xs text-grass-700">
                {plot.label}
              </code>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {plot.caption}
              </p>
            </figcaption>
          </figure>
        ))}
      </div>

      <figure className="mt-8 overflow-hidden rounded-xl border border-ink/12 bg-paper">
        <Image
          src={splitPlot.src}
          width={splitPlot.width}
          height={splitPlot.height}
          alt={splitPlot.alt}
          sizes="(min-width: 1152px) 1088px, 92vw"
          className="h-auto w-full"
        />
        <figcaption className="border-t border-ink/10 px-6 py-5">
          <code className="font-mono text-xs text-grass-700">
            {splitPlot.label}
          </code>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
            {splitPlot.caption}
          </p>
        </figcaption>
      </figure>
    </section>
  );
}

function GetStarted() {
  return (
    <section className="border-t border-ink/10 bg-grass-50">
      <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
        <div className="grid gap-12 lg:grid-cols-[1fr_1fr] lg:gap-20">
          <div>
            <h2 className="text-section font-semibold text-balance">
              Two minutes to your first pitch.
            </h2>
            <p className="mt-5 text-lg leading-relaxed text-grass-900/70">
              Install it, point it at a name and start asking. The worked
              example goes all the way from a pitcher&rsquo;s postgame quote to
              the video of the pitches that disproved it.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <a
                href={site.examples}
                className="inline-flex items-center gap-2 rounded-lg bg-grass-700 px-5 py-3 text-sm font-medium text-chalk transition hover:bg-grass-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700"
              >
                Read the walkthrough
                <ArrowIcon className="size-4" />
              </a>
              <a
                href={site.pypi}
                className="inline-flex items-center gap-2 rounded-lg border border-grass-900/20 px-5 py-3 text-sm font-medium text-grass-900 transition hover:border-grass-900/40 hover:bg-chalk/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-grass-700"
              >
                View on PyPI
              </a>
            </div>
          </div>

          <div className="space-y-3">
            <CopyCommand command="pip install mound" />
            <CopyCommand command='mound search "Roki Sasaki"' />
            <CopyCommand command='mound arsenal "Roki Sasaki" --last 4' />
            <p className="pt-3 text-sm leading-relaxed text-grass-900/60">
              Add{" "}
              <code className="font-mono text-grass-800">
                pip install &quot;mound[viz]&quot;
              </code>{" "}
              for KDE heatmaps, or{" "}
              <code className="font-mono text-grass-800">
                &quot;mound[parquet]&quot;
              </code>{" "}
              for Parquet export.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
