/* CIRCUVA — Interactive campus operations map (self-contained, no external deps)
 * Renders a reliable pseudo-3D SVG campus layout with status/severity-coded
 * incident markers, keyboard-accessible interactions, info cards, and category
 * filtering. Works fully offline. Exposes window.CampusMap.mount(opts).
 */
(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  var STATUS_COLOR = {
    reported: "#ef4444", open: "#ef4444", assigned: "#3b82f6",
    "in progress": "#f59e0b", resolved: "#10b981", verified: "#10b981"
  };
  var SEVERITY_COLOR = { High: "#dc2626", Medium: "#f59e0b", Low: "#94a3b8" };

  /* Campus buildings (viewBox 0 0 1000 620). depth = pseudo-3D extrusion. */
  var AREAS = [
    { name: "Admin Hall", code: "ADM", x: 70, y: 72, w: 190, h: 110, depth: 18 },
    { name: "Engineering Block", code: "ENG", x: 735, y: 55, w: 200, h: 142, depth: 32 },
    { name: "Student Centre", code: "STU", x: 70, y: 300, w: 200, h: 116, depth: 22 },
    { name: "Library", code: "LIB", x: 735, y: 300, w: 200, h: 116, depth: 28 },
    { name: "Cafeteria", code: "CAF", x: 70, y: 482, w: 200, h: 120, depth: 16 },
    { name: "Residential Court", code: "RES", x: 735, y: 482, w: 200, h: 120, depth: 24 },
    { name: "Engineering Quad", code: "QUAD", x: 380, y: 258, w: 240, h: 140, depth: 0, plaza: true }
  ];

  var PATHS = [
    [165, 127, 500, 328], [835, 126, 500, 328], [170, 358, 500, 328],
    [835, 358, 500, 328], [170, 542, 170, 358], [835, 542, 500, 328]
  ];

  var CATEGORY_PHOTOS = {
    waste: ["/static/assets/images/cat-waste-1.jpg", "/static/assets/images/cat-waste-2.jpg", "/static/assets/images/cat-waste-3.jpg"],
    water: ["/static/assets/images/cat-plastic-1.jpg", "/static/assets/images/cat-plastic-2.jpg", "/static/assets/images/cat-plastic-3.jpg"],
    cleanliness: ["/static/assets/images/cat-recycling-1.jpg", "/static/assets/images/cat-recycling-2.jpg", "/static/assets/images/cat-litter-1.jpg"],
    infrastructure: ["/static/assets/images/cat-broken-1.jpg", "/static/assets/images/cat-broken-2.jpg", "/static/assets/images/cat-broken-3.jpg"],
    energy: ["/static/assets/images/cat-ewaste-1.jpg", "/static/assets/images/cat-ewaste-2.jpg", "/static/assets/images/cat-ewaste-3.jpg"]
  };

  var DEFAULT_INCIDENTS = [
    { id: "inc-1", title: "Overflowing bin", category: "Waste", location: "Cafeteria", status: "In progress", severity: "Medium", group: "waste", team: "Ops Crew B", reported: "2h ago", desc: "Main dining bin overflowing during lunch rush; surrounding litter accumulating." },
    { id: "inc-2", title: "Water leakage", category: "Water", location: "Engineering Block", status: "Assigned", severity: "High", group: "water", team: "Plumbing Unit", reported: "5h ago", desc: "Pipe joint leaking near the east stairwell, pooling on the floor." },
    { id: "inc-3", title: "Recycling contamination", category: "Cleanliness", location: "Student Centre", status: "Resolved", severity: "Medium", group: "cleanliness", team: "Recycling Team", reported: "Yesterday", desc: "Mixed recycling bin contaminated with food waste; re-sorted and relabeled." },
    { id: "inc-4", title: "Illegal dumping", category: "Waste", location: "Admin Hall", status: "In progress", severity: "High", group: "waste", team: "Ops Crew A", reported: "1h ago", desc: "Furniture and debris dumped behind the loading bay." },
    { id: "inc-5", title: "Broken bin lid", category: "Infrastructure", location: "Library", status: "Resolved", severity: "Low", group: "infrastructure", team: "Facilities", reported: "2 days ago", desc: "Side bin lid hinge broken; replaced during morning round." },
    { id: "inc-6", title: "Litter cluster", category: "Cleanliness", location: "Residential Court", status: "Assigned", severity: "Low", group: "cleanliness", team: "Grounds", reported: "3h ago", desc: "Wind-blown litter collected near the east court entrance." },
    { id: "inc-7", title: "Streetlight outage", category: "Energy", location: "Engineering Quad", status: "Resolved", severity: "Low", group: "energy", team: "Electrical", reported: "Yesterday", desc: "Perimeter light out; bulb replaced and circuit checked." },
    { id: "inc-8", title: "Drain blockage", category: "Water", location: "Residential Court", status: "In progress", severity: "Medium", group: "water", team: "Plumbing Unit", reported: "4h ago", desc: "Storm drain blocked with leaves; causing minor ponding." }
  ];
  DEFAULT_INCIDENTS.forEach(function (inc, i) {
    var pool = CATEGORY_PHOTOS[inc.group] || CATEGORY_PHOTOS.waste;
    inc.photo = pool[i % pool.length];
  });

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]);
    });
  }
  function statusColor(s) { return STATUS_COLOR[String(s || "").toLowerCase()] || "#64748b"; }
  function severityColor(s) { return SEVERITY_COLOR[s] || "#94a3b8"; }
  function cap(s) { return String(s || "").replace(/\b\w/g, function (c) { return c.toUpperCase(); }); }
  function isActive(s) { return /progress|assigned/i.test(s); }

  function buildingSVG(a) {
    if (a.plaza) {
      return '<g class="cm-area">' +
        '<rect x="' + a.x + '" y="' + a.y + '" width="' + a.w + '" height="' + a.h + '" rx="18" fill="#dcefe0" stroke="#b9e0c4" stroke-width="2"/>' +
        '<circle cx="' + (a.x + a.w / 2) + '" cy="' + (a.y + a.h / 2) + '" r="20" fill="#bfe3b0" stroke="#86c46a" stroke-width="2"/>' +
        '<circle cx="' + (a.x + a.w / 2) + '" cy="' + (a.y + a.h / 2) + '" r="9" fill="#86c46a"/>' +
        '<text x="' + (a.x + a.w / 2) + '" y="' + (a.y + a.h - 14) + '" text-anchor="middle" class="cm-area__name">' + esc(a.name) + "</text>" +
        '<text x="' + (a.x + a.w / 2) + '" y="' + (a.y + a.h - 2) + '" text-anchor="middle" class="cm-area__code">' + a.code + "</text>" +
        "</g>";
    }
    var d = a.depth, x = a.x, y = a.y, w = a.w, h = a.h;
    var top = x + "," + y + " " + (x + w) + "," + y + " " + (x + w - d) + "," + (y - d) + " " + (x - d) + "," + (y - d);
    var side = (x + w) + "," + y + " " + (x + w - d) + "," + (y - d) + " " + (x + w - d) + "," + (y + h - d) + " " + (x + w) + "," + (y + h);
    return '<g class="cm-area" filter="url(#cm-shadow)">' +
      '<polygon points="' + side + '" fill="#cbd5e1"/>' +
      '<polygon points="' + top + '" fill="#f1f5f9" stroke="#e2e8f0" stroke-width="1"/>' +
      '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="7" fill="#e2e8f0" stroke="#cdd9e5" stroke-width="1"/>' +
      '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="9" rx="4" fill="#10b981" opacity="0.85"/>' +
      '<rect x="' + (x + 16) + '" y="' + (y + 22) + '" width="' + (w - 32) + '" height="' + (h - 40) + '" rx="4" fill="#eef3f8"/>' +
      '<text x="' + (x + w / 2) + '" y="' + (y + h / 2 - 2) + '" text-anchor="middle" class="cm-area__name">' + esc(a.name) + "</text>" +
      '<text x="' + (x + w / 2) + '" y="' + (y + h / 2 + 16) + '" text-anchor="middle" class="cm-area__code">' + a.code + "</text>" +
      "</g>";
  }

  function markerSVG(inc, idx, pos) {
    var active = isActive(inc.status);
    var sc = statusColor(inc.status);
    var vc = severityColor(inc.severity);
    var pulse = active
      ? '<circle r="16" fill="none" stroke="' + sc + '" stroke-width="3" class="cm-pulse">' +
        '<animate attributeName="r" values="14;26;14" dur="2.4s" repeatCount="indefinite"/>' +
        '<animate attributeName="opacity" values="0.7;0;0.7" dur="2.4s" repeatCount="indefinite"/></circle>'
      : "";
    return '<g class="cm-marker' + (active ? " cm-marker--active" : "") + '" data-id="' + esc(inc.id) + '" transform="translate(' + pos.x + "," + pos.y + ')" tabindex="0" role="button" ' +
      'aria-label="' + esc("Incident: " + inc.title + " at " + inc.location + ", status " + inc.status + ", severity " + inc.severity) + '">' +
      pulse +
      '<circle r="18" fill="none" stroke="' + vc + '" stroke-width="4" opacity="0.9"/>' +
      '<circle r="12" fill="' + sc + '" stroke="#ffffff" stroke-width="3"/>' +
      '<text x="0" y="4" text-anchor="middle" class="cm-marker__num">' + (idx + 1) + "</text>" +
      "</g>";
  }

  function mount(opts) {
    opts = opts || {};
    var target = typeof opts.target === "string" ? document.getElementById(opts.target) : opts.target;
    if (!target) return null;
    var incidents = (opts.incidents && opts.incidents.length) ? opts.incidents : DEFAULT_INCIDENTS.slice();
    var showLegend = opts.legend !== false;

    target.classList.add("campusmap");
    target.innerHTML = "";

    var stage = document.createElement("div");
    stage.className = "campusmap__stage";

    var svgParts = [];
    svgParts.push('<svg class="campusmap__svg" viewBox="0 0 1000 620" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Interactive campus incident map">');
    svgParts.push('<defs>' +
      '<linearGradient id="cm-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#f4f8fb"/><stop offset="100%" stop-color="#e7eef5"/></linearGradient>' +
      '<filter id="cm-shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.16"/></filter>' +
      "</defs>");
    svgParts.push('<rect x="0" y="0" width="1000" height="620" fill="url(#cm-bg)"/>');
    /* grass accents */
    svgParts.push('<rect x="30" y="30" width="940" height="560" rx="26" fill="#eaf3ec" opacity="0.6"/>');
    /* pathways */
    PATHS.forEach(function (p) {
      svgParts.push('<path d="M' + p[0] + " " + p[1] + " L" + p[2] + " " + p[3] + '" stroke="#dbe5ee" stroke-width="16" stroke-linecap="round" fill="none"/>');
      svgParts.push('<path d="M' + p[0] + " " + p[1] + " L" + p[2] + " " + p[3] + '" stroke="#ffffff" stroke-width="6" stroke-linecap="round" stroke-dasharray="2 12" fill="none"/>');
    });
    /* trees */
    [[130, 250], [650, 250], [500, 200], [250, 470], [560, 480], [880, 430], [60, 430], [940, 250]].forEach(function (t) {
      svgParts.push('<circle cx="' + t[0] + '" cy="' + t[1] + '" r="16" fill="#bfe3b0"/><circle cx="' + t[0] + '" cy="' + t[1] + '" r="9" fill="#86c46a"/>');
    });
    /* buildings */
    AREAS.forEach(function (a) { svgParts.push(buildingSVG(a)); });
    /* markers */
    var areaCenter = {};
    AREAS.forEach(function (a) { areaCenter[a.name] = { x: a.x + a.w / 2, y: a.y + a.h / 2 }; });
    incidents.forEach(function (inc, idx) {
      var pos = (typeof inc.x === "number" && typeof inc.y === "number")
        ? { x: inc.x, y: inc.y }
        : (function () {
            var a = areaCenter[inc.location] || areaCenter[Object.keys(areaCenter)[idx % Object.keys(areaCenter).length]];
            var jx = ((idx * 53) % 80) - 40, jy = ((idx * 31) % 60) - 30;
            return { x: a.x + jx, y: a.y + jy };
          })();
      svgParts.push(markerSVG(inc, idx, pos));
      inc._pos = pos;
    });
    svgParts.push("</svg>");
    stage.innerHTML = svgParts.join("");
    var svg = stage.querySelector("svg");

    var card = document.createElement("div");
    card.className = "campusmap__card";
    card.hidden = true;
    stage.appendChild(card);

    target.appendChild(stage);
    if (showLegend) target.appendChild(buildLegend());

    function buildLegend() {
      var wrap = document.createElement("div");
      wrap.className = "campusmap__legend";
      var html = '<span class="campusmap__legend-title">Status</span>';
      [["In progress", "#f59e0b"], ["Assigned", "#3b82f6"], ["Resolved", "#10b981"], ["Reported", "#ef4444"]].forEach(function (st) {
        html += '<span class="cm-leg"><i style="background:' + st[1] + '"></i>' + st[0] + "</span>";
      });
      html += '<span class="campusmap__legend-title">Severity ring</span>';
      [["High", "#dc2626"], ["Medium", "#f59e0b"], ["Low", "#94a3b8"]].forEach(function (sv) {
        html += '<span class="cm-leg"><i class="cm-leg--ring" style="border-color:' + sv[1] + '"></i>' + sv[0] + "</span>";
      });
      wrap.innerHTML = html;
      return wrap;
    }

    function showCard(inc, gEl) {
      var sc = statusColor(inc.status);
      card.innerHTML =
        '<div class="campusmap__card-head">' +
          '<span class="cm-status-dot" style="background:' + sc + '"></span>' +
          "<strong>" + esc(inc.title) + "</strong>" +
          '<button type="button" class="campusmap__card-close" aria-label="Close" data-close="1">×</button>' +
        "</div>" +
        (inc.photo ? '<img class="campusmap__card-img" src="' + esc(inc.photo) + '" alt="' + esc(inc.title) + '" loading="lazy">' : "") +
        '<div class="campusmap__card-meta">' +
          "<span><b>Category:</b> " + esc(inc.category || inc.group || "—") + "</span>" +
          "<span><b>Location:</b> " + esc(inc.location) + "</span>" +
          '<span><b>Status:</b> <span class="badge badge-' + esc(String(inc.status).toLowerCase().replace(/\s+/g, "_")) + '">' + esc(cap(inc.status)) + "</span></span>" +
          '<span><b>Severity:</b> <span class="badge badge-' + esc((inc.severity || "low").toLowerCase()) + '">' + esc(inc.severity) + "</span></span>" +
          "<span><b>Reported:</b> " + esc(inc.reported) + "</span>" +
          "<span><b>Assigned team:</b> " + esc(inc.team) + "</span>" +
        "</div>" +
        '<p class="campusmap__card-desc">' + esc(inc.desc) + "</p>" +
        '<button type="button" class="btn btn-sm btn-primary campusmap__card-btn" data-open="1">Open in Live Impact →</button>';

      card.hidden = false;
      var sr = stage.getBoundingClientRect();
      var mr = gEl.getBoundingClientRect();
      var cw = card.offsetWidth || 280;
      var ch = card.offsetHeight || 220;
      var left = (mr.left - sr.left) + mr.width / 2;
      var top = (mr.top - sr.top) - 14;
      card.style.transform = "translate(-50%, -100%)";
      left = Math.max(cw / 2 + 8, Math.min(left, sr.width - cw / 2 - 8));
      if (top - ch < 0) { top = (mr.top - sr.top) + mr.height + 14; card.style.transform = "translate(-50%, 0)"; }
      card.style.left = left + "px";
      card.style.top = top + "px";

      card.querySelector("[data-close]").addEventListener("click", function (e) { e.stopPropagation(); card.hidden = true; });
      card.querySelector("[data-open]").addEventListener("click", function (e) { e.stopPropagation(); card.hidden = true; if (window.switchView) window.switchView("liveimpact"); });
    }

    function wire(g) {
      var id = g.getAttribute("data-id");
      var inc = incidents.filter(function (i) { return i.id === id; })[0] || null;
      g.addEventListener("click", function (ev) { ev.stopPropagation(); if (inc) showCard(inc, g); });
      g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); if (inc) showCard(inc, g); } });
    }
    Array.prototype.forEach.call(svg.querySelectorAll(".cm-marker"), wire);

    document.addEventListener("click", function docClose(e) {
      if (!card.hidden && !card.contains(e.target) && !(e.target.closest && e.target.closest(".cm-marker"))) card.hidden = true;
    });

    return {
      setFilter: function (group) {
        Array.prototype.forEach.call(svg.querySelectorAll(".cm-marker"), function (m) {
          var inc = incidents.filter(function (i) { return i.id === m.getAttribute("data-id"); })[0];
          var show = !group || group === "all" || (inc && inc.group === group);
          m.style.display = show ? "" : "none";
        });
        card.hidden = true;
      },
      addIncident: function (inc) {
        if (!inc) return;
        incidents.push(inc);
        var pos = (typeof inc.x === "number" && typeof inc.y === "number")
          ? { x: inc.x, y: inc.y }
          : (function () {
              var a = areaCenter[inc.location] || areaCenter["Cafeteria"];
              return { x: a.x + 10, y: a.y + 10 };
            })();
        inc._pos = pos;
        var g = document.createElementNS(SVGNS, "g");
        g.setAttribute("class", "cm-marker");
        g.setAttribute("data-id", esc(inc.id));
        g.setAttribute("transform", "translate(" + pos.x + "," + pos.y + ")");
        g.setAttribute("tabindex", "0");
        g.setAttribute("role", "button");
        g.setAttribute("aria-label", esc("Incident: " + (inc.title || "New report")));
        g.innerHTML =
          '<circle r="18" fill="none" stroke="' + severityColor(inc.severity || "Low") + '" stroke-width="4" opacity="0.9"/>' +
          '<circle r="12" fill="' + statusColor(inc.status || "reported") + '" stroke="#ffffff" stroke-width="3"/>' +
          '<text x="0" y="4" text-anchor="middle" class="cm-marker__num">' + incidents.length + "</text>";
        svg.appendChild(g);
        wire(g);
      }
    };
  }

  window.CampusMap = { mount: mount };
})();
