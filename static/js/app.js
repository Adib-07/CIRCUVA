/* ==========================================================================
   Circuva — Core Frontend Controller
   All backend communication goes through window.Api (static/js/api.js).
   ========================================================================== */

let currentUser = null;
let currentToken = localStorage.getItem("circuva_token") || null;
let selectedReportId = null;
let charts = {};
let APP_META = null;
let activeViewName = "home";
let wizardFiles = [];
let wizardDefaults = { latitude: 42.3608, longitude: -71.0938, building: "Student Center — Main Campus" };
let currentAdminFilters = {};
let currentFacilityFilters = {};
let currentLiveFilters = {};

/* Local real photography per incident category (variety pool to avoid repeats). */
const CATEGORY_IMAGES = {
  overflowing_bin: ["/static/assets/images/cat-waste-1.jpg", "/static/assets/images/cat-waste-2.jpg", "/static/assets/images/cat-waste-3.jpg"],
  recycling_station: ["/static/assets/images/cat-recycling-1.jpg", "/static/assets/images/cat-recycling-2.jpg", "/static/assets/images/cat-recycling-3.jpg"],
  litter_outdoor: ["/static/assets/images/cat-litter-1.jpg", "/static/assets/images/cat-litter-2.jpg", "/static/assets/images/cat-litter-3.jpg"],
  illegal_dumping: ["/static/assets/images/cat-illegal-1.jpg", "/static/assets/images/cat-illegal-2.jpg", "/static/assets/images/cat-illegal-3.jpg"],
  plastic_waste: ["/static/assets/images/cat-plastic-1.jpg", "/static/assets/images/cat-plastic-2.jpg", "/static/assets/images/cat-plastic-3.jpg"],
  food_waste: ["/static/assets/images/cat-food-1.jpg", "/static/assets/images/cat-food-2.jpg", "/static/assets/images/cat-food-3.jpg"],
  e_waste: ["/static/assets/images/cat-ewaste-1.jpg", "/static/assets/images/cat-ewaste-2.jpg", "/static/assets/images/cat-ewaste-3.jpg"],
  broken_bins: ["/static/assets/images/cat-broken-1.jpg", "/static/assets/images/cat-broken-2.jpg", "/static/assets/images/cat-broken-3.jpg"]
};

function categoryImage(cat, seed) {
  const arr = CATEGORY_IMAGES[cat] || CATEGORY_IMAGES["overflowing_bin"];
  const s = String(seed == null ? cat : seed);
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return arr[h % arr.length];
}

const main = async () => {
  await loadMeta();
  initBeforeAfterSlider();
  initEventListeners();

  if (currentToken) {
    try {
      currentUser = await Api.me();
      updateUserUI();
    } catch (err) {
      logout();
    }
  }

  initCampusMap();
  initCampusView();
  loadLiveFeed();
  loadAnalytics();
  installImageFallback();
  hydrateMarketingStats();
  handleHashRoute();
};

/* Replace broken external images with a neutral placeholder so the UI
   never shows a broken-image icon if an asset fails to load. */
function installImageFallback() {
  document.addEventListener("error", (e) => {
    const t = e.target;
    if (t && t.tagName === "IMG" && !t.dataset.fallback) {
      t.dataset.fallback = "1";
      t.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect width='100%25' height='100%25' fill='%23e2e8f0'/></svg>";
    }
  }, true);
}

/* Keep the marketing / hero numbers consistent with the live demo dataset
   instead of showing hardcoded figures that contradict the dashboards. */
async function hydrateMarketingStats() {
  try {
    const o = await Api.overview();
    const hs = await Api.hotspots();
    const recurring = hs.filter((h) => (h.report_count || 0) >= 2).length;
    const contam = (o.by_category && o.by_category["Recycling Contamination"]) || 0;
    const rate = o.resolution_rate_pct != null ? o.resolution_rate_pct : "–";
    const avg = o.avg_response_hours != null ? o.avg_response_hours + "h" : "–";

    setText("heroActive", o.active_reports);
    setText("heroResolved", o.resolved_reports);
    setText("heroAvg", avg);
    setText("heroClean", rate);

    setText("livActive", o.total_reports);
    setText("livResolved", o.resolved_reports);
    setText("livHotspots", recurring);
    setText("livAvg", avg);
    setText("livContam", contam);
    setText("livClean", rate);

    const ring = document.getElementById("mScoreRing");
    if (ring) ring.style.setProperty("--val", rate);
    setText("mClean", rate);
    setText("mAvg", avg);
    setText("mRate", rate + (o.resolution_rate_pct != null ? "%" : ""));
    setText("mResolved", o.resolved_reports);
    setText("mTotal", o.total_reports);
  } catch (e) {
    /* Keep the default placeholders if the API is unavailable. */
  }
}

document.addEventListener("DOMContentLoaded", main);

function handleHashRoute() {
  const hash = window.location.hash.replace("#", "");
  if (["student", "admin", "facilities", "faculty", "liveimpact"].includes(hash)) {
    switchView(hash);
  }
}

/* ==========================================================================
   Meta / helpers
   ========================================================================== */

async function loadMeta() {
  try {
    APP_META = await Api.meta();
  } catch (err) {
    APP_META = null;
  }
}

function statusLabel(key) {
  if (APP_META && Array.isArray(APP_META.statuses)) {
    const f = APP_META.statuses.find((s) => s.key === key);
    if (f) return f.label;
  }
  return (key || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusStepIndex(key) {
  const order = ["submitted", "acknowledged", "assigned", "in_progress", "resolved"];
  if (key === "verified") return order.length;
  return order.indexOf(key);
}

function renderStatusStepper(currentStatus) {
  const steps = ["submitted", "acknowledged", "assigned", "in_progress", "resolved"];
  const verified = currentStatus === "verified";
  let idx = steps.indexOf(currentStatus);
  if (verified) idx = steps.length;

  let html = '<div class="status-stepper">';
  steps.forEach((s, i) => {
    let cls = "ss-step";
    if (i < idx) cls += " done";
    else if (i === idx && !verified) cls += " current";
    else if (verified && i === steps.length - 1) cls += " done";
    html += '<div class="' + cls + '"><div class="ss-dot"></div><div class="ss-label">' + escapeHtml(statusLabel(s)) + "</div></div>";
  });
  if (verified) {
    html += '<div class="ss-step current"><div class="ss-dot"></div><div class="ss-label">Verified</div></div>';
  }
  html += "</div>";
  return html;
}

function escapeHtml(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmtDate(s) {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d)) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function fmtDateTime(s) {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d)) return "—";
  return d.toLocaleString();
}

function statusBadge(status) {
  return '<span class="badge badge-' + escapeHtml(status) + '">' + escapeHtml(statusLabel(status)) + "</span>";
}

function severityBadge(sev) {
  return '<span class="badge badge-' + escapeHtml(sev) + '">' + escapeHtml(sev) + "</span>";
}

function stateRow(cols, type, msg) {
  return '<tr><td colspan="' + cols + '" class="state-cell state-' + type + '">' + escapeHtml(msg) + "</td></tr>";
}

