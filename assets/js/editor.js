/**
 * Editor page JavaScript — state management and rendering.
 *
 * Manages the in-memory state of workers and projects, renders them
 * into the DOM, and handles form submission (JSON to backend) and
 * YAML download.  No external dependencies — pure vanilla JS.
 *
 * @module editor
 */

// ---- State ----

/** @type {Array<{name: string, available_in: number}>} */
let workers = [{ name: "Worker 1", available_in: 0 }];

/** @type {Array<{name: string, tasks: Array<{name: string, days: number, parallel: boolean, depends_on: string[]}>}>} */
let projects = [{ name: "Project 1", tasks: [{ name: "Task 1", days: 1, parallel: false, depends_on: [] }] }];

// ---- Render helpers ----

/** Re-render the workers list into the DOM. */
function renderWorkers() {
    const container = document.getElementById("worker-list");
    container.innerHTML = "";
    workers.forEach((w, i) => {
        const div = document.createElement("div");
        div.className = "item-card";
        div.innerHTML = `
            <div class="row">
                <div>
                    <label class="small-label">Name</label>
                    <input type="text" value="${esc(w.name)}" onchange="workers[${i}].name=this.value">
                </div>
                <div>
                    <label class="small-label">Available In (days)</label>
                    <input type="number" min="0" value="${w.available_in}" onchange="workers[${i}].available_in=parseInt(this.value)||0">
                </div>
                <div style="flex:0 0 auto; padding-bottom: 8px;">
                    <button class="btn btn-danger" onclick="removeWorker(${i})">Remove</button>
                </div>
            </div>`;
        container.appendChild(div);
    });
}

/** Re-render the projects list and all nested tasks into the DOM. */
function renderProjects() {
    const container = document.getElementById("project-list");
    container.innerHTML = "";
    projects.forEach((p, pi) => {
        const div = document.createElement("div");
        div.className = "item-card";
        let tasksHTML = "";
        p.tasks.forEach((t, ti) => {
            const depsHTML = (t.depends_on || []).map((d, di) =>
                `<span class="dep-tag">${esc(d)}<button onclick="removeDep(${pi},${ti},${di})">&times;</button></span>`
            ).join("");
            const depOptions = getAllTaskIds().filter(id => id !== p.name + "/" + t.name)
                .map(id => `<option value="${esc(id)}">${esc(id)}</option>`).join("");
            tasksHTML += `
                <div class="task-item">
                    <div class="row">
                        <div>
                            <label class="small-label">Task Name</label>
                            <input type="text" value="${esc(t.name)}" onchange="projects[${pi}].tasks[${ti}].name=this.value; renderProjects()">
                        </div>
                        <div>
                            <label class="small-label">Days</label>
                            <input type="number" min="1" value="${t.days}" onchange="projects[${pi}].tasks[${ti}].days=parseInt(this.value)||1">
                        </div>
                        <div style="flex:0 0 auto">
                            <label class="small-label">&nbsp;</label><br>
                            <label><input type="checkbox" ${t.parallel ? "checked" : ""} onchange="projects[${pi}].tasks[${ti}].parallel=this.checked"> Parallel</label>
                        </div>
                        <div style="flex:0 0 auto; padding-bottom: 8px;">
                            <button class="btn btn-danger" onclick="removeTask(${pi},${ti})">Remove</button>
                        </div>
                    </div>
                    <div>
                        <label class="small-label">Dependencies</label>
                        <div class="depends-list">${depsHTML}</div>
                        <div class="row" style="margin-top:4px">
                            <select id="dep-sel-${pi}-${ti}">
                                <option value="">-- add dependency --</option>
                                ${depOptions}
                            </select>
                            <div style="flex:0 0 auto">
                                <button class="btn btn-secondary" onclick="addDep(${pi},${ti})">+</button>
                            </div>
                        </div>
                    </div>
                </div>`;
        });

        div.innerHTML = `
            <div class="item-header">
                <div class="row" style="flex:1">
                    <div>
                        <label class="small-label">Project Name</label>
                        <input type="text" value="${esc(p.name)}" onchange="projects[${pi}].name=this.value; renderProjects()">
                    </div>
                    <div style="flex:0 0 auto; padding-bottom: 8px;">
                        <button class="btn btn-danger" onclick="removeProject(${pi})">Remove</button>
                    </div>
                </div>
            </div>
            <div>${tasksHTML}</div>
            <button class="btn btn-secondary" onclick="addTask(${pi})" style="margin-top:4px">+ Add Task</button>`;
        container.appendChild(div);
    });
}

