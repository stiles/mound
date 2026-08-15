# moundcli.com

The landing page and documentation site for [Mound](https://github.com/stiles/mound). Next.js App Router, Tailwind v4, deployed on Vercel.

```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

## Vercel

Set the project's **root directory** to `site/`. Everything the build needs currently lives inside it, so the "include files outside the root directory" setting can stay off.

That changes in phase 3, when the changelog and examples routes start reading `../CHANGELOG.md` and `../docs/examples/`. A prebuild script will copy those in rather than relying on the Vercel setting, so the build behaves the same locally and in CI.

## Design

Ink, paper, muted, line and the pitch-type colors in `src/app/globals.css` are copied from `mound/viz.py`, so a chart screenshot and the page around it use the same palette. The grass ramp is the only color the site adds. Keep them in sync if the library's palette moves.

Every command and number rendered on the page comes from the repo's README or `docs/examples/`, collected in `src/lib/content.ts`. Nothing there is illustrative — if a number changes upstream, change it there too.

The full plan, including the phases still ahead, is in `.cursor/docs/site-plan.md`.
