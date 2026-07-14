# Toy Instructions

Browse switch-adapted toy builds. Use the filters below to narrow down by category, or scroll through everything.

---

<!--
============================================================================
 HOW TO ADD A NEW TOY (no coding knowledge needed!)
============================================================================
 1. Scroll down to the block that starts with "const toys = [".
 2. Copy one whole { ... } block below (including the commas).
 3. Paste it right before the closing "];" line.
 4. Change the text inside the quotes for your new toy:
      - name       -> the toy's name, e.g. "Bubble Blower"
      - image      -> path to a thumbnail photo (see note below)
      - link       -> the GitHub folder/README link for that toy
      - category   -> must exactly match one of the categories listed
                      in "const categories" further up. If your toy's
                      main folder isn't in that list yet, add it there
                      FIRST (see instructions above that list).
 5. Save the file, commit, and push. That's it - the card and the
    filter button will both appear automatically.

 ADDING A THUMBNAIL PHOTO:
 - Put your image file in: docs/images/toys/
 - Give it a short, simple, no-spaces filename, e.g. bubble-blower.jpg
 - Then set image to: "images/toys/bubble-blower.jpg"
 - If you don't have a photo yet, leave it as "images/toys/placeholder.jpg"
   and swap it in later - the card will still work, just with a
   placeholder image.
============================================================================
-->

<div id="toy-app">

  <div class="filter-bar" id="filter-bar">
    <!-- Filter buttons are generated automatically from the category list below -->
  </div>
  <button class="clear-btn" onclick="clearToyFilters()">Clear Filters</button>

  <div class="toy-grid" id="toy-grid">
    <!-- Cards are generated automatically - you never need to edit this part -->
  </div>

</div>

<script>
// ============================================================================
// STEP 1: CATEGORIES
// These come from the main folders inside Toy_Instructions on GitHub.
// To add a new category/folder, just add a new line in "quotes, like this,"
// ============================================================================
const categories = [
  "Battery Interrupter Toys",
  "Solderless Toys",
  "Bluetooth / Electronic Toys",
  "3D Printed Mounts"
];

// ============================================================================
// STEP 2: TOYS
// One block per toy. Copy a whole { ... }, block and edit the text in quotes.
// Make sure "category" exactly matches one entry from the list above.
// ============================================================================
const toys = [
  {
    name: "Bubble Blower",
    image: "images/toys/bubble-blower.jpg",
    link: "https://github.com/makersmakingchange/Switch-Adapted-Bubble-Blower",
    category: "Battery Interrupter Toys"
  },
  {
    name: "Nerf Gun",
    image: "images/toys/nerf-gun.jpg",
    link: "https://github.com/makersmakingchange/Switch-Adapted-Nerf-Gun",
    category: "Battery Interrupter Toys"
  },
  {
    name: "My Pal Scout / Violet",
    image: "images/toys/my-pal-scout.jpg",
    link: "https://github.com/makersmakingchange/My-Pal-Scout-Violet-Switch-Adapted-Toy",
    category: "Solderless Toys"
  },
  {
    name: "Beat Bow Wow",
    image: "images/toys/beat-bow-wow.jpg",
    link: "https://github.com/makersmakingchange/Switch-Adapted-Beat-Bow-Wow",
    category: "Solderless Toys"
  },
  {
    name: "Spinning Light Wand",
    image: "images/toys/spinning-light-wand.jpg",
    link: "https://github.com/makersmakingchange/Spinning-Light-Wand-Adaptation",
    category: "3D Printed Mounts"
  },
  {
    name: "Spin Art Toy",
    image: "images/toys/spin-art.jpg",
    link: "https://github.com/makersmakingchange/Spin-Art-Switch-Adapted-Toy",
    category: "3D Printed Mounts"
  }
];

// ============================================================================
// Everything below this line is the engine that builds the page.
// You should not need to touch it.
// ============================================================================
let activeFilters = new Set();

function buildFilterBar() {
  const bar = document.getElementById("filter-bar");
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
  const visibleToys = activeFilters.size === 0
    ? toys
    : toys.filter(t => activeFilters.has(t.category));

  grid.innerHTML = visibleToys.map(t => `
    <a href="${t.link}" class="toy-card" target="_blank" rel="noopener">
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

buildFilterBar();
renderToyCards();
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
