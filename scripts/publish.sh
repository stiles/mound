#!/usr/bin/env bash
#
# Cuts a mound release: bumps the version, updates the changelog, runs the
# checks, tags, and creates the GitHub release.
#
# It does not upload to PyPI. .github/workflows/publish.yml does that when the
# release is published. Uploading from both places means the workflow finds the
# files already on PyPI and fails with "400 File already exists".

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Everything runs through the project's own environment. A bare `pytest` picks
# up whichever interpreter is first on PATH -- a pyenv shim, usually -- and the
# release checks then pass or fail on a environment the package isn't developed
# in.
if command -v uv >/dev/null 2>&1; then
  PY=(uv run --extra dev python)
else
  PY=(python3)
fi

echo "Starting the mound release process..."
echo "========================================"

# --- 1. Version ---
echo "--- Version ---"

# One literal, in mound/__init__.py. pyproject.toml reads it from there via
# hatchling's dynamic version, so it never needs editing.
CURRENT_VERSION="$(grep '^__version__' mound/__init__.py | sed 's/.*= *//' | tr -d "\"'" | xargs)"

if [[ -z "${CURRENT_VERSION}" ]]; then
  echo "Error: could not find __version__ in mound/__init__.py" >&2
  exit 1
fi

echo "Current version: ${CURRENT_VERSION}"
echo
echo "What kind of bump?"
select bump_type in "patch" "minor" "major" "custom" "no change"; do
  case "${bump_type:-}" in
    patch|minor|major)
      NEW_VERSION="$(python3 - "$CURRENT_VERSION" "$bump_type" <<'PY'
import sys

version, kind = sys.argv[1], sys.argv[2]
major, minor, patch = (int(part) for part in version.split("."))
if kind == "patch":
    patch += 1
elif kind == "minor":
    minor, patch = minor + 1, 0
else:
    major, minor, patch = major + 1, 0, 0
print(f"{major}.{minor}.{patch}")
PY
)"
      break;;
    custom)
      read -r -p "New version: " NEW_VERSION
      break;;
    "no change")
      NEW_VERSION="$CURRENT_VERSION"
      break;;
    *) echo "Pick 1-5.";;
  esac
done

TAG="v${NEW_VERSION}"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: tag ${TAG} already exists. That version is spent; pick another." >&2
  exit 1
fi

echo "Releasing ${NEW_VERSION}"

# --- 2. Git status ---
echo "--- Git status ---"
if ! git diff-index --quiet HEAD --; then
  echo "Warning: uncommitted changes."
  git status --porcelain
  read -r -p "Continue anyway? (y/n) " -n 1 -r; echo
  [[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled. Commit first."; exit 1; }
fi

# --- 3. Version and changelog ---
if [[ "$NEW_VERSION" != "$CURRENT_VERSION" ]]; then
  echo "--- Updating version and changelog ---"

  # Rewrite the line outright rather than matching the old version, so a file
  # that has drifted still lands on the right number.
  sed -i.bak "s/^__version__ = .*/__version__ = \"${NEW_VERSION}\"/" mound/__init__.py

  if grep -q "^## \[${NEW_VERSION}\]" CHANGELOG.md; then
    echo "CHANGELOG.md already has a [${NEW_VERSION}] heading; leaving it."
  else
    TODAY="$(date +%Y-%m-%d)"
    sed -i.bak "s/^## \[Unreleased\]/## [Unreleased]\n\n## [${NEW_VERSION}] - ${TODAY}/" CHANGELOG.md
  fi

  rm -f mound/__init__.py.bak CHANGELOG.md.bak
  echo "Version set to ${NEW_VERSION}"

  # The site's own CI re-runs this same sync and fails on any diff (Site
  # workflow, "Check synced content is current") -- which is exactly what a
  # bare version-bump commit tripped on every release: the sed above edits
  # CHANGELOG.md, but nothing told site/content/changelog.md. Syncing here,
  # before that commit, is what keeps the two copies in the commit that
  # touched either.
  if command -v npm >/dev/null 2>&1 && [[ -f site/package.json ]]; then
    (cd site && npm run sync)
  else
    echo "Warning: npm not found; skipping site content sync." >&2
    echo "Run 'npm run sync' in site/ by hand before pushing, or the Site CI check will fail." >&2
  fi
fi

# The release notes are read from this section verbatim. Empty means an empty
# release.
NOTES="$(awk '/^## \['"${NEW_VERSION}"'\]/{flag=1; next} /^## \[/{flag=0} flag' CHANGELOG.md)"
if [[ -z "$(echo "$NOTES" | tr -d '[:space:]')" ]]; then
  echo "Warning: no notes under [${NEW_VERSION}] in CHANGELOG.md. The release would be empty."
  read -r -p "Continue? (y/n) " -n 1 -r; echo
  [[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }
fi

# --- 4. Checklist ---
echo "--- Checklist ---"
read -r -p "Is CHANGELOG.md accurate? (y/n) " -n 1 -r; echo
[[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }
read -r -p "Are the README and docs current? (y/n) " -n 1 -r; echo
[[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }

# --- 5. Checks ---
echo "--- Running lint and tests ---"
"${PY[@]}" -m ruff check .
"${PY[@]}" -m pytest -q
echo "Checks passed."

# --- 6. Tools ---
command -v gh >/dev/null 2>&1 || {
  echo "Error: the GitHub CLI ('gh') is missing. Run: brew install gh" >&2
  exit 1
}

# --- 7. Confirm ---
echo "--- Ready ---"
echo "This will commit, push main, tag ${TAG}, and create a GitHub release."
echo "The release triggers the PyPI upload."
read -r -p "Go? (y/n) " -n 1 -r; echo
[[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 1; }

# --- 8. Commit, push, tag ---
echo "--- Git ---"
if [[ "$NEW_VERSION" != "$CURRENT_VERSION" ]]; then
  git add mound/__init__.py CHANGELOG.md site/content site/public/docs-images
  git commit -m "chore(release): ${TAG}"
fi

git push origin main
git tag "$TAG"
git push origin "$TAG"
echo "Pushed ${TAG}."

# --- 9. Build ---
# The files are attached to the GitHub release so the tag has the exact
# artifacts alongside it. The workflow builds its own copy to upload.
echo "--- Building ---"
rm -rf build dist ./*.egg-info
"${PY[@]}" -m build
ls -l dist

# --- 10. Release ---
echo "--- GitHub release ---"
echo "This is the step that publishes to PyPI. Skip it and the tag ships nothing."
read -r -p "Create the release for ${TAG}? (y/n) " -n 1 -r; echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  gh release create "$TAG" dist/* --title "$TAG" --notes "$NOTES"
  echo "Released: https://github.com/stiles/mound/releases/tag/${TAG}"
else
  echo "Skipped. Nothing will publish until you run:"
  echo "  gh release create ${TAG} dist/* --title \"${TAG}\" --notes-file <notes>"
  exit 0
fi

echo "========================================"
echo "Done. Version ${NEW_VERSION}, tag ${TAG}."
echo
echo "Watch the upload:"
echo "  gh run watch \$(gh run list --workflow='Publish to PyPI' --limit 1 --json databaseId -q '.[0].databaseId')"
echo "Then check it:"
echo "  pip install --no-cache-dir --upgrade mound && mound --version"
echo "========================================"
