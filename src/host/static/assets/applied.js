const api = (path, options = {}) =>
  fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

const $ = (id) => document.getElementById(id);
const bodyEl = $("jobs-body");
const emptyEl = $("jobs-empty");
let currentPage = 1;
let outcomeFilter = "";
const PAGE_SIZE = 10;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function jobQuery() {
  const params = new URLSearchParams();
  const q = $("filter-query")?.value.trim() || "";
  const sort = $("sort")?.value || "recent";
  params.set("applied", "true");
  if (q) params.set("query", q);
  if (outcomeFilter) params.set("outcome", outcomeFilter);
  if (sort) params.set("sort", sort);
  params.set("page", String(currentPage));
  params.set("page_size", String(PAGE_SIZE));
  return `/api/v1/job/?${params.toString()}`;
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function visaPill(job) {
  if (job.sponsorship === "yes") return `<span class="pill yes">Visa</span>`;
  if (job.sponsorship === "no") return `<span class="pill no">No visa</span>`;
  return `<span class="pill">—</span>`;
}

function outcomeClass(outcome) {
  if (outcome === "passed") return "is-passed";
  if (outcome === "rejected") return "is-rejected";
  return "is-pending";
}

function oddsCell(value) {
  if (value == null) return "—";
  const n = Math.max(0, Math.min(100, Math.round(value)));
  return `<div class="odds"><b>${n}%</b><span class="odds-bar"><i style="width:${n}%"></i></span></div>`;
}

function renderStats(stats) {
  const applied = stats.applied ?? 0;
  setText("stat-applied", applied);
  setText("stat-pending", stats.pending ?? 0);
  setText("stat-passed", stats.passed ?? 0);
  setText("stat-rejected", stats.rejected ?? 0);
  setText("stat-success", `${Math.round(stats.avg_success || 0)}%`);
  const badge = $("nav-applied-count");
  if (badge) {
    badge.textContent = applied ? String(applied) : "";
    badge.hidden = !applied;
  }
}

function pageList(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const keep = new Set([1, total, current, current - 1, current + 1]);
  const ordered = [...keep].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b);
  const result = [];
  for (const num of ordered) {
    const prev = result[result.length - 1];
    if (prev && num - prev > 1) result.push("…");
    result.push(num);
  }
  return result;
}

function renderPager(page) {
  const pager = $("pager");
  const total = page.total || 0;
  if (!pager) return;
  if (!total) {
    pager.hidden = true;
    setText("page-info", "No applications");
    return;
  }
  pager.hidden = false;
  currentPage = page.page;
  const start = (page.page - 1) * page.page_size + 1;
  const end = Math.min(page.page * page.page_size, total);
  setText("page-info", `Showing ${start}–${end} of ${total}`);
  const prev = $("page-prev");
  const next = $("page-next");
  if (prev) prev.disabled = page.page <= 1;
  if (next) next.disabled = page.page >= page.pages;
  const numbers = $("page-numbers");
  if (!numbers) return;
  numbers.innerHTML = pageList(page.page, page.pages)
    .map((item) => {
      if (item === "…") return `<span class="pager-gap">…</span>`;
      const current = item === page.page ? " is-current" : "";
      return `<button type="button" class="${current}" data-page="${item}">${item}</button>`;
    })
    .join("");
  numbers.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      currentPage = Number(button.dataset.page);
      loadJobs();
    });
  });
}

function bindRowActions() {
  bodyEl.querySelectorAll(".seg button").forEach((button) => {
    button.addEventListener("click", async () => {
      const wrap = button.closest(".seg");
      const next = button.dataset.outcome;
      if (!wrap || wrap.dataset.current === next) return;
      wrap.querySelectorAll("button").forEach((item) => item.disabled = true);
      const res = await api(`/api/v1/job/${wrap.dataset.id}/outcome`, {
        method: "POST",
        body: JSON.stringify({ outcome: next }),
      });
      wrap.querySelectorAll("button").forEach((item) => item.disabled = false);
      if (res.ok) await loadJobs();
    });
  });
  bodyEl.querySelectorAll("[data-apply]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      button.disabled = true;
      const res = await api(`/api/v1/job/${button.dataset.apply}/applied`, {
        method: "POST",
        body: JSON.stringify({ applied: false }),
      });
      if (!res.ok) {
        button.disabled = false;
        return;
      }
      await loadJobs();
    });
  });
}

