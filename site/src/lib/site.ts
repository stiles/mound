export const site = {
  name: "Mound",
  url: "https://moundcli.com",
  tagline: "Pitch-level baseball data, without the scavenger hunt.",
  description:
    "A CLI and Python toolkit for retrieving, analyzing and visualizing MLB pitch-level data — without needing to know MLB player IDs or the underlying API structures.",
  repo: "https://github.com/stiles/mound",
  pypi: "https://pypi.org/project/mound/",
  docs: "https://github.com/stiles/mound#readme",
  examples: "/examples",
  changelog: "/changelog",
  author: "Matt Stiles",
  // Public by nature — it ships in the page source — so it lives with the
  // rest of the site config rather than in an env var that can go missing.
  analyticsId: "G-XS9802RWM6",
} as const;
