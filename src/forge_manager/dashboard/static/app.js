async function load(path) {
  const output = document.getElementById("output");
  output.textContent = "Loading...";
  const res = await fetch(path);
  if (!res.ok) {
    output.textContent = `HTTP ${res.status}`;
    return;
  }
  const data = await res.json();
  output.textContent = data.text;
}

document.querySelectorAll("button[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.dataset.action;
    const view = button.dataset.view;
    const active = button.dataset.active ? "&active=1" : "";
    load(`/api/${action}?view=${encodeURIComponent(view)}${active}`);
  });
});

document.getElementById("project-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const id = document.getElementById("project-id").value.trim() || "forge";
  const view = document.getElementById("project-view").value;
  load(`/api/project?id=${encodeURIComponent(id)}&view=${encodeURIComponent(view)}`);
});

load("/api/structure?view=tree&active=1");