function renderJobs(page) {
  const jobs = page.items || [];
  renderPager(page);
  if (!jobs.length) {
    const labels = { pending: "waiting", passed: "passed", rejected: "rejected" };
    bodyEl.innerHTML = "";
    emptyEl.classList.remove("hidden");
    emptyEl.textContent = outcomeFilter
      ? `No ${labels[outcomeFilter] || outcomeFilter} applications in this list.`
      : "No applications yet. Mark a role with I applied on the search page.";
    return;
  }
  emptyEl.classList.add("hidden");
  bodyEl.innerHTML = jobs
    .map((job) => {
      const url = job.url || "#";
      const outcome = job.outcome || "pending";
      return `
        <tr data-id="${job.id}" class="${outcomeClass(outcome)}">
          <td>
            <div class="role-cell">
              <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(job.title)}</a>
              <span>${escapeHtml(job.company || "—")}</span>
            </div>
          </td>
          <td class="loc-cell" title="${escapeHtml(job.location || "")}">${escapeHtml(job.location || "—")}</td>
          <td>${oddsCell(job.interview_success_rate)}</td>
          <td>${visaPill(job)}</td>
          <td>
            <div class="seg" data-id="${job.id}" data-current="${escapeHtml(outcome)}">
              <button type="button" data-outcome="pending"${outcome === "pending" ? " class=\"is-on\"" : ""}>Waiting</button>
              <button type="button" data-outcome="passed"${outcome === "passed" ? " class=\"is-on\"" : ""}>Passed</button>
              <button type="button" data-outcome="rejected"${outcome === "rejected" ? " class=\"is-on\"" : ""}>Rejected</button>
            </div>
          </td>
          <td>
            <div class="row-act">
              <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Open</a>
              <button type="button" data-apply="${job.id}">Undo</button>
            </div>
          </td>
        </tr>`;
    })
    .join("");
  bindRowActions();
}

function renderSkeleton() {
  emptyEl.classList.add("hidden");
  bodyEl.innerHTML = Array.from(
    { length: 8 },
    () => `<tr class="ap-skel"><td></td><td></td><td></td><td></td><td></td><td></td></tr>`
  ).join("");
}

async function loadJobs() {
  renderSkeleton();
  try {
    const [statsRes, jobsRes] = await Promise.all([
      api("/api/v1/job/stats?applied=true"),
      api(jobQuery()),
    ]);
    if (statsRes.ok) renderStats(await statsRes.json());
    if (jobsRes.ok) {
      renderJobs(await jobsRes.json());
      return;
    }
    bodyEl.innerHTML = "";
    emptyEl.classList.remove("hidden");
    emptyEl.textContent = "Could not load applied roles.";
  } catch (error) {
    bodyEl.innerHTML = "";
    emptyEl.classList.remove("hidden");
    emptyEl.textContent = "Could not load applied roles. Reload the page.";
  }
}

$("outcome-tabs")?.querySelectorAll("button").forEach((button) => {
  button.addEventListener("click", () => {
    $("outcome-tabs").querySelectorAll("button").forEach((item) => item.classList.remove("is-on"));
    button.classList.add("is-on");
    outcomeFilter = button.dataset.outcome || "";
    currentPage = 1;
    loadJobs();
  });
});

$("filter-query")?.addEventListener("change", () => {
  currentPage = 1;
  loadJobs();
});
$("filter-query")?.addEventListener("keyup", (event) => {
  if (event.key === "Enter") {
    currentPage = 1;
    loadJobs();
  }
});
$("sort")?.addEventListener("change", () => {
  currentPage = 1;
  loadJobs();
});
$("page-prev")?.addEventListener("click", () => {
  if (currentPage <= 1) return;
  currentPage -= 1;
  loadJobs();
});
$("page-next")?.addEventListener("click", () => {
  currentPage += 1;
  loadJobs();
});

loadJobs();
