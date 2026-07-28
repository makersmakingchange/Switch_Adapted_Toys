# Toy Instructions

Browse switch-adapted toy builds. Use the filters below to narrow down by category, or scroll through everything.

!!! note "Information be outdated"
    This resource is where Makers Making Change hosts all of our toy instructions both current and past. This means, some of the toys that you find instructions for may not be available at the moment OR information may be out of date.


<div id="toy-app">
  <input type="text" id="toy-search" class="toy-search" placeholder="Search toys by name..." oninput="handleToySearch(this.value)">
  
  <!-- Grouped, clean filter panel -->
  <details class="filter-dropdown-container">
    <summary class="filter-toggle-summary">🔍 Filter Options (Click to expand)</summary>
    <div class="advanced-filters-grid">
      <div class="filter-group">
        <h4>Tags / Categories</h4>
        <div class="filter-bar" id="filter-bar-tags"></div>
      </div>
      <div class="filter-group">
        <h4>Build Style</h4>
        <div class="filter-bar" id="filter-bar-build"></div>
      </div>
      <div class="filter-group">
        <h4>Battery Type</h4>
        <div class="filter-bar" id="filter-bar-battery"></div>
      </div>
      <div class="filter-group">
        <h4>Connection Method</h4>
        <div class="filter-bar" id="filter-bar-method"></div>
      </div>
      <div class="filter-group">
        <h4>Activation Type</h4>
        <div class="filter-bar" id="filter-bar-activation"></div>
      </div>
      <div class="filter-group">
        <h4>3D Printed Parts</h4>
        <div class="filter-bar" id="filter-bar-3d"></div>
      </div>
      <div class="filter-group">
        <h4>Availability</h4>
        <div class="filter-bar" id="filter-bar-availability"></div>
      </div>
    </div>
  </details>

  <button class="clear-btn" onclick="clearToyFilters()">Clear All Filters</button>
  <div class="toy-grid" id="toy-grid"></div>
</div>

<script>
function getSiteBase() {
  const script = document.querySelector('script[src$="toy-data.js"]');
  if (script) {
    return script.src.replace(/js\/toy-data\.js(\?.*)?$/, "");
  }
  return "";
}

let SITE_BASE = "";
let activeFilters = {
  tags: new Set(),
  build: new Set(),
  battery: new Set(),
  method: new Set(),
  activation: new Set(),
  threeD: new Set(),
  availability: new Set()
};
let searchQuery = "";

function handleToySearch(value) {
  searchQuery = value.trim().toLowerCase();
  renderToyCards();
}

function populateFilterGroup(containerId, items, categoryKey) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = items.map(item => `
    <label class="filter-chip">
      <input type="checkbox" value="${item}" data-group="${categoryKey}" onchange="toggleToyFilter(this)">
      <span>${item}</span>
    </label>
  `).join("");
}

function buildFilterBar() {
  const toys = window.TOY_DATA || [];
  
  const tags = window.TOY_TAGS || [];
  const builds = [...new Set(toys.map(t => t.build_type).filter(Boolean))];
  const batteries = [...new Set(toys.map(t => t.battery_type).filter(Boolean))];
  const methods = [...new Set(toys.map(t => t.method).filter(Boolean))];
  const activations = [...new Set(toys.map(t => t.activation_type).filter(Boolean))];
  const needs3d = [...new Set(toys.map(t => t.requires_3d).filter(Boolean))];

  populateFilterGroup("filter-bar-tags", tags, "tags");
  populateFilterGroup("filter-bar-build", builds, "build");
  populateFilterGroup("filter-bar-battery", batteries, "battery");
  populateFilterGroup("filter-bar-method", methods, "method");
  populateFilterGroup("filter-bar-activation", activations, "activation");
  populateFilterGroup("filter-bar-3d", needs3d, "threeD");
  populateFilterGroup("filter-bar-availability", ["Available", "Unavailable"], "availability");
}

function toggleToyFilter(checkbox) {
  const group = checkbox.dataset.group;
  if (checkbox.checked) {
    activeFilters[group].add(checkbox.value);
  } else {
    activeFilters[group].delete(checkbox.value);
  }
  renderToyCards();
}

function clearToyFilters() {
  Object.keys(activeFilters).forEach(k => activeFilters[k].clear());
  searchQuery = "";
  document.querySelectorAll("#toy-app input[type=checkbox]").forEach(cb => cb.checked = false);
  const searchBox = document.getElementById("toy-search");
  if (searchBox) searchBox.value = "";
  renderToyCards();
}

function renderToyCards() {
  const grid = document.getElementById("toy-grid");
  const toys = window.TOY_DATA || [];

  let visibleToys = toys.filter(t => {
    if (searchQuery && !t.name.toLowerCase().includes(searchQuery)) return false;

    if (activeFilters.tags.size > 0) {
      const matchTag = [...activeFilters.tags].some(tag => (t.tags || []).includes(tag));
      if (!matchTag) return false;
    }
    if (activeFilters.build.size > 0 && !activeFilters.build.has(t.build_type)) return false;
    if (activeFilters.battery.size > 0 && !activeFilters.battery.has(t.battery_type)) return false;
    if (activeFilters.method.size > 0 && !activeFilters.method.has(t.method)) return false;
    if (activeFilters.activation.size > 0 && !activeFilters.activation.has(t.activation_type)) return false;
    if (activeFilters.threeD.size > 0 && !activeFilters.threeD.has(t.requires_3d)) return false;
    if (activeFilters.availability.size > 0) {
      const isAvailStr = t.available ? "Available" : "Unavailable";
      if (!activeFilters.availability.has(isAvailStr)) return false;
    }

    return true;
  });

  grid.innerHTML = visibleToys.map(t => `
    <a href="${SITE_BASE}toys/${t.slug}/" class="toy-card" title="${t.description || t.name}">
      <div class="toy-card-image">
        <img src="${SITE_BASE}${t.image}" alt="${t.name}" loading="lazy"
             onerror="this.src='${SITE_BASE}images/placeholder.png'">
      </div>
      <div class="toy-card-label">
        <p class="toy-name">${t.name}</p>
        <p class="toy-category">${t.category}</p>
      </div>
    </a>
  `).join("");

  if (visibleToys.length === 0) {
    grid.innerHTML = `<p class="no-results">No toys match the selected filters.</p>`;
  }
}

function initToyApp() {
  if (!document.getElementById("toy-grid")) return;
  SITE_BASE = getSiteBase();
  buildFilterBar();
  renderToyCards();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initToyApp);
} else {
  initToyApp();
}

if (typeof document$ !== "undefined" && document$ && typeof document$.subscribe === "function") {
  document$.subscribe(initToyApp);
}
</script>