function stateCard(type, msg) {
  return '<div class="state-card state-' + type + '">' + escapeHtml(msg) + "</div>";
}

function setText(id, val) {
  const e = document.getElementById(id);
  if (e) e.textContent = val;
}

/* ==========================================================================
   Authentication & Persona Switching
   ========================================================================== */

async function loginAsDemo(role) {
  try {
    const data = await Api.demoLogin(role);
    currentToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem("circuva_token", currentToken);
    updateUserUI();
    closeModal("loginModal");
    closeModal("demoModal");
    showToast("Logged in as " + currentUser.name + " (" + currentUser.role + ")", "success");

    if (role === "student") switchView("student");
    else if (role === "admin") switchView("admin");
    else if (role === "facilities" || role === "facility_worker") switchView("facilities");
    else if (role === "faculty") switchView("faculty");
  } catch (err) {
    showToast(err.message || "Failed to authenticate demo user", "error");
  }
}

function logout() {
  currentUser = null;
  currentToken = null;
  localStorage.removeItem("circuva_token");
  updateUserUI();
  switchView("home");
  showToast("Logged out successfully", "info");
}

function updateUserUI() {
  const userBtn = document.getElementById("navUserBtn");
  const loginBtn = document.getElementById("navLoginBtn");
  const logoutBtn = document.getElementById("navLogoutBtn");
  const demoBtn = document.getElementById("navDemoBtn");

  if (currentUser) {
    if (userBtn) {
      userBtn.style.display = "inline-flex";
      userBtn.innerHTML = "👤 " + escapeHtml(currentUser.name) + ' <span class="badge badge-low" style="margin-left:6px;">' + escapeHtml(currentUser.role) + "</span>";
    }
    if (loginBtn) loginBtn.style.display = "none";
    if (demoBtn) demoBtn.style.display = "none";
    if (logoutBtn) logoutBtn.style.display = "inline-flex";
    const impactEl = document.getElementById("userImpactScore");
    if (impactEl) impactEl.innerText = currentUser.impact_score || 0;
  } else {
    if (userBtn) userBtn.style.display = "none";
    if (loginBtn) loginBtn.style.display = "inline-flex";
    if (demoBtn) demoBtn.style.display = "inline-flex";
    if (logoutBtn) logoutBtn.style.display = "none";
  }
}

async function doLogin(event) {
  event.preventDefault();
  const form = document.getElementById("loginForm");
  const emailEl = document.getElementById("loginEmail");
  const passEl = document.getElementById("loginPassword");
  const errEl = document.getElementById("loginError");
  const submitBtn = document.getElementById("loginSubmit");

  errEl.hidden = true;
  errEl.textContent = "";

  const email = emailEl.value.trim();
  const password = passEl.value;

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errEl.textContent = "Please enter a valid email address.";
    errEl.hidden = false;
    return false;
  }
  if (!password) {
    errEl.textContent = "Please enter your password.";
    errEl.hidden = false;
    return false;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Signing in…";

  try {
    const data = await Api.login(email, password);
    currentToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem("circuva_token", currentToken);

    closeModal("loginModal");
    form.reset();
    updateUserUI();
    showToast("Welcome back, " + currentUser.name, "success");

    const role = currentUser.role;
    if (role === "student") switchView("student");
    else if (role === "admin") switchView("admin");
    else if (role === "facilities" || role === "facility_worker") switchView("facilities");
    else if (role === "faculty") switchView("faculty");
    else switchView("home");
  } catch (err) {
    errEl.textContent = err.message || "Incorrect email or password.";
    errEl.hidden = false;
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Sign in";
  }
  return false;
}

/* ==========================================================================
   Demo Mode persona selector UI
   ========================================================================== */

const FALLBACK_PERSONAS = [
  { role: "student", label: "Student Reporter", description: "Submit reports & verify cleanups", capabilities: [] },
  { role: "faculty", label: "Faculty / Staff", description: "Monitor campus issues nearby", capabilities: [] },
  { role: "facilities", label: "Facilities Team", description: "Execute tasks & upload after photos", capabilities: [] },
  { role: "admin", label: "Campus Admin", description: "Analytics, dispatch & hotspot intel", capabilities: [] }
];

async function renderPersonas() {
  const grid = document.getElementById("personaGrid");
  if (!grid) return;

  let personas = FALLBACK_PERSONAS;
  try {
    const data = await Api.personas();
    if (Array.isArray(data) && data.length) {
      const iconMap = { student: "🎓", faculty: "🧑‍🏫", facilities: "🧹", admin: "🏢" };
      personas = data.map((p) => ({ ...p, icon: iconMap[p.role] || "👤" }));
    }
  } catch (err) {
    /* use fallback */
  }

  grid.innerHTML = personas
    .map(
      (p) =>
        '<button class="hp-persona-card" onclick="loginAsDemo(\'' + p.role + '\')">' +
        '<span class="hp-persona-card__icon">' + (p.icon || "👤") + "</span>" +
        '<span class="hp-persona-card__label">' + escapeHtml(p.label) + "</span>" +
        '<span class="hp-persona-card__desc">' + escapeHtml(p.description || "") + "</span>" +
        '<span class="hp-persona-card__cta">Explore →</span>' +
        "</button>"
    )
    .join("");
}

/* ==========================================================================
   Navigation & View Switching
   ========================================================================== */

