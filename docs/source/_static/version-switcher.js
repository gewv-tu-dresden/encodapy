(function () {
  function normalizeBaseUrl(baseUrl) {
    if (!baseUrl) {
      return "/";
    }
    return baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  }

  function createOption(label, target, selected) {
    return { label, target, selected: Boolean(selected) };
  }

  async function fetchManifest(baseUrl) {
    const normalized = normalizeBaseUrl(baseUrl);
    const manifestUrl = new URL(`${normalized}versions.json`, window.location.origin).toString();
    try {
      const response = await fetch(manifestUrl, { cache: "no-store" });
      if (!response.ok) {
        return null;
      }
      return response.json();
    } catch (err) {
      return null;   // local dev server may not have the manifest, so we just return null
    }
}


  function getPathSegment(baseUrl) {
    const basePath = new URL(baseUrl, window.location.origin).pathname;
    const currentPath = window.location.pathname;
    const relativePath = currentPath.startsWith(basePath)
      ? currentPath.slice(basePath.length)
      : currentPath.replace(/^\//, "");
    const parts = relativePath.split("/").filter(Boolean);
    return parts[0] || "";
  }

  function buildOptions(config, manifest) {
    const baseUrl = normalizeBaseUrl(config.baseUrl);
    const currentVersion = config.currentVersion || "main";
    const pathSegment = getPathSegment(baseUrl);
    const currentFromPath = pathSegment || (currentVersion === "main" ? "main" : currentVersion);
    const options = [];
    const versions = Array.isArray(manifest?.versions) ? manifest.versions : [];
    const latest = manifest?.latest || "";

    options.push(createOption("Main", `${baseUrl}main/`, currentFromPath === "main"));
    if (latest) {
      options.push(createOption(`Latest release (${latest})`, baseUrl, currentFromPath === ""));
    } else {
      options.push(createOption("Latest release", baseUrl, currentFromPath === ""));
    }

    versions.forEach((version) => {
      options.push(createOption(version, `${baseUrl}${version}/`, currentFromPath === version));
    });

    return options;
  }

  async function insertSwitcher() {
    const config = window.ENCODAPY_DOCS;
    if (!config) {
      return;
    }

    const search = document.querySelector(".wy-side-nav-search");
    if (!search) {
      return;
    }

    const container = document.createElement("div");
    container.className = "encodapy-version-switcher";

    const label = document.createElement("label");
    label.className = "encodapy-version-switcher__label";
    label.textContent = "Documentation version";

    const select = document.createElement("select");
    select.className = "encodapy-version-switcher__select";

    const manifest = await fetchManifest(config.baseUrl).catch(() => null);
    const options = buildOptions(config, manifest);
    options.forEach((option) => {
      const element = document.createElement("option");
      element.value = option.target;
      element.textContent = option.label;
      element.selected = option.selected;
      select.appendChild(element);
    });

    select.addEventListener("change", (event) => {
      const target = event.target.value;
      if (target) {
        window.location.href = target;
      }
    });

    const hint = document.createElement("span");
    hint.className = "encodapy-version-switcher__hint";
    hint.textContent = "Switch between the main build and published release versions.";

    container.appendChild(label);
    container.appendChild(select);
    container.appendChild(hint);
    search.insertAdjacentElement("afterend", container);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", insertSwitcher);
  } else {
    insertSwitcher();
  }
}());
