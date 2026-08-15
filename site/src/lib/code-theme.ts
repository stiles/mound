import type { ThemeRegistrationRaw } from "shiki";

const tokens = [
  { settings: { foreground: "#EAF6EF", background: "#0F3D2A" } },
  {
    scope: ["comment", "punctuation.definition.comment"],
    settings: { foreground: "#6E9B84", fontStyle: "italic" },
  },
  {
    scope: ["string", "string.quoted", "meta.string"],
    settings: { foreground: "#7FD3A8" },
  },
  {
    scope: ["keyword", "storage.type", "storage.modifier", "keyword.control"],
    settings: { foreground: "#F18851" },
  },
  {
    scope: ["entity.name.function", "support.function", "meta.function-call"],
    settings: { foreground: "#5194C3" },
  },
  {
    scope: ["constant.numeric", "constant.language", "constant.character"],
    settings: { foreground: "#F0A15C" },
  },
  {
    scope: ["variable.parameter", "entity.name.tag", "support.type"],
    settings: { foreground: "#9BC7E4" },
  },
  {
    scope: ["entity.name.class", "support.class", "entity.name.type"],
    settings: { foreground: "#C9A9E0" },
  },
  {
    scope: ["punctuation", "meta.brace", "keyword.operator"],
    settings: { foreground: "#A9C9B8" },
  },
];

/**
 * Built from the same palette as the library's plots, so a code block and a
 * chart on the same page read as one family rather than two vendors.
 *
 * The token list is assigned to both keys deliberately. Shiki reads
 * `settings` and its type requires it, while rehype-pretty-code decides
 * whether an object is a single theme or a map of themes by testing for
 * `tokenColors`. Supplying only one of the two fails in one place or the
 * other.
 */
export const moundDark: ThemeRegistrationRaw = {
  name: "mound-dark",
  type: "dark",
  colors: {
    "editor.background": "#0F3D2A",
    "editor.foreground": "#EAF6EF",
  },
  settings: tokens,
  tokenColors: tokens,
};
