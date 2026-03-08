const params = new URLSearchParams(window.location.search);
const paperId = params.get("id");
const collectionKey = params.get("collection");

function byId(id) {
  return document.querySelector(id);
}

function fitHeadline(el, maxLines = 4) {
  const computed = window.getComputedStyle(el);
  const lineHeight = parseFloat(computed.lineHeight);
  const minSize = 1.7;
  let size = parseFloat(computed.fontSize) / 16;
  const maxHeight = lineHeight * maxLines + 1;

  while (el.scrollHeight > maxHeight && size > minSize) {
    size -= 0.08;
    el.style.fontSize = `${size}rem`;
  }
}

function renderStory(story) {
  const host = byId("#core-story");
  const labels = [
    ["Problem", story.problem],
    ["Limitation", story.limitation],
    ["Insight", story.insight],
    ["Method", story.proposed_method],
    ["Evidence", story.experimental_evidence],
  ];
  host.innerHTML = "";
  for (const [label, text] of labels) {
    const item = document.createElement("div");
    item.className = "story-step";
    item.innerHTML = `<p class="story-label">${label}</p><p>${text || "N/A"}</p>`;
    host.appendChild(item);
  }
}

function renderStack(hostSelector, items, formatter) {
  const host = byId(hostSelector);
  host.innerHTML = "";
  if (!items.length) {
    host.innerHTML = "<p>No structured items extracted.</p>";
    return;
  }
  for (const item of items) {
    const node = document.createElement("article");
    node.className = "stack-item";
    node.innerHTML = formatter(item);
    host.appendChild(node);
  }
}

function renderTemplates(templates) {
  const host = byId("#template-groups");
  host.innerHTML = "";
  for (const [group, items] of Object.entries(templates)) {
    const node = document.createElement("article");
    node.className = "template-group";
    const pretty = group.replaceAll("_", " ");
    const list = items.length
      ? `<ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>`
      : "<p>No templates captured.</p>";
    node.innerHTML = `<h3>${pretty}</h3>${list}`;
    host.appendChild(node);
  }
}

async function init() {
  const indexResponse = await fetch("data/index.json");
  const indexPayload = await indexResponse.json();
  const meta = indexPayload.papers.find((paper) => paper.paper_id === paperId);
  if (!meta) {
    throw new Error(`Unknown paper id: ${paperId}`);
  }
  const sourcePath =
    (collectionKey && meta.source_paths && meta.source_paths[collectionKey]) ||
    (meta.source_paths && meta.source_paths[meta.primary_collection_key]);
  if (!sourcePath) {
    throw new Error(`No source path found for ${paperId}`);
  }
  const recordResponse = await fetch(sourcePath);
  const record = await recordResponse.json();

  document.title = `${record.paper_title} | Elephant Paper Reading`;
  const titleEl = byId("#paper-title");
  titleEl.textContent = record.paper_title;
  byId("#paper-summary").textContent = record.core_story.summary || meta.story_summary;
  byId("#paper-source").textContent = record.source.filename;
  byId("#paper-generated").textContent = new Date(record.generated_at).toLocaleString();
  byId("#count-intro").textContent = `Introduction blocks: ${record.introduction_structure.length}`;
  byId("#count-method").textContent = `Method headings: ${record.method_structure.length}`;
  byId("#count-exp").textContent = `Experiment headings: ${record.experiment_structure.length}`;

  const tags = byId("#paper-tags");
  [meta.theme, ...(meta.collections || []), `${record.source.page_count} pages`].forEach((label) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = label;
    tags.appendChild(chip);
  });

  fitHeadline(titleEl, 4);

  renderStory(record.core_story);
  renderStack("#intro-structure", record.introduction_structure, (item) => `
    <h3>${item.paragraph_index}. ${item.paragraph_role}</h3>
    <p><strong>Main message:</strong> ${item.main_message}</p>
    <p><strong>Writing strategy:</strong> ${item.writing_strategy}</p>
  `);
  renderStack("#method-structure", record.method_structure, (item) => `
    <h3>${item.section_heading}</h3>
    <p><strong>Purpose:</strong> ${item.purpose}</p>
    <p><strong>Strategy:</strong> ${item.author_introduction_strategy}</p>
  `);
  renderStack("#experiment-structure", record.experiment_structure, (item) => `
    <h3>${item.section_heading}</h3>
    <p><strong>Purpose:</strong> ${item.purpose}</p>
    <p><strong>Strategy:</strong> ${item.author_introduction_strategy}</p>
  `);
  renderTemplates(record.writing_templates);

  const notableHost = byId("#notable-sentences");
  notableHost.innerHTML = "";
  for (const sentence of record.notable_sentences) {
    const li = document.createElement("li");
    li.textContent = sentence;
    notableHost.appendChild(li);
  }
}

init().catch((error) => {
  byId("#paper-title").textContent = "Paper not found";
  byId("#paper-summary").textContent = error.message;
});
