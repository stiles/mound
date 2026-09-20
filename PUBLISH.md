# Publishing

A release is one command, `./scripts/publish.sh`, and one thing to understand:
the script does not upload to PyPI. It creates a GitHub release, and
`.github/workflows/publish.yml` uploads when that release is published.

Keeping the upload in one place is the point. Doing it locally *and* from the
release means the workflow finds the files already on PyPI and fails with
"400 File already exists" after the package has gone out — a red check on a
release that actually worked.

## Where the version lives

`mound/__init__.py`, in `__version__`, and nowhere else. `pyproject.toml`
declares `dynamic = ["version"]` and hatchling reads the literal from there, so
it never needs editing. Two hand-maintained copies drift, and the drift only
shows up after the version number is spent.

## Running the script

```bash
./scripts/publish.sh
```

It stops at any answer that isn't yes:

1. Asks for the bump — patch, minor, major, custom or none — and refuses a
   version whose tag already exists.
2. Warns if the working directory is dirty.
3. Rewrites `__version__` and adds a dated `## [X.Y.Z]` heading to
   `CHANGELOG.md` under `[Unreleased]`. It warns if that section is empty,
   because the release notes are pulled from it verbatim.
4. Asks you to confirm the changelog and the docs.
5. Runs `ruff check .` and `pytest`. A failure aborts the release.
6. Checks that `build` and `gh` are installed.
7. Commits `chore(release): vX.Y.Z`, pushes `main`, then tags and pushes
   `vX.Y.Z`.
8. Builds a clean `dist/`.
9. Offers to create the GitHub release, with notes read out of the changelog
   section for that version and the built files attached. **Say yes.** This is
   the step that publishes to PyPI. Skip it and the tag is pushed but nothing
   ships.

Then watch the upload:

```bash
gh run watch $(gh run list --workflow="Publish to PyPI" --limit 1 --json databaseId -q '.[0].databaseId')
```

The workflow builds its own copy rather than trusting the attached files, and
refuses to upload if the built version doesn't match the tag.

## Prerequisites

```bash
pip install -e ".[dev]"
brew install gh   # or https://cli.github.com/
```

`npm` too, if you want the release commit to carry a synced `site/content/changelog.md` -- the script re-runs `npm run sync` itself when it edits `CHANGELOG.md`, and warns and skips it if `npm` isn't on `PATH`. The Site CI check re-runs the same sync and fails the build on any diff, so a release cut without it leaves that workflow red on a commit that otherwise did nothing wrong.

The PyPI token is a repository secret named `PYPI_API_TOKEN`, held in GitHub
rather than in your shell:

```bash
gh secret set PYPI_API_TOKEN   # paste a project-scoped token from pypi.org
```

There is no local `PYPI` or `PYPI_TEST` variable to set, and no reason to hold
a token locally at all.

## Version numbering

Semver, and mound is pre-1.0:

- **Patch** (0.13.1): bug fixes that don't change what callers pass or get back.
- **Minor** (0.14.0): new features, new arguments, changed output. Also the
  right call for a raised Python floor, a new dependency or a `Pitch` field
  that can now be null — anything a user can feel.
- **Major** (1.0.0): reserved for declaring the API settled.

## If something goes wrong

The tag and the GitHub release can both be removed:

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
gh release delete vX.Y.Z
```

A PyPI release can't be deleted and can't be replaced: that version number is
spent even if you yank it. Yanking hides it from resolvers while leaving it
installable by exact pin, and it's done from the project page on PyPI under
Manage, not from the command line. The fix for a bad release is a new patch
version.

## Doing it by hand

Only if the script is broken, and mind the one rule — tag locally, but let the
release do the uploading.

```bash
# 1. Bump __version__ in mound/__init__.py, move [Unreleased] in CHANGELOG.md
git add mound/__init__.py CHANGELOG.md
git commit -m "chore(release): vX.Y.Z"
git push origin main
git tag vX.Y.Z && git push origin vX.Y.Z

# 2. Build and check
rm -rf build dist ./*.egg-info && python -m build && python -m twine check dist/*

# 3. Release, which triggers the PyPI upload
gh release create vX.Y.Z dist/* --title "vX.Y.Z" --notes "..."
```

## After a release

- `pip install --no-cache-dir --upgrade mound` and check `mound --version`
  reports the number you just shipped.
- Check the [PyPI page](https://pypi.org/project/mound/) rendered the README.
- The site at [moundcli.com](https://moundcli.com) builds from `main` on its own.
