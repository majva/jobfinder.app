const api = (path, options = {}) =>
  fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

const $ = (id) => document.getElementById(id);
const jobsEl = $("jobs");
const statusEl = $("status");
let keywordTags = [];
let seededFromCv = false;
let currentPage = 1;
let progressTimer = null;
const PAGE_SIZE = 10;
const SEARCH_TIPS = [
  "Checking LinkedIn public listings…",
  "Reading job details and salary clues…",
  "Scoring interview fit against your CV…",
  "Filtering to visa and work-permit roles…",
];

function setStatus(text, isError = false) {
  statusEl.textContent = text || "";
  statusEl.classList.toggle("busy", Boolean(text) && !isError);
  statusEl.style.color = isError ? "#d37a6a" : "";
}

function setButtonLoading(button, loading, labelId, idleText, busyText) {
  button.classList.toggle("loading", loading);
  button.disabled = loading;
  const label = $(labelId);
  if (label) label.textContent = loading ? busyText : idleText;
}

function setSearching(loading) {
  setButtonLoading($("search-btn"), loading, "search-label", "Find jobs", "Searching…");
  $("search-form").classList.toggle("form-busy", loading);
  $("search-progress").classList.toggle("hidden", !loading);
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  if (loading) {
    let i = 0;
    $("pager").hidden = true;
    $("progress-copy").textContent = SEARCH_TIPS[0];
    jobsEl.innerHTML = `
      <div class="job skeleton"></div>
      <div class="job skeleton"></div>
      <div class="job skeleton"></div>
    `;
    progressTimer = setInterval(() => {
      i = (i + 1) % SEARCH_TIPS.length;
      $("progress-copy").textContent = SEARCH_TIPS[i];
    }, 2800);
  }
}

function setUploading(loading) {
  setButtonLoading($("upload-btn"), loading, "upload-label", "Upload CV", "Reading CV…");
}

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