function switchView(viewName) {
  const views = ["homeView", "studentView", "adminView", "facilitiesView", "facultyView", "liveImpactView"];
  views.forEach((v) => {
    const el = document.getElementById(v);
    if (el) el.classList.remove("active");
  });

  document.querySelectorAll(".demo-nav-btn").forEach((b) => b.classList.remove("active"));

  const setActive = (id) => {
    const e = document.getElementById(id);
    if (e) e.classList.add("active");
  };

  if (viewName === "home") {
    setActive("homeView");
    setActive("btnViewHome");
    window.location.hash = "home";
  } else if (viewName === "student") {
    setActive("studentView");
    setActive("btnViewStudent");
    window.location.hash = "student";
    activeViewName = "student";
    loadStudentDashboard();
  } else if (viewName === "admin") {
    setActive("adminView");
    setActive("btnViewAdmin");
    window.location.hash = "admin";
    activeViewName = "admin";
    renderFilterBar("adminFilter", (p) => loadAdminReports(p));
    loadAdminDashboard();
  } else if (viewName === "facilities") {
    setActive("facilitiesView");
    setActive("btnViewFacilities");
    window.location.hash = "facilities";
    activeViewName = "facilities";
    renderFilterBar("facilityFilter", (p) => loadFacilityReports(p));
    loadFacilityDashboard();
  } else if (viewName === "faculty") {
    setActive("facultyView");
    setActive("btnViewFaculty");
    window.location.hash = "faculty";
    activeViewName = "faculty";
    loadFacultyDashboard();
  } else if (viewName === "liveimpact") {
    setActive("liveImpactView");
    setActive("btnViewLiveImpact");
    window.location.hash = "liveimpact";
    activeViewName = "liveimpact";
    renderFilterBar("liFilter", (p) => loadLiveRecent(p));
    loadLiveImpact();
  }

  if (viewName === "liveimpact") initLiveImpactMap();

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function refreshActive() {
  if (activeViewName === "admin") loadAdminDashboard();
  else if (activeViewName === "facilities") loadFacilityDashboard();
  else if (activeViewName === "student") loadStudentDashboard();
  else if (activeViewName === "faculty") loadFacultyDashboard();
  else if (activeViewName === "liveimpact") loadLiveImpact();
}

/* ==========================================================================
   Interactive Campus Map (self-contained SVG — no external/network deps)
   ========================================================================== */

let hotspotMap = null;
const campusMaps = {};

function categoryGroup(cat) {
  if (!cat) return "waste";
  const c = String(cat).toLowerCase();
  if (c.includes("water") || c.includes("leak") || c.includes("drain")) return "water";
  if (c.includes("energy") || c.includes("e-waste") || c.includes("power") || c.includes("light")) return "energy";
  if (c.includes("recycl") || c.includes("clean") || c.includes("litter")) return "cleanliness";
  if (c.includes("broken") || c.includes("infrastructure") || c.includes("bin")) return "infrastructure";
  return "waste"; // overflowing bins, illegal dumping, plastic, food, etc.
}

function initCampusMap() {
  const el = document.getElementById("campusMap");
  if (!el || typeof CampusMap === "undefined") return;
  hotspotMap = CampusMap.mount({ target: "campusMap", legend: true });
  setupMapFilters();
}

function initCampusView() {
  const el = document.getElementById("campusView");
  if (!el || typeof CampusMap === "undefined") return;
  CampusMap.mount({ target: "campusView", legend: true });
}

function initLiveImpactMap() {
  const el = document.getElementById("liveImpactMap");
  if (!el || typeof CampusMap === "undefined" || campusMaps.liveImpactMap) return;
  campusMaps.liveImpactMap = CampusMap.mount({ target: "liveImpactMap", legend: true });
}

function setupMapFilters() {
  const wrap = document.getElementById("mapFilters");
  if (!wrap || wrap.dataset.wired) return;
  wrap.dataset.wired = "1";
  wrap.querySelectorAll(".map-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      wrap.querySelectorAll(".map-filter").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      if (hotspotMap) hotspotMap.setFilter(btn.dataset.filter);
    });
  });
}

function addIncidentToMaps(report) {
  if (!report) return;
  const inc = {
    id: "rep-" + (report.id != null ? report.id : Date.now()),
    title: report.category || "New report",
    location: report.building || "Campus",
    status: report.status || "reported",
    severity: report.severity || "Medium",
    group: categoryGroup(report.category),
    team: "Ops Crew",
    reported: "Just now",
    desc: report.description || "Newly submitted campus environmental report.",
    photo: (report.images && report.images.length ? report.images[0].image_url : categoryImage(report.category, report.id || Date.now()))
  };
  if (hotspotMap) hotspotMap.addIncident(inc);
  if (campusMaps.liveImpactMap) campusMaps.liveImpactMap.addIncident(inc);
}

/* ==========================================================================
   Report Wizard (single-form)
   ========================================================================== */

let wizardCategory = "Overflowing Bin";
let wizardSeverity = "high";
let wizardStep = 1;

async function openReportWizard() {
  if (!currentUser || !currentToken) {
    await loginAsDemo("student");
  }
  resetWizardForm();
  openModal("reportWizardModal");
}

function resetWizardForm() {
  wizardFiles = [];
  renderThumbs();
  clearWizardErrors();

  const catGrid = document.querySelector("#wizardStep1 .category-grid");
  if (catGrid) {
    const cards = catGrid.querySelectorAll(".category-card-opt");
    cards.forEach((c, i) => c.classList.toggle("selected", i === 0));
  }
  wizardCategory = "Overflowing Bin";

  wizardSeverity = "high";
  document.querySelectorAll("#wizardStep3 .severity-btn").forEach((b) => {
    b.classList.toggle("selected", (b.getAttribute("data-sev") || "").toLowerCase() === "high");
  });

  const bld = document.getElementById("reportBuildingSelect");
  if (bld) bld.selectedIndex = 0;
  const desc = document.getElementById("reportDescInput");
  if (desc) desc.value = "";
  const file = document.getElementById("reportFileInput");
  if (file) file.value = "";

  setWizardStep(1);
}

function selectCategory(category, el) {
  wizardCategory = category;
  if (el && el.parentElement) {
    el.parentElement.querySelectorAll(".category-card-opt").forEach((c) => c.classList.remove("selected"));
    el.classList.add("selected");
  }
  setWizardError("wizardIssueError", "");
}

function selectSeverity(severity, el) {
  wizardSeverity = (severity || "medium").toLowerCase();
  if (el && el.parentElement) {
    el.parentElement.querySelectorAll(".severity-btn").forEach((b) => b.classList.remove("selected"));
    el.classList.add("selected");
  }
}

function setWizardStep(step) {
  wizardStep = step;
  for (let i = 1; i <= 5; i++) {
    const s = document.getElementById("wizardStep" + i);
    if (s) s.style.display = i === step ? "block" : "none";
    const h = document.getElementById("stepHead" + i);
    if (h) h.classList.toggle("active", i <= step);
  }
  const back = document.getElementById("wizardBackBtn");
  const next = document.getElementById("wizardNextBtn");
  const submit = document.getElementById("wizardSubmitBtn");
  if (back) back.style.display = step > 1 && step < 5 ? "inline-flex" : "none";
  if (next) next.style.display = step < 4 ? "inline-flex" : "none";
  if (submit) submit.style.display = step === 4 ? "inline-flex" : "none";
}

function wizardGo(dir) {
  setWizardStep(Math.min(5, Math.max(1, wizardStep + dir)));
}

function clearWizardErrors() {
  /* No inline error elements in the current wizard DOM; validation uses toasts. */
}

function setWizardError(id, msg) {
  const e = document.getElementById(id);
  if (e) e.textContent = msg;
}

function useCurrentLocationGPS() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        wizardDefaults.latitude = pos.coords.latitude;
        wizardDefaults.longitude = pos.coords.longitude;
        showToast("GPS Position Locked (" + pos.coords.latitude.toFixed(4) + ", " + pos.coords.longitude.toFixed(4) + ")", "success");
      },
      () => showToast("Geolocation unavailable. Using default campus building coordinates.", "info")
    );
  }
}

async function handlePhotoUpload(event) {
  const files = event.target.files;
  if (!files || !files.length) return;
  for (const file of files) {
    wizardFiles.push({ file, url: null, status: "uploading" });
  }
  event.target.value = "";
  renderThumbs();
  for (const entry of wizardFiles) {
    if (entry.status !== "uploading") continue;
    try {
      const data = await Api.upload(entry.file);
      entry.url = data.image_url;
      entry.status = "done";
    } catch (e) {
      entry.status = "error";
    }
  }
  renderThumbs();
}

