# pylint: skip-file
"""
Config script for the sphinx doc.
Author: Martin Altenburger
"""
import os
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath("../../.."))
from sphinx.util import logging
# Recommended logger for Sphinx config/extensions
logger = logging.getLogger(__name__)
# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = 'EnCoDaPy'
copyright = '2025, GEWV TU Dresden'
author = 'Martin Altenburger'
# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.autodoc_pydantic",
    "myst_parser",
]
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "filip": ("https://rwth-ebc.github.io/FiLiP/master/docs/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}
exclude_patterns = []
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = 'sphinx_rtd_theme'
# GitHub "Edit on GitHub" Link
html_context = {
    "display_github": True,
    "github_user": "gewv-tu-dresden",
    "github_repo": "encodapy",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}
# Optional: Direct edit links in theme
html_theme_options = {
    "vcs_pageview_mode": "blob",
}
# Static files (custom CSS)
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]
# Cross-Referencing for local class
autodoc_typehints_format = "short"
typehints_use_rtype = True
typehints_document_rtype = True
# Settings for type hints: output types in the description (clear fields)
autodoc_typehints = "both"  # alternative: "signature", "both"
# if you want to avoid fully qualified type names:
typehints_fully_qualified = False
always_document_param_types = False  # No automatic parameter documentation
typehints_defaults = "comma"
simplify_optional_unions = False
typehints_use_signature = True
typehints_use_signature_return = True
# Napoleon settings - hide parameters from docstrings
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_param = False  # Hides :param: sections
napoleon_use_keyword = False  # Hides :keyword: sections
napoleon_use_rtype = True  # Keeps :rtype:
napoleon_use_ivar = True  # Keeps instance variables
napoleon_preprocess_types = True
# pydantic-specific settings - for automodule
autodoc_pydantic_model_show_json = True
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_settings_show_field_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_validator_summary = False
# Hide the automatically generated parameter lists for Pydantic models
autodoc_pydantic_model_hide_paramlist = True # Shows Parameters
# Order of listed members for Pydantic objects: by source code
# Possible: "groupwise" (default), "bysource", "alphabetical"
# Set to "bysource" so that the documentation reflects the order in the code.
autodoc_pydantic_model_member_order = "bysource"
autodoc_pydantic_settings_member_order = "bysource"
# Import of myst-parser settings / for markdown support
myst_config = {
    "enable_extensions": [
        "colon_fence",
        "deflist",
        "substitution",
        "tasklist",
        "attrs_block",
        "attrs_inline",
        "replacements",
        "include",
    ],
    "heading_anchors": 3,
}
# Prevent display of docstrings
def suppress_module_docstring(app, what, name, obj, options, lines):
    """Removes all module docstrings from the output."""
    if what == "module":
        lines[:] = []
def suppress_pydantic_parameters(app, what, name, obj, options, lines):
    """Removes parameter sections from Pydantic models."""
    if what == "class" and hasattr(obj, '__pydantic_core_schema__'):
        # Remove parameter-related lines from the docstring
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() == "Parameters" or line.strip().startswith("Parameters:"):
                # Skip this line and the following parameters
                i += 1
                while i < len(lines) and (
                    lines[i].strip() == "" or
                    lines[i].startswith("    ") or
                    lines[i].startswith("\t") or
                    not lines[i].strip().endswith(":")
                ):
                    i += 1
                continue
            else:
                new_lines.append(line)
                i += 1
        lines[:] = new_lines
def _generate_readme(app):
    readmes: dict(str, str)= {
        "README.md": "README_FOR_DOCS.md",
        "encodapy/components/readme.md": "COMPONENTS_README_FOR_DOCS.md",
        "encodapy/components/thermal_storage/readme.md": "COMPONENT_Thermal_Storage_README_FOR_DOCS.md",
        "encodapy/components/two_point_controller/readme.md": "COMPONENT_Two_Point_Controller_README_FOR_DOCS.md",
        "examples/readme.md": "COMPONENT_Examples_README_FOR_DOCS.md"
    }
    # script is under docs/scripts relative to repo root
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "docs" / "scripts" / "generate_readme_for_docs.py"
    print("Generating README for docs using script:", str(script))
    if not script.exists():
        # if the script is missing: only log, do not crash
        logger.warning("README generator script not found: %s", str(script))
        return
    # read repo info from html_context (set above in this file)
    owner = html_context.get("github_user") or html_context.get("github_org") or ""
    repo = html_context.get("github_repo") or ""
    branch = html_context.get("github_version") or html_context.get("github_branch") or "main"
    repo_root = Path(__file__).resolve().parents[2]  # docs/source -> repo_root
    for readme_src, output_name in readmes.items():
        cmd = [sys.executable, str(script), "--owner", owner, "--repo", repo, "--branch", branch,
               "--repo_root", str(repo_root),
               "--readme-src", readme_src,
               "--output_name", output_name]
        try:
            subprocess.check_call(cmd, cwd=str(repo_root))
            logger.info("README generator finished: %s", str(script))
        except subprocess.CalledProcessError as exc:
            logger.warning("README generator failed (non-zero exit): %s", exc)
# Environment variable to indicate that docs are being built
os.environ["BUILDING_DOCS"] = "1"
def setup(app):
    app.connect("builder-inited", _generate_readme)
    app.connect("autodoc-process-docstring", suppress_module_docstring)
