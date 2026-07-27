# Toy Instructions

Browse switch-adapted toy builds. Use the filters below to narrow down by category, or scroll through everything.

!!! note "Adding a new toy"
    This resource is where Makers Making Change hosts all of our toy instructions both current and past. This means, some of the toys that you find instructions for may not be available at the moment OR information may be out of date.

<div id="toy-app">
  <input type="text" id="toy-search" class="toy-search" placeholder="Search toys by name..." oninput="handleToySearch(this.value)">
  <div class="filter-bar" id="filter-bar"></div>
  <button class="clear-btn" onclick="clearToyFilters()">Clear Filters</button>
  <div class="toy-grid" id="toy-grid"></div>
</div>

<script>
// Data comes from window.TOY_TAGS and window.TOY_DATA,
// which are generated automatically by scripts/generate_toy_data.py
// during the site build - see docs/js/toy-data.js (auto-generated, do not edit).

// Relative image paths break on this page because MkDocs serves it at
// /toy-instructions/ (a folder) rather than a flat file, so a plain
// relative path like "images/toys/x.jpg" would incorrectly resolve to
// /toy-instructions/images/toys/x.jpg. To fix this without hardcoding
// the site's root path, we borrow the already-correct absolute URL that
// the browser resolved for the toy-data.js <script> tag itself.
function getSiteBase() {
  const script = document.querySelector('script[src$="toy-data.js"]');
  if (script) {
    return script.src.replace(/js\/toy-data\.js(\?.*)?$/, "");
  }
  return ""; // fallback - relative paths, may break on nested pages
}

let SITE_BASE = "";

let activeFilters = new Set();
let searchQuery = "";

function handleToySearch(value) {
  searchQuery = value.trim().toLowerCase();
  renderToyCards();
}

function buildFilterBar() {
  const bar = document.getElementById("filter-bar");
  const tags = window.TOY_TAGS || [];
  bar.innerHTML = tags.map(tag => `
    <label class="filter-chip">
      <input type="checkbox" value="${tag}" onchange="toggleToyFilter(this)">
      <span>${tag}</span>
    </label>
  `).join("");
}

function toggleToyFilter(checkbox) {
  if (checkbox.checked) {
    activeFilters.add(checkbox.value);
  } else {
    activeFilters.delete(checkbox.value);
  }
  renderToyCards();
}

function clearToyFilters() {
  activeFilters.clear();
  searchQuery = "";
  document.querySelectorAll("#filter-bar input[type=checkbox]").forEach(cb => cb.checked = false);
  const searchBox = document.getElementById("toy-search");
  if (searchBox) searchBox.value = "";
  renderToyCards();
}

function renderToyCards() {
  const grid = document.getElementById("toy-grid");
  const toys = window.TOY_DATA || [];

  let visibleToys = activeFilters.size === 0
    ? toys
    : toys.filter(t => (t.tags || []).some(tag => activeFilters.has(tag)));

  if (searchQuery) {
    visibleToys = visibleToys.filter(t => t.name.toLowerCase().includes(searchQuery));
  }

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

// Runs the app once the page (and any deferred scripts like toy-data.js)
// have finished loading. DOMContentLoaded fires after deferred scripts
// run, so window.TOY_DATA is guaranteed to be set by this point on a
// normal page load.
function initToyApp() {
  if (!document.getElementById("toy-grid")) return;
  SITE_BASE = getSiteBase();
  activeFilters = new Set();
  searchQuery = "";
  buildFilterBar();
  renderToyCards();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initToyApp);
} else {
  // DOM already loaded by the time this script ran
  initToyApp();
}

// Material for MkDocs uses instant-loading (SPA-style) navigation, which
// swaps page content without a full reload. If document$ exists (it's
// provided by the Material theme bundle), also re-run on every page swap
// so the cards reappear correctly when navigating back to this page.
if (typeof document$ !== "undefined" && document$ && typeof document$.subscribe === "function") {
  document$.subscribe(initToyApp);
}
</script>

<style>
.toy-search {
  display: block;
  width: 100%;
  max-width: 320px;
  padding: 8px 12px;
  margin-bottom: 14px;
  font-size: 0.9rem;
  border-radius: 8px;
  border: 1px solid var(--md-default-fg-color--lightest, #ccc);
  background: var(--md-default-bg-color, #fff);
  color: inherit;
}

.toy-search:focus {
  outline: none;
  border-color: var(--md-primary-fg-color, #888);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--md-default-fg-color--lightest, #ccc);
  border-radius: 999px;
  font-size: 0.85rem;
  cursor: pointer;
  user-select: none;
}

.filter-chip input {
  cursor: pointer;
}

.clear-btn {
  margin-bottom: 20px;
  padding: 6px 14px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid var(--md-default-fg-color--lightest, #ccc);
  background: transparent;
  cursor: pointer;
}

.clear-btn:hover {
  background: var(--md-code-bg-color, #f0f0f0);
}

.toy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 14px;
}

.toy-card {
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--md-default-fg-color--lightest, #ddd);
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.toy-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 10px rgba(0,0,0,0.15);
}

.toy-card-image {
  width: 100%;
  aspect-ratio: 1 / 1;
  background: var(--md-code-bg-color, #eee);
  overflow: hidden;
}

.toy-card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.toy-card-label {
  padding: 8px 10px;
}

.toy-name {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.2;
}

.toy-category {
  margin: 2px 0 0 0;
  font-size: 0.7rem;
  opacity: 0.65;
}

.no-results {
  grid-column: 1 / -1;
  text-align: center;
  opacity: 0.6;
  padding: 30px 0;
}
</style>