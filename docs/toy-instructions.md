# Toy Instructions

Browse switch-adapted toy builds. Use the filters below to narrow down by category, or scroll through everything.

!!! note "Some info may be out of date"
    This resource is where Makers Making Change hosts all of our toy instructions both current and past. This means, some of the toys that you find instructions for may not be available at the moment OR information may be out of date.

<div id="toy-app">
  <input type="text" id="toy-search" class="toy-search" placeholder="Search toys by name..." oninput="handleToySearch(this.value)">

  <button class="more-filters-toggle" id="more-filters-toggle" onclick="toggleMoreFilters()">Filters ▾</button>

  <div class="more-filters" id="more-filters" hidden>
    <div class="filter-group" id="filter-group-features">
      <span class="filter-group-label">Toy Features</span>
      <div class="filter-bar" id="filter-bar-features"></div>
    </div>
    <div class="filter-group" id="filter-group-activation">
      <span class="filter-group-label">Activation Type</span>
      <div class="filter-bar" id="filter-bar-activation"></div>
    </div>
    <div class="filter-group" id="filter-group-method">
      <span class="filter-group-label">Method of Adaptation</span>
      <div class="filter-bar" id="filter-bar-method"></div>
    </div>
    <div class="filter-group" id="filter-group-switches">
      <span class="filter-group-label">Number of Switches Required</span>
      <div class="filter-bar" id="filter-bar-switches"></div>
    </div>
    <div class="filter-group" id="filter-group-hfth">
      <span class="filter-group-label">HFTH Collection Year</span>
      <div class="filter-bar" id="filter-bar-hfth"></div>
    </div>
    <div class="filter-group filter-toggles">
      <label class="filter-toggle"><input type="checkbox" onchange="toggleFlag('requires_3d_printing', this)"> Requires 3D Printing</label>
      <label class="filter-toggle"><input type="checkbox" onchange="toggleFlag('available_to_purchase', this)"> Available to Purchase</label>
    </div>
  </div>

  <button class="clear-btn" onclick="clearToyFilters()">Clear Filters</button>
  <div class="toy-grid" id="toy-grid"></div>
</div>


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

.more-filters-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
  padding: 6px 14px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid var(--md-default-fg-color--lightest, #ccc);
  background: transparent;
  cursor: pointer;
  color: inherit;
}

.more-filters-toggle:hover {
  background: var(--md-code-bg-color, #f0f0f0);
}

.more-filters {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid var(--md-default-fg-color--lightest, #ddd);
  background: var(--md-code-bg-color, #f7f7f7);
}

/* .more-filters{display:flex} and the browser's built-in [hidden]{display:none}
   have equal CSS specificity, so without this, source order alone decided
   the tie and the panel could get stuck permanently visible regardless of
   the hidden attribute. This rule has higher specificity and always wins. */
.more-filters[hidden] {
  display: none;
}

.filter-group-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.65;
  margin-bottom: 6px;
}

.filter-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  user-select: none;
}

.filter-toggle input {
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