function renderThumbs() {
  const box = document.getElementById("uploadPreviewBox");
  if (!box) return;
  box.innerHTML = wizardFiles
    .map((e, i) => {
      if (e.status === "uploading")
        return '<div class="thumb thumb--loading"><div class="thumb-spinner"></div><button type="button" class="thumb-remove" onclick="removeWizardFile(' + i + ')">×</button></div>';
      if (e.status === "error")
        return '<div class="thumb thumb--error">✕<button type="button" class="thumb-remove" onclick="removeWizardFile(' + i + ')">×</button></div>';
      return '<div class="thumb"><img src="' + encodeURI(e.url) + '" alt=""><button type="button" class="thumb-remove" onclick="removeWizardFile(' + i + ')">×</button></div>';
    })
    .join("");
}

function removeWizardFile(i) {
  wizardFiles.splice(i, 1);
  renderThumbs();
}

async function submitReport() {
  clearWizardErrors();
  const buildingEl = document.getElementById("reportBuildingSelect");
  const location = buildingEl ? buildingEl.value.trim() : "";
  const descEl = document.getElementById("reportDescInput");
  const desc = descEl ? descEl.value.trim() : "";

  let ok = true;
  if (!wizardCategory) {
    showToast("Please select an issue type.", "error");
    ok = false;
  }
  if (!location) {
    showToast("Please select a location.", "error");
    ok = false;
  }
  if (!desc) {
    showToast("Please describe the issue.", "error");
    ok = false;
  }
  if (!ok) return;

  const imageUrls = wizardFiles.filter((f) => f.status === "done" && f.url).map((f) => f.url);
  const btn = document.getElementById("wizardSubmitBtn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Submitting…";
  }

  try {
    const data = {
      category: wizardCategory,
      description: desc,
      building: location,
      latitude: wizardDefaults.latitude,
      longitude: wizardDefaults.longitude,
      severity: wizardSeverity,
      additional_info: undefined,
      campus_id: 1
    };
    const rep = await Api.createReport(data, imageUrls);
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Submit Report";
    }

    const codeEl = document.getElementById("submittedReportCode");
    if (codeEl) codeEl.textContent = rep.report_code;
    const sum = document.getElementById("wizardSummaryBox");
    if (sum) {
      sum.innerHTML =
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">' +
        '<div><span class="hp-mini__label">Category</span><br><strong>' + escapeHtml(rep.category) + "</strong></div>" +
        '<div><span class="hp-mini__label">Location</span><br><strong>' + escapeHtml(rep.building || "") + "</strong></div>" +
        '<div><span class="hp-mini__label">Severity</span><br><strong>' + escapeHtml(rep.severity) + "</strong></div>" +
        '<div><span class="hp-mini__label">Status</span><br>' + statusBadge(rep.status) + "</div>" +
        "</div>";
    }

    setWizardStep(5);
    addIncidentToMaps(rep);
    refreshActive();
  } catch (e) {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Submit Report";
    }
    showToast(e.message || "Failed to submit report.", "error");
  }
}

/* ==========================================================================
   Dashboards
   ========================================================================== */

async function loadStudentDashboard() {
  const tbody = document.getElementById("studentReportsTbody");
  if (!tbody) return;
  const impactEl = document.getElementById("userImpactScore");
  tbody.innerHTML = stateRow(7, "loading", "Loading your reports…");

  try {
    const reports = await Api.reports();
    const mine = currentUser ? reports.filter((r) => r.user_id === currentUser.id) : reports;
    const total = mine.length;
    const resolved = mine.filter((r) => r.status === "resolved" || r.status === "verified").length;
    const inprog = mine.filter((r) => ["acknowledged", "assigned", "in_progress"].includes(r.status)).length;
    setText("stuTotal", total);
    setText("stuResolved", resolved);
    setText("stuInProgress", inprog);
    if (impactEl) impactEl.innerText = currentUser ? currentUser.impact_score || 0 : 0;

    if (mine.length === 0) {
      tbody.innerHTML = stateRow(7, "empty", "No reports submitted yet.");
      return;
    }
    tbody.innerHTML = mine
      .map(
        (r) =>
          "<tr>" +
          "<td><strong>" + escapeHtml(r.report_code) + "</strong></td>" +
          "<td>" + escapeHtml(r.category) + "</td>" +
          "<td>" + escapeHtml(r.building || "") + "</td>" +
          "<td>" + severityBadge(r.severity) + "</td>" +
          "<td>" + statusBadge(r.status) + "</td>" +
          "<td>" + fmtDate(r.created_at) + "</td>" +
          "<td>" + studentActions(r) + "</td>" +
          "</tr>"
      )
      .join("");
  } catch (e) {
    tbody.innerHTML = stateRow(7, "error", "Failed to load reports.");
  }
}

async function loadFacultyDashboard() {
  const tbody = document.getElementById("facultyReportsTbody");
  if (!tbody) return;
  tbody.innerHTML = stateRow(5, "loading", "Loading campus reports…");

  try {
    const reports = await Api.reports();
    const total = reports.length;
    const resolved = reports.filter((r) => r.status === "resolved" || r.status === "verified").length;
    const critical = reports.filter((r) => r.severity === "critical").length;
    setText("facTotal", total);
    setText("facResolved", resolved);
    setText("facCritical", critical);
    setText("facNearby", Math.max(0, total - resolved));

    const recent = [...reports].sort((a, b) => (b.id || 0) - (a.id || 0)).slice(0, 8);
    tbody.innerHTML = recent.length
      ? recent
          .map(
            (r) =>
              "<tr>" +
              "<td><strong>" + escapeHtml(r.report_code) + "</strong></td>" +
              "<td>" + escapeHtml(r.category) + "</td>" +
              "<td>" + escapeHtml(r.building || "") + "</td>" +
              "<td>" + severityBadge(r.severity) + "</td>" +
              "<td>" + statusBadge(r.status) + "</td>" +
              "</tr>"
          )
          .join("")
      : stateRow(5, "empty", "No reports.");

    const nearby = reports.filter((r) => r.status !== "resolved" && r.status !== "verified").slice(0, 3);
    const nel = document.getElementById("facultyNearbyList");
    if (nel)
      nel.innerHTML = nearby.length
        ? nearby
            .map(
              (r) =>
                '<div class="hp-nearby-item">' +
                '<span class="badge badge-' + r.severity + '">' + escapeHtml(r.severity) + "</span>" +
                "<div>" +
                '<div style="font-weight:600;">' + escapeHtml(r.building || "") + "</div>" +
                '<div style="font-size:12px; color:var(--color-slate-500);">' + escapeHtml(r.category) + " · " + escapeHtml(r.report_code) + "</div>" +
                "</div>" +
                "</div>"
            )
            .join("")
        : '<p style="font-size:13px; color:var(--color-slate-500);">No open issues right now. 🎉</p>';
  } catch (e) {
    tbody.innerHTML = stateRow(5, "error", "Failed to load campus reports.");
  }
}