function chips(items, fallback = "None listed") {
  if (!items || !items.length) return `<span>${fallback}</span>`;
  return items.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function addKeyword(value) {
  const tag = String(value || "")
    .replaceAll(",", " ")
    .trim();
  if (!tag) return;
  if (keywordTags.some((item) => item.toLowerCase() === tag.toLowerCase())) return;
  keywordTags.push(tag);
  renderKeywordTags();
}

function removeKeyword(index) {
  keywordTags.splice(index, 1);
  renderKeywordTags();
  $("keyword-input").focus();
}

function renderKeywordTags() {
  $("keyword-tags").innerHTML = keywordTags
    .map(
      (tag, index) =>
        `<span class="tag">${escapeHtml(tag)}<button type="button" data-remove="${index}" aria-label="Remove ${escapeHtml(tag)}">×</button></span>`
    )
    .join("");
}

function renderSuggestions(tags) {
  const unused = (tags || []).filter(
    (tag) => !keywordTags.some((item) => item.toLowerCase() === tag.toLowerCase())
  );
  $("keyword-suggest").innerHTML = unused
    .slice(0, 8)
    .map((tag) => `<button type="button" data-add="${escapeHtml(tag)}">+ ${escapeHtml(tag)}</button>`)
    .join("");
}

function renderCv(cv, seedForm = false) {
  const empty = $("cv-empty");
  const card = $("cv-card");
  if (!cv) {
    empty.classList.remove("hidden");
    card.classList.add("hidden");
    return;
  }
  empty.classList.add("hidden");
  card.classList.remove("hidden");
  $("cv-file-name").textContent = cv.original_filename;
  $("cv-name").textContent = cv.full_name || "Candidate";
  $("cv-headline").textContent = cv.headline || (cv.titles || []).join(" · ") || "—";
  $("cv-location").textContent = cv.location || "—";
  $("cv-years").textContent = cv.years_experience ? `${cv.years_experience}+ years` : "—";
  $("cv-email").textContent = cv.email || "—";
  $("cv-skills").innerHTML = (cv.skills || [])
    .map((item) => `<button type="button" class="chip-add" data-add="${escapeHtml(item)}">${escapeHtml(item)}</button>`)
    .join("") || "<span>None listed</span>";
  renderSuggestions(cv.suggested_tags || cv.skills || []);
  if (seedForm) {
    keywordTags = (cv.suggested_tags || []).slice(0, 3);
    renderKeywordTags();
    fillPlaceFromCv(cv.location);
  }
}

function fillPlaceFromCv(location) {
  if ($("country").value || $("city").value) return;
  const parts = String(location || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length >= 2) {
    $("city").value = parts[0];
    $("country").value = parts[parts.length - 1];
  } else if (parts.length === 1) {
    $("country").value = parts[0];
  }
}

function renderStats(stats) {
  const applied = stats.applied ?? 0;
  $("stat-jobs").textContent = stats.jobs ?? 0;
  $("stat-applied").textContent = applied;
  $("stat-success").textContent = `${Math.round(stats.avg_success || 0)}%`;
  $("stat-remote").textContent = stats.remote ?? 0;
  $("stat-sponsor").textContent = stats.sponsorship ?? 0;
  $("stat-salary").textContent = stats.with_salary ?? 0;
  const badge = $("nav-applied-count");
  if (badge) {
    badge.textContent = applied ? String(applied) : "";
    badge.hidden = !applied;
  }
}

function renderJobs(page) {
  const jobs = page.items || [];
  renderPager(page);
  if (!jobs.length) {
    const visaOnly = $("sponsor-only").checked;
    jobsEl.innerHTML = visaOnly
      ? `<p class="empty">No visa-sponsorship roles in this list. Uncheck Visa sponsorship or search again.</p>`
      : `<p class="empty">No roles yet. Add a few tags and search LinkedIn.</p>`;
    return;
  }
  jobsEl.innerHTML = jobs
    .map((job) => {
      const url = job.url || "#";
      return `
      <article class="job${job.applied ? " applied-row" : ""}" data-id="${job.id}">
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
          <button type="button" class="btn ${job.applied ? "applied-btn" : "ghost"}" data-apply="${job.id}" data-applied="${job.applied ? "1" : "0"}">
            <span class="spinner" aria-hidden="true"></span>
            <span>${job.applied ? "Applied" : "I applied"}</span>
          </button>
        </div>
      </article>`;
    })
    .join("");

  jobsEl.querySelectorAll("[data-apply]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const id = button.dataset.apply;
      const next = button.dataset.applied !== "1";
      button.classList.add("loading");
      button.disabled = true;
      const res = await api(`/api/v1/job/${id}/applied`, {
        method: "POST",
        body: JSON.stringify({ applied: next }),
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

function renderPager(page) {
  const pager = $("pager");
  const total = page.total || 0;
  if (!total) {
    pager.hidden = true;
    return;
  }
  pager.hidden = false;
  currentPage = page.page;
  $("page-info").textContent = `Page ${page.page} of ${page.pages} · ${total} roles`;
  $("page-prev").disabled = page.page <= 1;
  $("page-next").disabled = page.page >= page.pages;
}

async function loadJobs() {
  const [statsRes, jobsRes] = await Promise.all([
    api("/api/v1/job/stats"),
    api(jobQuery()),
  ]);
  if (statsRes.ok) renderStats(await statsRes.json());
  if (jobsRes.ok) renderJobs(await jobsRes.json());
}

function resetSearchForm() {
  keywordTags = [];
  seededFromCv = false;
  currentPage = 1;
  renderKeywordTags();
  $("keyword-suggest").innerHTML = "";
  $("keyword-input").value = "";
  $("country").value = "";
  $("city").value = "";
  $("remote-only").checked = false;
  $("sponsor-only").checked = false;
  $("filter-query").value = "";
  $("filter-work").value = "";
  $("sort").value = "success";
  setStatus("");
  renderCv(null);
}

function jobQuery() {
  const params = new URLSearchParams();
  const q = $("filter-query").value.trim();
  const work = $("filter-work").value;
  const sort = $("sort").value;
  if (q) params.set("query", q);
  if (work) params.set("workplace_type", work);
  if (sort) params.set("sort", sort);
  if ($("sponsor-only").checked) params.set("immigration_only", "true");
  params.set("page", String(currentPage));
  params.set("page_size", String(PAGE_SIZE));
  const qs = params.toString();
  return `/api/v1/job/${qs ? `?${qs}` : ""}`;
}

$("keyword-box").addEventListener("click", (event) => {
  if (event.target.dataset.remove != null) {
    removeKeyword(Number(event.target.dataset.remove));
    return;
  }
  $("keyword-input").focus();
});

$("keyword-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === ",") {
    event.preventDefault();
    addKeyword(event.target.value);
    event.target.value = "";
  } else if (event.key === "Backspace" && !event.target.value && keywordTags.length) {
    removeKeyword(keywordTags.length - 1);
  }
});

$("keyword-input").addEventListener("blur", (event) => {
  if (event.target.value.trim()) {
    addKeyword(event.target.value);
    event.target.value = "";
  }
});

document.addEventListener("click", (event) => {
  const add = event.target.closest("[data-add]");
  if (!add) return;
  addKeyword(add.dataset.add);
  add.remove();
});

$("cv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  setUploading(true);
  setStatus("Reading CV…");
  try {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch("/api/v1/cv/upload", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.detail || "Could not parse this PDF.", true);
      return;
    }
    seededFromCv = false;
    renderCv(data, true);
    setStatus("CV parsed. Tweak the tags, then hit Find jobs.");
  } catch (error) {
    setStatus("Could not upload this CV.", true);
  } finally {
    setUploading(false);
    event.target.value = "";
  }
});

$("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if ($("keyword-input").value.trim()) {
    addKeyword($("keyword-input").value);
    $("keyword-input").value = "";
  }
  setSearching(true);
  setStatus("Searching LinkedIn…");
  try {
    const res = await api("/api/v1/job/search", {
      method: "POST",
      body: JSON.stringify({
        keywords: keywordTags,
        country: $("country").value || null,
        city: $("city").value || null,
        remote_only: $("remote-only").checked,
        sponsorship_only: $("sponsor-only").checked,
        posted_within_days: 30,
      }),
    });
    const data = await res.json();
    currentPage = 1;
    if (!res.ok) {
      jobsEl.innerHTML = `<p class="empty">Search failed. Try again in a moment.</p>`;
      setStatus(data.detail || "LinkedIn search failed.", true);
      return;
    }
    if (!data.jobs_found) {
      setStatus(data.hint || "No roles found for those tags.", true);
    } else {
      const place = [data.city, data.country || data.location].filter(Boolean).join(", ");
      const visaNote = $("sponsor-only").checked ? " with visa sponsorship" : "";
      setStatus(
        data.hint
        || `Found ${data.jobs_found} roles${visaNote} from the last 30 days${place ? ` in ${place}` : ""}.`
      );
    }
    await loadJobs();
  } catch (error) {
    jobsEl.innerHTML = `<p class="empty">Could not reach the API.</p>`;
    setStatus("Could not reach the API.", true);
  } finally {
    setSearching(false);
  }
});

["filter-query", "filter-work", "sort", "sponsor-only"].forEach((id) => {
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

resetSearchForm();
renderJobs({ items: [], total: 0, page: 1, page_size: PAGE_SIZE, pages: 1 });
api("/api/v1/job/stats").then(async (res) => {
  if (res.ok) renderStats(await res.json());
});