// ---- Actions ----

/** Add a new worker with a default name and re-render. */
function addWorker() {
    workers.push({ name: "Worker " + (workers.length + 1), available_in: 0 });
    renderWorkers();
}
/** Remove a worker by index and re-render. */
function removeWorker(i) { workers.splice(i, 1); renderWorkers(); }

/** Add a new project with one default task and re-render. */
function addProject() {
    projects.push({ name: "Project " + (projects.length + 1), tasks: [{ name: "Task 1", days: 1, parallel: false, depends_on: [] }] });
    renderProjects();
}
/** Remove a project by index and re-render. */
function removeProject(i) { projects.splice(i, 1); renderProjects(); }

/** Add a new task to a project and re-render. */
function addTask(pi) {
    projects[pi].tasks.push({ name: "Task " + (projects[pi].tasks.length + 1), days: 1, parallel: false, depends_on: [] });
    renderProjects();
}
/** Remove a task from a project and re-render. */
function removeTask(pi, ti) { projects[pi].tasks.splice(ti, 1); renderProjects(); }

/** Collect all task IDs across all projects in "Project/Task" format. */
function getAllTaskIds() {
    const ids = [];
    projects.forEach(p => p.tasks.forEach(t => ids.push(p.name + "/" + t.name)));
    return ids;
}
/** Add a dependency to a task from the dropdown selector. */
function addDep(pi, ti) {
    const sel = document.getElementById("dep-sel-" + pi + "-" + ti);
    if (sel.value && !(projects[pi].tasks[ti].depends_on || []).includes(sel.value)) {
        if (!projects[pi].tasks[ti].depends_on) projects[pi].tasks[ti].depends_on = [];
        projects[pi].tasks[ti].depends_on.push(sel.value);
        renderProjects();
    }
}
/** Remove a dependency from a task by index and re-render. */
function removeDep(pi, ti, di) {
    projects[pi].tasks[ti].depends_on.splice(di, 1);
    renderProjects();
}

/**
 * Build the JSON payload from current editor state.
 * @returns {Object} JSON-serializable config object for the backend.
 */
function buildPayload() {
    return {
        workers: workers.length,
        worker_names: workers.map(w => ({ name: w.name, available_in: w.available_in || 0 })),
        calendar: {
            start_date: document.getElementById("start-date").value || "",
            show_weekends: document.getElementById("show-weekends").checked,
        },
        projects: projects.map(p => ({
            name: p.name,
            tasks: p.tasks.map(t => ({
                name: t.name,
                days: t.days,
                parallel: !!t.parallel,
                depends_on: t.depends_on || [],
            })),
        })),
    };
}

/** Submit the config to the backend and replace the page with the Gantt chart. */
function generateSchedule() {
    const payload = buildPayload();
    fetch("/editor/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    })
    .then(r => { if (!r.ok) return r.text().then(t => { throw new Error(t); }); return r.text(); })
    .then(html => { document.open(); document.write(html); document.close(); })
    .catch(err => alert("Error: " + err.message));
}

/** Download the current config as a YAML file via the backend. */
function downloadYAML() {
    const payload = buildPayload();
    fetch("/editor/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    })
    .then(r => { if (!r.ok) return r.text().then(t => { throw new Error(t); }); return r.blob(); })
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "config.yaml";
        a.click();
        URL.revokeObjectURL(url);
    })
    .catch(err => alert("Error: " + err.message));
}

/**
 * Escape a string for safe insertion into HTML.
 * Uses the browser's built-in text encoding via a temporary DOM element.
 * @param {string} s - The raw string to escape.
 * @returns {string} HTML-safe string.
 */
function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// ---- Init ----
renderWorkers();
renderProjects();
