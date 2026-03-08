const state = {
  papers: [],
  activeTheme: "All",
  activeCollection: "All",
  query: "",
};

const grid = document.querySelector("#paper-grid");
const cardTemplate = document.querySelector("#paper-card-template");
const searchInput = document.querySelector("#search-input");
const collectionFilter = document.querySelector("#collection-filter");
const themeFilter = document.querySelector("#theme-filter");
const paperCount = document.querySelector("#paper-count");
const themeCount = document.querySelector("#theme-count");
const heroTitle = document.querySelector(".hero h1");

function fitBlock(el, maxLines, minRem) {
  if (!el) return;
  el.style.fontSize = "";
  const computed = window.getComputedStyle(el);
  const lineHeight = parseFloat(computed.lineHeight);
  let size = parseFloat(computed.fontSize) / 16;
  const maxHeight = lineHeight * maxLines + 1;

  while (el.scrollHeight > maxHeight && size > minRem) {
    size -= 0.08;
    el.style.fontSize = `${size}rem`;
  }
}

function classifyCardTitle(el) {
  if (!el) return;
  const text = (el.textContent || "").trim();
  const words = text.split(/\s+/).filter(Boolean);
  const chars = text.length;
  el.classList.remove("is-short");
  if (words.length <= 8 || chars <= 58) {
    el.classList.add("is-short");
  }
}

function matchesPaper(paper) {
  const themeOk = state.activeTheme === "All" || paper.theme === state.activeTheme;
  const collectionOk =
    state.activeCollection === "All" ||
    (paper.collections || []).includes(state.activeCollection);
  const haystack = [
    paper.paper_title,
    paper.story_summary,
    paper.problem,
    paper.proposed_method,
    paper.notable_sentence,
  ]
    .join(" ")
    .toLowerCase();
  const queryOk = haystack.includes(state.query.toLowerCase());
  return themeOk && collectionOk && queryOk;
}

function renderPapers() {
  const papers = state.papers.filter(matchesPaper);
  grid.innerHTML = "";
  for (const paper of papers) {
    const node = cardTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".theme-pill").textContent = paper.theme;
    const collections = node.querySelector(".collection-list");
    collections.innerHTML = "";
    for (const label of paper.collections || []) {
      const chip = document.createElement("span");
      chip.className = "dataset-pill";
      chip.textContent = label;
      collections.appendChild(chip);
    }
    const title = node.querySelector(".paper-title");
    title.textContent = paper.paper_title;
    classifyCardTitle(title);
    node.querySelector(".paper-summary").textContent = paper.story_summary;
    node.querySelector(".story-method").textContent = paper.proposed_method;
    node.querySelector(".meta-intro").textContent = paper.intro_paragraphs;
    node.querySelector(".meta-method").textContent = paper.method_sections;
    node.querySelector(".meta-exp").textContent = paper.experiment_sections;
    const link = node.querySelector(".card-link");
    link.href = paper.detail_path;
    grid.appendChild(node);
    fitBlock(title, 3, 0.96);
  }
}

function renderCollections(collections) {
  const items = ["All", ...collections];
  collectionFilter.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.className = `chip${state.activeCollection === item ? " is-active" : ""}`;
    button.type = "button";
    button.textContent = item;
    button.addEventListener("click", () => {
      state.activeCollection = item;
      renderCollections(collections);
      renderPapers();
    });
    collectionFilter.appendChild(button);
  }
}

function renderThemes(themes) {
  const items = ["All", ...themes];
  themeFilter.innerHTML = "";
  for (const item of items) {
    const button = document.createElement("button");
    button.className = `chip${state.activeTheme === item ? " is-active" : ""}`;
    button.type = "button";
    button.textContent = item;
    button.addEventListener("click", () => {
      state.activeTheme = item;
      renderThemes(themes);
      renderPapers();
    });
    themeFilter.appendChild(button);
  }
}

async function init() {
  const response = await fetch("data/index.json");
  const payload = await response.json();
  state.papers = payload.papers;
  paperCount.textContent = payload.stats.paper_count;
  themeCount.textContent = payload.stats.theme_count;
  fitBlock(heroTitle, 6, 2.2);
  renderCollections(payload.collections || []);
  renderThemes(payload.themes);
  renderPapers();
}

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value.trim();
  renderPapers();
});

init().catch((error) => {
  grid.innerHTML = `<p>Failed to load site index: ${error.message}</p>`;
});
