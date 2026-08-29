const api = (path, options = {}) =>
  fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

const $ = (id) => document.getElementById(id);
const jobsEl = $("jobs");
const statusEl = $("status");
let currentPage = 1;
const PAGE_SIZE = 10;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function ringHtml(value) {
  const n = Math.round(value ?? 0);
  return `<div class="ring" style="--p:${n}"><strong>${n}%</strong></div>`;
}

function flag(label, on, extraClass = "") {
  if (!on) return "";
  const klass = extraClass ? `flag ${extraClass}` : "flag";
  return `<span class="${klass}">${escapeHtml(label)}</span>`;
}

function jobQuery() {
  const params = new URLSearchParams();
  const q = $("filter-query").value.trim();
  const sort = $("sort").value;
  params.set("applied", "true");
  if (q) params.set("query", q);
  if (sort) params.set("sort", sort);
  params.set("page", String(currentPage));
  params.set("page_size", String(PAGE_SIZE));
  return `/api/v1/job/?${params.toString()}`;
}

function renderStats(stats) {
  const applied = stats.applied ?? 0;
  $("stat-applied").textContent = applied;
  $("stat-success").textContent = `${Math.round(stats.avg_success || 0)}%`;
  $("stat-remote").textContent = stats.remote ?? 0;
  $("stat-sponsor").textContent = stats.sponsorship ?? 0;
  $("stat-salary").textContent = stats.with_salary ?? 0;
  const badge = $("nav-applied-count");
  badge.textContent = applied ? String(applied) : "";
  badge.hidden = !applied;
}

function renderPager(page) {
  const pager = $("pager");
  const total = page.total || 0;
  if (!total) {
    pager.hidden = true;
    return;
  }
  pager.hidden = false;
  currentPage = page.page;
  $("page-info").textContent = `Page ${page.page} of ${page.pages} · ${total} applied`;
  $("page-prev").disabled = page.page <= 1;
  $("page-next").disabled = page.page >= page.pages;
}

function renderJobs(page) {
  const jobs = page.items || [];
  renderPager(page);
  if (!jobs.length) {
    jobsEl.innerHTML = `<p class="empty">You have not marked any roles as applied yet. Search, then tap I applied.</p>`;
    statusEl.textContent = "";
    return;
  }
  statusEl.textContent = `${page.total} applied ${page.total === 1 ? "role" : "roles"}.`;
  jobsEl.innerHTML = jobs
    .map((job) => {
      const url = job.url || "#";
      return `
      <article class="job applied-row" data-id="${job.id}">
        ${ringHtml(job.interview_success_rate)}
        <div>
          <h3><a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(job.title)}</a></h3>
          <p>${[job.company, job.location].filter(Boolean).map(escapeHtml).join(" · ")}</p>
          <div class="job-flags">
            ${flag(job.workplace_type, job.workplace_type && job.workplace_type !== "unknown")}
            ${flag("visa", job.sponsorship === "yes", "visa")}
            ${flag("no visa", job.sponsorship === "no")}
            ${flag("relocation help", job.relocation === "offered")}
            ${flag(job.salary_text, Boolean(job.salary_text))}
          </div>
        </div>
        <div class="job-actions">
          <a class="btn ghost" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Open LinkedIn</a>
          <button type="button" class="btn applied-btn" data-apply="${job.id}">
            <span class="spinner" aria-hidden="true"></span>
            <span>Undo applied</span>
          </button>
        </div>
      </article>`;
    })
    .join("");

  jobsEl.querySelectorAll("[data-apply]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      button.classList.add("loading");
      button.disabled = true;
      const res = await api(`/api/v1/job/${button.dataset.apply}/applied`, {
        method: "POST",
        body: JSON.stringify({ applied: false }),
      });
      if (!res.ok) {
        button.classList.remove("loading");
        button.disabled = false;
        return;
      }
      await loadJobs();
    });
  });
}

async function loadJobs() {
  jobsEl.innerHTML = `
    <div class="job skeleton"></div>
    <div class="job skeleton"></div>
    <div class="job skeleton"></div>
  `;
  const [statsRes, jobsRes] = await Promise.all([
    api("/api/v1/job/stats?applied=true"),
    api(jobQuery()),
  ]);
  if (statsRes.ok) renderStats(await statsRes.json());
  if (jobsRes.ok) {
    renderJobs(await jobsRes.json());
    return;
  }
  jobsEl.innerHTML = `<p class="empty">Could not load applied roles.</p>`;
}

["filter-query", "sort"].forEach((id) => {
  $(id).addEventListener("change", () => {
    currentPage = 1;
    loadJobs();
  });
  $(id).addEventListener("keyup", (event) => {
    if (event.key === "Enter") {
      currentPage = 1;
      loadJobs();
    }
  });
});

$("page-prev").addEventListener("click", () => {
  if (currentPage <= 1) return;
  currentPage -= 1;
  loadJobs();
});
$("page-next").addEventListener("click", () => {
  currentPage += 1;
  loadJobs();
});

loadJobs();
