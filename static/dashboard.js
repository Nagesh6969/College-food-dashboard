function el(id) { return document.getElementById(id); }

function renderList(ulId, items, emptyText) {
  const ul = el(ulId);
  ul.innerHTML = "";
  if (!items || items.length === 0) {
    ul.innerHTML = `<li class="empty">${emptyText}</li>`;
    return;
  }
  items.forEach(t => {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  });
}

function runInlineScripts(container) {
  container.querySelectorAll("script").forEach(old => {
    const s = document.createElement("script");
    s.textContent = old.textContent;
    old.replaceWith(s);
  });
}

let CURRENT_FILTERS = [];

async function buildFilters() {
  const res = await fetch("/api/dashboard-meta");
  const meta = await res.json();
  CURRENT_FILTERS = meta.filters;

  el("dash-source").textContent = meta.dataset_label;
  el("dash-title").textContent = meta.schema === "food"
    ? "Food Choice Analysis Dashboard"
    : "Dataset Dashboard (auto-detected)";

  const bar = el("filter-bar");
  bar.innerHTML = "";
  if (meta.filters.length === 0) {
    bar.innerHTML = `<div class="filter-note">No categorical columns found to filter by — showing the full dataset.</div>`;
  } else {
    meta.filters.forEach(f => {
      const group = document.createElement("div");
      group.className = "filter-group";
      group.innerHTML = `<label for="f-${f.key}">${f.label}</label>
        <select id="f-${f.key}">${f.options.map(o => `<option value="${o}">${o}</option>`).join("")}</select>`;
      bar.appendChild(group);
    });
    const note = document.createElement("div");
    note.className = "filter-note";
    note.id = "filter-note";
    bar.appendChild(note);

    meta.filters.forEach(f => {
      el(`f-${f.key}`).addEventListener("change", loadData);
    });
  }
}

async function loadData() {
  const params = new URLSearchParams();
  CURRENT_FILTERS.forEach(f => {
    const sel = el(`f-${f.key}`);
    if (sel) params.set(f.key, sel.value);
  });

  const noteEl = el("filter-note");
  if (noteEl) noteEl.textContent = "Loading…";

  const res = await fetch(`/api/dashboard-data?${params.toString()}`);
  const data = await res.json();

  // KPIs
  const kpiRow = el("kpi-row");
  kpiRow.innerHTML = "";
  data.kpis.forEach(k => {
    const card = document.createElement("div");
    card.className = "kpi-card";
    card.innerHTML = `<div class="num">${k.value}</div><div class="label">${k.label}</div>`;
    kpiRow.appendChild(card);
  });

  // Charts
  const grid = el("chart-grid");
  grid.innerHTML = "";
  if (data.charts.length === 0) {
    grid.innerHTML = `<p style="padding:20px;color:#6b6f68;">No data for this filter combination.</p>`;
  } else {
    data.charts.forEach(c => {
      const box = document.createElement("div");
      box.className = "chart-box";
      box.id = `box-${c.id}`;
      box.innerHTML = c.html;
      grid.appendChild(box);
      runInlineScripts(box);
    });
  }

  // Suggestions
  renderList("sug-take", data.suggestions.take, "No positive habits stand out yet.");
  renderList("sug-avoid", data.suggestions.avoid, "Nothing flagged to avoid for this group.");
  renderList("sug-watch", data.suggestions.watch, "Nothing to escalate right now.");

  const n = data.kpis.length ? data.kpis[0].value : 0;
  const note2 = el("filter-note");
  if (note2) note2.textContent = `Showing ${n} record${n === 1 ? "" : "s"}`;
}

(async function init() {
  await buildFilters();
  await loadData();
})();