async function loadAdminDashboard() {
  try {
    const o = await Api.overview();
    setText("admTotal", o.total_reports);
    setText("admActive", o.active_reports);
    setText("admCritical", o.critical_reports);
    setText("admRate", o.resolution_rate_pct != null ? o.resolution_rate_pct + "%" : "—");
    setText("admAvg", o.avg_response_hours != null ? o.avg_response_hours + "h" : "—");
    setText("admImpact", o.user_impact_score != null ? o.user_impact_score : "—");
  } catch (e) { /* ignore */ }

  try {
    const h = await Api.hotspots();
    renderHotspots("adminHotspots", h, false);
  } catch (e) { /* ignore */ }

  try {
    const a = await Api.activity();
    renderActivity("liveIncidentFeed", a);
  } catch (e) { /* ignore */ }

  try {
    const c = await Api.charts();
    renderAdminCharts(c);
  } catch (e) { /* ignore */ }

  loadAdminReports(currentAdminFilters || {});
}

async function loadAdminReports(params) {
  const tbody = document.getElementById("adminReportsTbody");
  if (!tbody) return;
  currentAdminFilters = params || {};
  tbody.innerHTML = stateRow(7, "loading", "Loading incidents…");

  try {
    const reports = await Api.reports(params);
    if (!reports.length) {
      tbody.innerHTML = stateRow(7, "empty", "No incidents match the filters.");
      return;
    }
    tbody.innerHTML = reports
      .map(
        (r) =>
          "<tr>" +
          "<td><strong>" + escapeHtml(r.report_code) + "</strong></td>" +
          "<td>" + escapeHtml(r.category) + "</td>" +
          "<td>" + escapeHtml(r.building || "") + "</td>" +
          "<td>" + severityBadge(r.severity) + "</td>" +
          "<td>" + statusBadge(r.status) + "</td>" +
          "<td>" + escapeHtml(r.reporter_name || "—") + "</td>" +
          "<td>" + adminActions(r) + "</td>" +
          "</tr>"
      )
      .join("");
  } catch (e) {
    tbody.innerHTML = stateRow(7, "error", "Failed to load incidents.");
  }
}

async function loadFacilityDashboard() {
  const container = document.getElementById("facilityTasksContainer");
  if (!container) return;
  container.innerHTML = stateCard("loading", "Loading tasks…");

  try {
    const reports = await Api.reports();
    const incoming = reports.filter((r) => ["submitted", "acknowledged", "assigned", "in_progress"].includes(r.status));
    setText("facIncoming", incoming.length);
  } catch (e) { /* ignore */ }

  loadFacilityReports(currentFacilityFilters || {});
}

async function loadFacilityReports(params) {
  const container = document.getElementById("facilityTasksContainer");
  if (!container) return;
  currentFacilityFilters = params || {};
  container.innerHTML = stateCard("loading", "Loading tasks…");

  try {
    const reports = await Api.reports(params);
    if (!reports.length) {
      container.innerHTML = stateCard("empty", "🎉 No tasks match the filters.");
      return;
    }
    container.innerHTML = reports
      .map(
        (r) =>
          '<div class="card report-card">' +
          '<div class="report-card__head">' +
          '<div><strong class="report-card__code">' + escapeHtml(r.report_code) + "</strong> <span class=\"report-card__cat\">" + escapeHtml(r.category) + "</span></div>" +
          statusBadge(r.status) +
          "</div>" +
          '<div class="report-card__meta">' +
          "<span>📍 " + escapeHtml(r.building || "") + "</span>" +
          severityBadge(r.severity) +
          '<span class="report-card__time">' + fmtDate(r.created_at) + "</span>" +
          "</div>" +
          (r.description ? '<p class="report-card__desc">' + escapeHtml(r.description) + "</p>" : "") +
          (r.images && r.images.length
            ? '<img class="report-card__img" src="' + encodeURI(r.images[0].image_url) + '" alt="evidence photo" loading="lazy">'
            : '<img class="report-card__img" src="' + categoryImage(r.category, r.id) + '" alt="' + escapeHtml(r.category) + '" loading="lazy">') +
          renderStatusStepper(r.status) +
          '<div class="report-card__actions">' + facilityActions(r) + "</div>" +
          "</div>"
      )
      .join("");
  } catch (e) {
    container.innerHTML = stateCard("error", "Failed to load tasks.");
  }
}

async function loadLiveImpact() {
  const mEl = document.getElementById("liMetrics");
  if (!mEl) return;
  mEl.innerHTML = stateCard("loading", "Loading impact metrics…");

  try {
    const o = await Api.overview();
    mEl.innerHTML =
      '<div class="metric-card"><div class="metric-label">Current Reports</div><div class="metric-val">' + o.total_reports + "</div></div>" +
      '<div class="metric-card"><div class="metric-label">Active</div><div class="metric-val" style="color:var(--color-amber-500);">' + o.active_reports + "</div></div>" +
      '<div class="metric-card"><div class="metric-label">Resolved</div><div class="metric-val" style="color:var(--color-emerald-600);">' + o.resolved_reports + "</div></div>" +
      '<div class="metric-card"><div class="metric-label">Resolution Rate</div><div class="metric-val">' + (o.resolution_rate_pct != null ? o.resolution_rate_pct + "%" : "—") + "</div></div>" +
      '<div class="metric-card"><div class="metric-label">Avg Response</div><div class="metric-val">' + (o.avg_response_hours != null ? o.avg_response_hours + "h" : "—") + "</div></div>";
  } catch (e) {
    mEl.innerHTML = stateCard("error", "Failed to load metrics.");
  }

  try {
    const h = await Api.hotspots();
    renderHotspots("liHotspots", h, false);
  } catch (e) { /* ignore */ }

  try {
    const a = await Api.activity();
    renderActivity("liActivity", a);
  } catch (e) { /* ignore */ }

  try {
    const c = await Api.charts();
    renderLiveCharts(c);
  } catch (e) { /* ignore */ }

  loadLiveRecent(currentLiveFilters || {});
  initLiveImpactMap();
}

async function loadLiveRecent(params) {
  const el = document.getElementById("liRecent");
  if (!el) return;
  currentLiveFilters = params || {};
  el.innerHTML = stateCard("loading", "Loading reports…");

  try {
    const reports = await Api.reports(params);
    if (!reports.length) {
      el.innerHTML = stateCard("empty", "No reports match the filters.");
      return;
    }
    el.innerHTML = reports
      .slice(0, 12)
      .map(
        (r) =>
          '<div class="report-card">' +
          '<div class="report-card__head">' +
          '<div><strong class="report-card__code">' + escapeHtml(r.report_code) + "</strong> <span class=\"report-card__cat\">" + escapeHtml(r.category) + "</span></div>" +
          statusBadge(r.status) +
          "</div>" +
          '<div class="report-card__meta">' +
          "<span>📍 " + escapeHtml(r.building || "") + "</span>" +
          severityBadge(r.severity) +
          '<span class="report-card__time">' + fmtDate(r.created_at) + "</span>" +
          "</div>" +
          (r.images && r.images.length
            ? '<img class="report-card__img" src="' + encodeURI(r.images[0].image_url) + '" alt="evidence photo" loading="lazy">'
            : '<img class="report-card__img" src="' + categoryImage(r.category, r.id) + '" alt="' + escapeHtml(r.category) + '" loading="lazy">') +
          renderStatusStepper(r.status) +
          "</div>"
      )
      .join("");
  } catch (e) {
    el.innerHTML = stateCard("error", "Failed to load reports.");
  }
}

