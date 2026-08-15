#!/usr/bin/env node
/**
 * Copies the repo's canonical docs into the site so the changelog and
 * examples pages render from the same files the package ships.
 *
 * The copies are committed rather than generated during the Vercel build.
 * That keeps everything the build touches inside site/, so the deploy never
 * depends on reaching above its root directory. CI re-runs this and fails on
 * any diff, which is what actually prevents drift.
 *
 *   npm run sync
 */
import { access, mkdir, readdir, copyFile, rm } from "node:fs/promises";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(siteRoot, "..");

const CHANGELOG = { from: join(repoRoot, "CHANGELOG.md"), to: join(siteRoot, "content/changelog.md") };
const EXAMPLES = { from: join(repoRoot, "docs/examples"), to: join(siteRoot, "content/examples"), ext: ".md" };
const IMAGES = { from: join(repoRoot, "docs/images"), to: join(siteRoot, "public/docs-images"), ext: ".png" };

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function syncDirectory({ from, to, ext }) {
  if (!(await exists(from))) {
    throw new Error(`Missing source directory: ${from}`);
  }

  await rm(to, { recursive: true, force: true });
  await mkdir(to, { recursive: true });

  const names = (await readdir(from)).filter((name) => extname(name) === ext).sort();
  for (const name of names) {
    await copyFile(join(from, name), join(to, name));
  }
  return names.length;
}

async function main() {
  if (!(await exists(CHANGELOG.from))) {
    throw new Error(`Missing source file: ${CHANGELOG.from}`);
  }
  await mkdir(dirname(CHANGELOG.to), { recursive: true });
  await copyFile(CHANGELOG.from, CHANGELOG.to);

  const examples = await syncDirectory(EXAMPLES);
  const images = await syncDirectory(IMAGES);

  console.log(`synced changelog.md, ${examples} example(s), ${images} image(s)`);
}

main().catch((error) => {
  console.error(`sync-content failed: ${error.message}`);
  process.exit(1);
});
