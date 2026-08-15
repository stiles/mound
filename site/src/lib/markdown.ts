import rehypeAutolinkHeadings from "rehype-autolink-headings";
import rehypePrettyCode from "rehype-pretty-code";
import rehypeSlug from "rehype-slug";
import rehypeStringify from "rehype-stringify";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import remarkSmartypants from "remark-smartypants";
import { unified } from "unified";
import { SKIP, visit } from "unist-util-visit";
import type { Element, Root } from "hast";
import { moundDark } from "@/lib/code-theme";
import { site } from "@/lib/site";

/**
 * The source files live in the repo and link to each other with relative
 * paths that only resolve on GitHub. Rewrite them for the web: images point
 * at the synced public directory, and links to files the site doesn't host
 * yet fall back to GitHub rather than 404.
 */
function rewriteRepoPaths() {
  return (tree: Root) => {
    visit(tree, "element", (node: Element) => {
      if (node.tagName === "img") {
        const src = node.properties?.src;
        if (typeof src === "string") {
          const name = src.split("/").pop();
          if (name && !src.startsWith("http")) {
            node.properties.src = `/docs-images/${name}`;
          }
        }
        node.properties.loading = "lazy";
        return;
      }

      if (node.tagName === "a") {
        const href = node.properties?.href;
        if (typeof href !== "string") return;

        if (href.startsWith("http") || href.startsWith("#") || href.startsWith("/")) {
          return;
        }

        // e.g. "../../README.md#caching" -> the README anchor on GitHub
        const [path, hash] = href.split("#");
        const file = path.replace(/^(\.\.\/)+/, "").replace(/^\.\//, "");
        const anchor = hash ? `#${hash}` : "";

        node.properties.href = file
          ? `${site.repo}/blob/main/${file}${anchor}`
          : anchor;
      }
    });
  };
}

/** A wide table in normal flow drags the whole page wider than a phone
 *  viewport, so each one gets its own scroll container. */
function wrapTables() {
  return (tree: Root) => {
    visit(tree, "element", (node: Element, index, parent) => {
      if (node.tagName !== "table" || !parent || index === undefined) return;

      const wrapper: Element = {
        type: "element",
        tagName: "div",
        properties: { className: ["table-scroll"] },
        children: [node],
      };
      parent.children[index] = wrapper;

      return [SKIP, index + 1];
    });
  };
}

const processor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  // Curly quotes and real dashes. Safe because it skips code, and every CLI
  // flag in the source markdown is written inside backticks — a bare
  // `--flag` in running prose would come out as an en dash.
  .use(remarkSmartypants)
  .use(remarkRehype)
  .use(rewriteRepoPaths)
  .use(wrapTables)
  .use(rehypeSlug)
  .use(rehypeAutolinkHeadings, {
    behavior: "wrap",
    properties: { className: ["heading-anchor"] },
  })
  .use(rehypePrettyCode, {
    theme: moundDark,
    keepBackground: true,
    // Block only. A bare string would also highlight every inline `code`
    // span, which paints the dark editor background onto running prose.
    defaultLang: { block: "text" },
  })
  .use(rehypeStringify);

export async function renderMarkdown(source: string): Promise<string> {
  const file = await processor.process(source);
  return String(file);
}