async function loadLiveFeed() {
  try {
    const a = await Api.activity();
    renderActivity("liveIncidentFeed", a);
  } catch (e) { /* ignore */ }
}

async function loadAnalytics() {
  try {
    const c = await Api.charts();
    renderAdminCharts(c);
  } catch (e) { /* ignore */ }
}

/* ==========================================================================
   Charts
   ========================================================================== */

 function renderChart(id, type, data, options) {
   const el = document.getElementById(id);
   if (!el) return;
   if (typeof CircuvaCharts !== "undefined") {
     CircuvaCharts.render(id, type, data, options);
     return;
   }
   /* final fallback: leave canvas hidden rather than throwing */
   el.style.display = "none";
 }

function renderAdminCharts(c) {
  if (!c) return;
  renderChart(
    "chartCategories",
    "bar",
    { labels: c.categories.labels, datasets: [{ label: "Reports", data: c.categories.data, backgroundColor: "#059669", borderRadius: 6 }] },
    { plugins: { legend: { display: false } } }
  );
  renderChart(
    "chartSeverity",
    "doughnut",
    { labels: c.severity.labels, datasets: [{ data: c.severity.data, backgroundColor: ["#ef4444", "#f59e0b", "#3b82f6", "#64748b"] }] },
    {}
  );
  renderChart(
    "chartWeekly",
    "line",
    {
      labels: c.weekly_trend.labels,
      datasets: [
        { label: "Reported", data: c.weekly_trend.reported, borderColor: "#ef4444", tension: 0.3 },
        { label: "Resolved", data: c.weekly_trend.resolved, borderColor: "#10b981", tension: 0.3 }
      ]
    },
    {}
  );
}

function renderLiveCharts(c) {
  if (!c) return;
  renderChart(
    "liCategoryChart",
    "bar",
    { labels: c.categories.labels, datasets: [{ label: "Reports", data: c.categories.data, backgroundColor: "#059669", borderRadius: 6 }] },
    { plugins: { legend: { display: false } } }
  );
  renderChart(
    "liSeverityChart",
    "doughnut",
    { labels: c.severity.labels, datasets: [{ data: c.severity.data, backgroundColor: ["#ef4444", "#f59e0b", "#3b82f6", "#64748b"] }] },
    {}
  );
  renderChart(
    "liTrendChart",
    "line",
    {
      labels: c.weekly_trend.labels,
      datasets: [
        { label: "Reported", data: c.weekly_trend.reported, borderColor: "#ef4444", tension: 0.3 },
        { label: "Resolved", data: c.weekly_trend.resolved, borderColor: "#10b981", tension: 0.3 }
      ]
    },
    {}
  );
}

/* ==========================================================================
   Hotspots & Activity renderers
   ========================================================================== */

function renderHotspots(containerId, hotspots, compact) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!hotspots || !hotspots.length) {
    el.innerHTML = stateCard("empty", "No hotspots recorded.");
    return;
  }
  el.innerHTML = hotspots
    .map((h) => {
      const types = (h.issue_types || []).map((t) => '<span class="chip">' + escapeHtml(t) + "</span>").join("");
      const rate = h.resolution_rate_pct != null ? h.resolution_rate_pct : 0;
      return (
        '<div class="hotspot-card">' +
        '<div class="hotspot-card__head"><strong>' + escapeHtml(h.building) + "</strong>" +
        '<span class="hotspot-count">' + h.report_count + " report" + (h.report_count !== 1 ? "s" : "") + "</span></div>" +
        '<div class="hotspot-chips">' + (types || '<span class="chip">—</span>') + "</div>" +
        '<div class="hotspot-meta">Last: ' + fmtDate(h.last_report_at) + " · " + statusBadge(h.latest_status || "") + "</div>" +
        '<div class="progress"><div class="progress-bar" style="width:' + rate + '%;"></div></div>' +
        '<div class="hotspot-rate">Resolution rate: ' + rate + "%</div>" +
        "</div>"
      );
    })
    .join("");
}

function renderActivity(containerId, items) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!items || !items.length) {
    el.innerHTML = stateCard("empty", "No recent activity.");
    return;
  }
  el.innerHTML = items
    .map(
      (it) =>
        '<div class="activity-item"><span class="pulse-dot"></span>' +
        '<div class="activity-body">' +
        '<div class="activity-msg">' + escapeHtml(it.message) + "</div>" +
        '<div class="activity-meta">' + escapeHtml(it.report_code || "") + " · " + fmtDateTime(it.timestamp) + "</div>" +
        "</div></div>"
    )
    .join("");
}

/* ==========================================================================
   Action buttons (role-aware)
   ========================================================================== */

function studentActions(r) {
  let a = "";
  if (r.status === "resolved") a += '<button class="btn btn-sm btn-primary" onclick="openVerificationModal(' + r.id + ')">Verify Fix</button>';
  if (r.status === "verified") a += '<span class="badge badge-verified">Verified ✓</span>';
  a += '<button class="btn btn-sm btn-secondary" onclick="openReportModal(' + r.id + ')">Details</button>';
  return a;
}

function adminActions(r) {
  let a = "";
  if (r.status === "submitted") a += '<button class="btn btn-sm btn-primary" onclick="uiAcknowledge(' + r.id + ')">Acknowledge</button>';
  a += '<button class="btn btn-sm btn-secondary" onclick="uiAssign(' + r.id + ')">Assign</button>';
  a += '<button class="btn btn-sm btn-secondary" onclick="uiSetStatusPrompt(' + r.id + ')">Set Status</button>';
  if (["in_progress", "assigned", "acknowledged", "submitted"].includes(r.status))
    a += '<button class="btn btn-sm btn-primary" onclick="uiResolve(' + r.id + ')">Resolve</button>';
  if (r.status === "resolved") a += '<button class="btn btn-sm btn-outline" onclick="uiVerify(' + r.id + ', true)">Verify</button>';
  a += '<button class="btn btn-sm btn-ghost" onclick="openReportModal(' + r.id + ')">Details</button>';
  return a;
}

function facilityActions(r) {
  let a = "";
  if (r.status === "submitted") a += '<button class="btn btn-sm btn-primary" onclick="uiAcknowledge(' + r.id + ')">Acknowledge</button>';
  a += '<button class="btn btn-sm btn-secondary" onclick="uiSetStatusPrompt(' + r.id + ')">Set Status</button>';
  if (["assigned", "in_progress", "acknowledged", "submitted"].includes(r.status))
    a += '<button class="btn btn-sm btn-primary" onclick="uiResolve(' + r.id + ')">Resolve</button>';
  a += '<button class="btn btn-sm btn-ghost" onclick="openReportModal(' + r.id + ')">Details</button>';
  return a;
}

