const state = {
  papers: [],
  activeTheme: "All",
  query: "",
};

const grid = document.querySelector("#paper-grid");
const cardTemplate = document.querySelector("#paper-card-template");
const searchInput = document.querySelector("#search-input");
const themeFilter = document.querySelector("#theme-filter");
const paperCount = document.querySelector("#paper-count");
const themeCount = document.querySelector("#theme-count");

function matchesPaper(paper) {
  const themeOk = state.activeTheme === "All" || paper.theme === state.activeTheme;
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
  return themeOk && queryOk;
}

function renderPapers() {
  const papers = state.papers.filter(matchesPaper);
  grid.innerHTML = "";
  for (const paper of papers) {
    const node = cardTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".theme-pill").textContent = paper.theme;
    node.querySelector(".dataset-pill").textContent = paper.dataset;
    node.querySelector(".paper-title").textContent = paper.paper_title;
    node.querySelector(".paper-summary").textContent = paper.story_summary;
    node.querySelector(".story-method").textContent = paper.proposed_method;
    node.querySelector(".meta-intro").textContent = paper.intro_paragraphs;
    node.querySelector(".meta-method").textContent = paper.method_sections;
    node.querySelector(".meta-exp").textContent = paper.experiment_sections;
    const link = node.querySelector(".card-link");
    link.href = paper.detail_path;
    grid.appendChild(node);
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
