import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const CONTENT = join(process.cwd(), "content");

export type Release = {
  version: string;
  date: string;
  body: string;
};

export type Example = {
  slug: string;
  title: string;
  summary: string;
  body: string;
};

const RELEASE_HEADING = /^##\s+\[([^\]]+)\]\s*[-–]\s*(.+?)\s*$/;

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  if (!year || !month || !day) return iso;
  const name = new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
  return name;
}

/** Splits CHANGELOG.md on its `## [version] - date` headings. Anything above
 *  the first one is the file's own preamble, which the page supplies itself. */
export async function getReleases(): Promise<Release[]> {
  const source = await readFile(join(CONTENT, "changelog.md"), "utf8");
  const lines = source.split("\n");

  const heads: { line: number; version: string; date: string }[] = [];
  lines.forEach((line, index) => {
    const match = RELEASE_HEADING.exec(line);
    if (match) heads.push({ line: index, version: match[1], date: match[2] });
  });

  return heads.map((head, index) => {
    const end = index + 1 < heads.length ? heads[index + 1].line : lines.length;
    return {
      version: head.version,
      date: head.date,
      body: lines.slice(head.line + 1, end).join("\n").trim(),
    };
  });
}

/** Titles and summaries are pulled out as plain strings so they can serve as
 *  page metadata, which means they skip the markdown pipeline's typography.
 *  This applies the same quote and dash conventions to that handful of text. */
function smarten(text: string): string {
  return text
    .replace(/(^|[\s([{])"/g, "$1\u201c")
    .replace(/"/g, "\u201d")
    .replace(/(^|[\s([{])'/g, "$1\u2018")
    .replace(/'/g, "\u2019")
    .replace(/ -- /g, " \u2014 ");
}

function parseExample(slug: string, source: string): Example {
  const lines = source.split("\n");
  const titleIndex = lines.findIndex((line) => line.startsWith("# "));
  const title = titleIndex >= 0 ? lines[titleIndex].replace(/^#\s+/, "").trim() : slug;

  const rest = lines.slice(titleIndex + 1);
  const summaryIndex = rest.findIndex((line) => line.trim().length > 0);
  const summary = summaryIndex >= 0 ? rest[summaryIndex].trim() : "";

  return {
    slug,
    title: smarten(title),
    summary: smarten(summary),
    // The page renders its own title and standfirst, so drop them from the body.
    body: rest.slice(summaryIndex + 1).join("\n").trim(),
  };
}

export async function getExamples(): Promise<Example[]> {
  const names = (await readdir(join(CONTENT, "examples")))
    .filter((name) => name.endsWith(".md"))
    .sort();

  return Promise.all(
    names.map(async (name) => {
      const slug = name.replace(/\.md$/, "");
      const source = await readFile(join(CONTENT, "examples", name), "utf8");
      return parseExample(slug, source);
    }),
  );
}

export async function getExample(slug: string): Promise<Example | null> {
  const examples = await getExamples();
  return examples.find((example) => example.slug === slug) ?? null;
}