async function uiAcknowledge(id) {
  try {
    await Api.acknowledge(id);
    showToast("Report acknowledged", "success");
    refreshActive();
  } catch (e) {
    showToast(e.message || "Failed to acknowledge", "error");
  }
}

async function uiAssign(id) {
  selectedReportId = id;
  const sel = document.getElementById("dispatchWorkerSelect");
  if (sel) {
    try {
      const users = await Api.users("facilities");
      sel.innerHTML = users.map((u) => '<option value="' + u.id + '">' + escapeHtml(u.name) + " (" + escapeHtml(u.role) + ")</option>").join("");
    } catch (e) {
      /* keep defaults */
    }
  }
  openModal("dispatchModal");
}

async function submitDispatch() {
  const sel = document.getElementById("dispatchWorkerSelect");
  const workerId = sel ? Number(sel.value) : null;
  if (!workerId) {
    showToast("Select a worker", "error");
    return;
  }
  try {
    await Api.assign(selectedReportId, { worker_id: workerId, notes: "Dispatched via dashboard" });
    closeModal("dispatchModal");
    showToast("Task dispatched", "success");
    refreshActive();
  } catch (e) {
    showToast(e.message || "Dispatch failed", "error");
  }
}

function uiSetStatusPrompt(id) {
  selectedReportId = id;
  const sel = document.getElementById("setStatusSelect");
  if (sel && APP_META) {
    sel.innerHTML = (APP_META.statuses || []).map((s) => '<option value="' + s.key + '">' + escapeHtml(s.label) + "</option>").join("");
  }
  openModal("setStatusModal");
}

async function uiApplyStatus() {
  const sel = document.getElementById("setStatusSelect");
  const status = sel ? sel.value : null;
  if (!status) {
    showToast("Select a status", "error");
    return;
  }
  try {
    await Api.setStatus(selectedReportId, status);
    closeModal("setStatusModal");
    showToast("Status updated", "success");
    refreshActive();
  } catch (e) {
    showToast(e.message || "Failed to update status", "error");
  }
}

function uiResolve(id) {
  selectedReportId = id;
  openModal("resolveTaskModal");
}

async function submitWorkerResolution() {
  const notes = document.getElementById("resolutionNotesInput") ? document.getElementById("resolutionNotesInput").value : "";
  const fileEl = document.getElementById("resolutionAfterFile");
  let afterUrl = undefined;
  if (fileEl && fileEl.files && fileEl.files.length) {
    try {
      const up = await Api.upload(fileEl.files[0]);
      afterUrl = up.image_url;
    } catch (e) {
      /* fall back to default after-photo on the backend */
    }
  }
  try {
    await Api.resolve(selectedReportId, { resolution_notes: notes || "", after_image_url: afterUrl });
    closeModal("resolveTaskModal");
    showToast("Marked resolved", "success");
    refreshActive();
  } catch (e) {
    showToast(e.message || "Failed to resolve", "error");
  }
}

async function uiVerify(id, verified) {
  try {
    await Api.verify(id, { verified: !!verified, feedback: "" });
    showToast(verified ? "Verified ✓" : "Reopened", "success");
    refreshActive();
  } catch (e) {
    showToast(e.message || "Failed to verify", "error");
  }
}

function openVerificationModal(reportId) {
  selectedReportId = reportId;
  openModal("verificationModal");
}

async function submitVerification(isVerified) {
  const feedback = document.getElementById("verifyFeedbackInput") ? document.getElementById("verifyFeedbackInput").value : "";
  try {
    await Api.verify(selectedReportId, { verified: isVerified, feedback: feedback || "" });
    closeModal("verificationModal");
    showToast(isVerified ? "Verified! +10 impact points" : "Reopened", "success");
    loadStudentDashboard();
  } catch (e) {
    showToast(e.message || "Failed to verify", "error");
  }
}

async function openReportModal(reportId) {
  selectedReportId = reportId;
  const modal = document.getElementById("reportDetailsModal");
  const body = document.getElementById("reportDetailsBody");
  if (!modal || !body) return;
  body.innerHTML = '<p class="state-cell">Loading…</p>';
  openModal("reportDetailsModal");

  try {
    const r = await Api.report(reportId);
    const hasImg = r.images && r.images.length;
    const hasRes = r.resolutions && r.resolutions.length;
    body.innerHTML =
      '<div class="report-detail">' +
      '<div class="report-detail__head"><h2>' + escapeHtml(r.category) + "</h2>" + statusBadge(r.status) + "</div>" +
      '<p class="report-detail__sub">Code: ' + escapeHtml(r.report_code) + " · Reporter: " + escapeHtml(r.reporter_name || "—") + " · 📍 " + escapeHtml(r.building || "") + "</p>" +
      renderStatusStepper(r.status) +
      '<div class="report-detail__media">' +
      "<div><h4>Evidence</h4>" + (hasImg ? '<img src="' + encodeURI(r.images[0].image_url) + '" alt="Report evidence photo">' : '<div class="placeholder">No photo</div>') + "</div>" +
      "<div><h4>Resolution</h4>" + (hasRes ? '<img src="' + encodeURI(r.resolutions[0].after_image_url || "") + '" alt="Resolution proof photo">' : '<div class="placeholder">Pending</div>') + "</div>" +
      "</div>" +
      "<p><strong>Description:</strong> " + escapeHtml(r.description || "") + "</p>" +
      (r.additional_info ? "<p><strong>Additional:</strong> " + escapeHtml(r.additional_info) + "</p>" : "") +
      "<h4>Audit Timeline</h4>" +
      '<div class="timeline">' +
      '<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-title">Submitted</div><div class="timeline-time">' + fmtDateTime(r.created_at) + "</div></div>" +
      (r.assignments || []).map((a) => '<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-title">Assigned to ' + escapeHtml(a.worker_name || "worker") + '</div><div class="timeline-time">' + fmtDateTime(a.assigned_at || a.created_at) + "</div></div>").join("") +
      (r.resolutions || []).map((rp) => '<div class="timeline-item"><div class="timeline-dot" style="background:var(--color-emerald-500);"></div><div class="timeline-title">Resolved</div><div class="timeline-time">' + fmtDateTime(rp.resolved_at || rp.created_at) + '</div><p style="font-size:12px;color:var(--color-slate-600);">' + escapeHtml(rp.resolution_notes || "") + "</p></div>").join("") +
      (r.verifications || []).map((v) => '<div class="timeline-item"><div class="timeline-dot" style="background:' + (v.verified ? "var(--color-emerald-600)" : "var(--color-red-500)") + ';"></div><div class="timeline-title">' + (v.verified ? "Verified ✓" : "Reopened") + '</div><div class="timeline-time">' + fmtDateTime(v.created_at) + "</div></div>").join("") +
      "</div>" +
      "</div>";
  } catch (e) {
    body.innerHTML = '<p class="state-cell state-error">Failed to load details.</p>';
  }
}

/* ==========================================================================
   Reusable Filter Bar
   ========================================================================== */

