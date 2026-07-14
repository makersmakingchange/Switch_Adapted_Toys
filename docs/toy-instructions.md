# Toy Instructions

Browse switch-adapted toy builds. Use the filters below to narrow down by category, or scroll through everything.

!!! note "Adding a new toy"
    You don't need to edit this page at all. To add a new toy to the site:

    1. Go to the `Toy_Instructions` folder on GitHub.
    2. Open the category folder that fits your toy (`Bubble`, `Lamp_Projector`, `RC`, `Sound_movement_light`, or `Water_nerf_gun`). If none fit, create a new folder for the category.
    3. Create a new folder for your toy inside it, and add a photo (jpg/png) of the toy.
    4. Optional: add a plain text file named `info.txt` inside that folder if you want to set a custom name, link, or description (see the template in `Toy_Instructions/_TEMPLATE/info.txt`).
    5. Commit your changes. The card and its filter will appear automatically the next time the site rebuilds (a few minutes after you push).

<div id="toy-app">
  <div class="filter-bar" id="filter-bar"></div>
  <button class="clear-btn" onclick="clearToyFilters()">Clear Filters</button>
  <div class="toy-grid" id="toy-grid"></div>
</div>

<script>
// Data comes from window.TOY_CATEGORIES and window.TOY_DATA,
// which are generated automatically by scripts/generate_toy_data.py
// during the site build - see docs/js/toy-data.js (auto-generated, do not edit).

let activeFilters = new Set();

function buildFilterBar() {
  const bar = document.getElementById("filter-bar");
  const categories = window.TOY_CATEGORIES || [];
  bar.innerHTML = categories.map(cat => `
    <label class="filter-chip">
      <input type="checkbox" value="${cat}" onchange="toggleToyFilter(this)">
      <span>${cat}</span>
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
  document.querySelectorAll("#filter-bar input[type=checkbox]").forEach(cb => cb.checked = false);
  renderToyCards();
}

function renderToyCards() {
  const grid = document.getElementById("toy-grid");
  const toys = window.TOY_DATA || [];
  const visibleToys = activeFilters.size === 0
    ? toys
    : toys.filter(t => activeFilters.has(t.category));

  grid.innerHTML = visibleToys.map(t => `
    <a href="${t.link}" class="toy-card" target="_blank" rel="noopener" title="${t.description || t.name}">
      <div class="toy-card-image">
        <img src="${t.image}" alt="${t.name}" loading="lazy"
             onerror="this.src='images/toys/placeholder.jpg'">
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

// document$ is provided by Material for MkDocs and fires after every
// page load AND every instant-navigation page swap - this avoids both
// the "toy-data.js hasn't loaded yet" race condition and the
// "script didn't re-run after clicking an internal link" issue.
document$.subscribe(function() {
  if (document.getElementById("toy-grid")) {
    buildFilterBar();
    renderToyCards();
  }
});
</script>

<style>
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