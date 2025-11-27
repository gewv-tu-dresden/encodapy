# Build files for the documentation.

The documentation is built using Sphinx and the Poetry environment. You can use:
```
poetry run sphinx-build -b html -a -E ./source ./build 
```
to build the documentation locally.
The [GitHub workflow](./../.github/workflows/docs.yml) is used for automated documentation.