function renderFilterBar(containerId, onApply) {
  const c = document.getElementById(containerId);
  if (!c) return;
  const statuses = (APP_META && APP_META.statuses) || [];
  const issues = (APP_META && APP_META.issue_types) || [];
  const urgencies = (APP_META && APP_META.urgency_levels) || [];

  c.innerHTML =
    '<div class="filter-bar">' +
    '<div class="filter-grid">' +
    filterField("Status", '<select data-f="status" class="form-control"><option value="">All</option>' + statuses.map((s) => '<option value="' + s.key + '">' + escapeHtml(s.label) + "</option>").join("") + "</select>") +
    filterField("Issue Type", '<select data-f="category" class="form-control"><option value="">All</option>' + issues.map((i) => '<option value="' + escapeHtml(i) + '">' + escapeHtml(i) + "</option>").join("") + "</select>") +
    filterField("Location", '<input data-f="location" class="form-control" placeholder="Building / zone">') +
    filterField("Urgency", '<select data-f="urgency" class="form-control"><option value="">All</option>' + urgencies.map((u) => '<option value="' + escapeHtml(u) + '">' + escapeHtml(u) + "</option>").join("") + "</select>") +
    filterField("From", '<input data-f="date_from" type="date" class="form-control">') +
    filterField("To", '<input data-f="date_to" type="date" class="form-control">') +
    '<div class="filter-field filter-field--wide">' + filterFieldInner("Search", '<input data-f="search" class="form-control" placeholder="Search…">') + "</div>" +
    "</div>" +
    '<div class="filter-actions">' +
    '<button class="btn btn-primary btn-sm" id="' + containerId + '_apply">Apply</button>' +
    '<button class="btn btn-secondary btn-sm" id="' + containerId + '_reset">Reset</button>' +
    "</div>" +
    "</div>";

  const apply = () => {
    const params = {};
    c.querySelectorAll("[data-f]").forEach((el) => {
      params[el.dataset.f] = el.value.trim();
    });
    onApply(params);
  };

  document.getElementById(containerId + "_apply").addEventListener("click", apply);
  document.getElementById(containerId + "_reset").addEventListener("click", () => {
    c.querySelectorAll("[data-f]").forEach((el) => (el.value = ""));
    onApply({});
  });
  c.querySelectorAll('[data-f]').forEach((el) => {
    if (el.tagName === "INPUT") el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") apply();
    });
  });
}

function filterField(label, control) {
  return '<div class="filter-field">' + filterFieldInner(label, control) + "</div>";
}

function filterFieldInner(label, control) {
  return "<label class=\"form-label\">" + label + "</label>" + control;
}

/* ==========================================================================
   Modal & Toast utilities
   ========================================================================== */

function openModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add("active");
}

function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.remove("active");
}

function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.className = "toast toast-" + type;
  toast.style.cssText =
    "position: fixed; bottom: 24px; right: 24px; z-index: 3000;" +
    "background: #0f172a; color: #fff; padding: 12px 20px;" +
    "border-radius: 8px; font-size: 14px; font-weight: 500;" +
    "box-shadow: 0 10px 25px rgba(0,0,0,0.3); border-left: 4px solid " +
    (type === "success" ? "#10b981" : type === "error" ? "#ef4444" : "#3b82f6") + ";" +
    "animation: toastIn 300ms ease-out;";
  toast.innerText = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

/* ==========================================================================
   Event listeners & misc
   ========================================================================== */

function initEventListeners() {
  const b = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener("click", fn); };
  b("btnViewHome", () => switchView("home"));
  b("btnViewStudent", () => switchView("student"));
  b("btnViewFaculty", () => switchView("faculty"));
  b("btnViewFacilities", () => switchView("facilities"));
  b("btnViewAdmin", () => switchView("admin"));
  b("btnViewLiveImpact", () => switchView("liveimpact"));

  renderPersonas();
}

function initBeforeAfterSlider() {
  const container = document.getElementById("beforeAfterContainer");
  const afterWrapper = document.getElementById("baAfterWrapper");
  const handle = document.getElementById("baHandle");

  if (!container || !afterWrapper || !handle) return;
  const afterImg = afterWrapper.querySelector("img");

  let isDragging = false;

  const syncAfterWidth = () => {
    if (afterImg) afterImg.style.width = container.offsetWidth + "px";
  };

  const updateSliderPos = (x) => {
    const rect = container.getBoundingClientRect();
    syncAfterWidth();
    let posX = x - rect.left;
    if (posX < 0) posX = 0;
    if (posX > rect.width) posX = rect.width;
    const pct = (posX / rect.width) * 100;
    afterWrapper.style.width = pct + "%";
    handle.style.left = pct + "%";
  };

  syncAfterWidth();
  window.addEventListener("resize", syncAfterWidth);

  container.addEventListener("mousedown", (e) => { isDragging = true; updateSliderPos(e.clientX); });
  window.addEventListener("mouseup", () => { isDragging = false; });
  window.addEventListener("mousemove", (e) => { if (isDragging) updateSliderPos(e.clientX); });

  container.addEventListener("touchstart", (e) => { isDragging = true; updateSliderPos(e.touches[0].clientX); });
  window.addEventListener("touchend", () => { isDragging = false; });
  window.addEventListener("touchmove", (e) => { if (isDragging) updateSliderPos(e.touches[0].clientX); });
}

/* Close any open modal with Escape, or by clicking the backdrop. */
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-overlay.active").forEach((m) => m.classList.remove("active"));
  }
});

document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("mousedown", (e) => {
    if (e.target === overlay) overlay.classList.remove("active");
  });
});

const baHandleEl = document.getElementById("baHandle");
if (baHandleEl) {
  baHandleEl.addEventListener("keydown", (e) => {
    const container = document.getElementById("beforeAfterContainer");
    const afterWrap = document.getElementById("baAfterWrapper");
    if (!container || !afterWrap) return;
    let pct = parseFloat(baHandleEl.style.left) || 50;
    if (e.key === "ArrowLeft") pct = Math.max(0, pct - 5);
    else if (e.key === "ArrowRight") pct = Math.min(100, pct + 5);
    else return;
    e.preventDefault();
    afterWrap.style.width = pct + "%";
    baHandleEl.style.left = pct + "%";
    baHandleEl.setAttribute("aria-valuenow", Math.round(pct));
  });
}

/* Mobile navigation toggle */
function toggleMobileNav() {
  const nav = document.getElementById("mobileNav");
  const btn = document.getElementById("navToggle");
  if (!nav || !btn) return;
  const open = nav.classList.toggle("is-open");
  btn.setAttribute("aria-expanded", String(open));
  nav.setAttribute("aria-hidden", String(!open));
  document.body.classList.toggle("nav-open", open);
}

function closeMobileNav() {
  const nav = document.getElementById("mobileNav");
  const btn = document.getElementById("navToggle");
  if (nav && nav.classList.contains("is-open")) {
    nav.classList.remove("is-open");
    if (btn) btn.setAttribute("aria-expanded", "false");
    nav.setAttribute("aria-hidden", "true");
    document.body.classList.remove("nav-open");
  }
}

document.querySelectorAll(".mobile-nav__link, .mobile-nav__actions .btn").forEach((el) => {
  el.addEventListener("click", closeMobileNav);
});
