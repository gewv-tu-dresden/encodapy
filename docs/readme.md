# Build files for the documentation

The documentation is built using Sphinx and the Poetry environment. You can use:

```shell
poetry run sphinx-build -b html -a -E ./source ./build
```

to build the documentation locally.
The [GitHub workflow](./../.github/workflows/docs.yml) is used for automated documentation.

The version switcher reads a `versions.json` manifest from the published documentation. On GitHub Pages, this manifest is updated by the release workflow so that the dropdown only shows versions that were actually published as docs.

## Check a release build locally

To verify how a release or tag build behaves without pushing anything, set the docs version explicitly before building:

```powershell
$env:DOCS_GITHUB_VERSION = "vx.x.x"
$env:DOCS_RELEASE_VERSION = "vx.x.x"
$env:DOCS_PUBLISHED_VERSIONS_URL = ""
poetry run sphinx-build -b html -a -E ./source ./build
poetry run python ./scripts/prepare_versioned_docs.py --build-dir ./build --release-version vx.x.x
```

Then open the generated `build/index.html` in your browser, or serve the folder locally:

```powershell
poetry run python -m http.server 8000 --directory ./build
```

This lets you inspect the generated links and confirm that GitHub edit links point to the expected tag instead of `main`.

If you want the version switcher paths to be available locally as well, prepare the version folders after the build:

```powershell
poetry run python ./scripts/prepare_versioned_docs.py --build-dir ./build --release-version vx.x.x
```

If you want the dropdown to include the same published history as GitHub Pages, point `DOCS_PUBLISHED_VERSIONS_URL` to a reachable `versions.json` from your deployed docs before building. For example:

```powershell
$env:DOCS_PUBLISHED_VERSIONS_URL = "https://gewv-tu-dresden.github.io/encodapy/versions.json"
poetry run sphinx-build -b html -a -E ./source ./build
poetry run python ./scripts/prepare_versioned_docs.py --build-dir ./build --release-version vx.x.x
```

Then open `http://localhost:8000/index.html` and use the English switcher in the lower-left corner.
