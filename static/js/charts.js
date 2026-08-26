/* CIRCUVA — Self-contained SVG chart engine (no external library).
 * Replaces Chart.js for the demo dashboards. Draws bar / doughnut / line
 * charts directly as inline SVG. Exposes window.CircuvaCharts.render(id, type, data, options).
 * `data` matches the Chart.js shape: { labels:[], datasets:[{ label, data, backgroundColor, borderColor }] }.
 */
(function () {
  "use strict";

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]);
    });
  }

  function barSVG(data) {
    var labels = data.labels || [];
    var ds = (data.datasets && data.datasets[0]) || {};
    var vals = ds.data || [];
    var W = 320, H = 200, pad = 26;
    var max = Math.max(1, Math.max.apply(null, vals));
    var n = Math.max(1, vals.length);
    var gap = (W - pad * 2) / n;
    var bw = gap * 0.56;
    var base = H - pad - 12;
    var out = "";
    vals.forEach(function (v, i) {
      var h = (v / max) * (H - pad * 2 - 16);
      var x = pad + i * gap + (gap - bw) / 2;
      var y = base - h;
      out += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" rx="4" fill="' + (ds.backgroundColor || "#059669") + '"/>';
      out += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (y - 4).toFixed(1) + '" text-anchor="middle" class="cc-barval">' + esc(v) + "</text>";
      out += '<text x="' + (x + bw / 2).toFixed(1) + '" y="' + (H - pad + 12) + '" text-anchor="middle" class="cc-axis">' + esc(labels[i] || "") + "</text>";
    });
    out += '<line x1="' + pad + '" y1="' + base + '" x2="' + (W - pad) + '" y2="' + base + '" stroke="#e2e8f0"/>';
    return '<svg viewBox="0 0 ' + W + " " + H + '" class="cc-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Bar chart">' + out + "</svg>";
  }

  function doughnutSVG(data) {
    var labels = data.labels || [];
    var ds = (data.datasets && data.datasets[0]) || {};
    var vals = ds.data || [];
    var colors = ds.backgroundColor || ["#ef4444", "#f59e0b", "#3b82f6", "#64748b"];
    var total = vals.reduce(function (a, b) { return a + b; }, 0) || 1;
    var cx = 100, cy = 100, r = 64, sw = 26;
    var ang = -Math.PI / 2, segs = "";
    vals.forEach(function (v, i) {
      var frac = v / total;
      var a2 = ang + frac * Math.PI * 2;
      var large = frac > 0.5 ? 1 : 0;
      var x1 = cx + r * Math.cos(ang), y1 = cy + r * Math.sin(ang);
      var x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
      segs += '<path d="M' + x1.toFixed(2) + " " + y1.toFixed(2) + " A" + r + " " + r + " 0 " + large + " 1 " + x2.toFixed(2) + " " + y2.toFixed(2) + '" fill="none" stroke="' + (colors[i] || "#94a3b8") + '" stroke-width="' + sw + '"/>';
      ang = a2;
    });
    var legend = "";
    labels.forEach(function (l, i) {
      legend += '<rect x="0" y="' + (i * 18) + '" width="11" height="11" rx="2" fill="' + (colors[i] || "#94a3b8") + '"/>' +
        '<text x="16" y="' + (i * 18 + 10) + '" class="cc-legend">' + esc(l) + "</text>";
    });
    return '<svg viewBox="0 0 300 210" class="cc-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Distribution chart">' +
      '<g transform="translate(20,5)">' + segs +
      '<text x="' + cx + '" y="' + (cy - 2) + '" text-anchor="middle" class="cc-doughnut-val">' + total + "</text>" +
      '<text x="' + cx + '" y="' + (cy + 14) + '" text-anchor="middle" class="cc-axis">total</text></g>' +
      '<g transform="translate(225,40)">' + legend + "</g></svg>";
  }

  function lineSVG(data) {
    var labels = data.labels || [];
    var sets = data.datasets || [];
    var W = 320, H = 200, pad = 28;
    var all = [];
    sets.forEach(function (s) { all = all.concat(s.data || []); });
    var max = Math.max(1, Math.max.apply(null, all));
    var min = Math.min(0, Math.min.apply(null, all));
    var range = (max - min) || 1;
    function px(i) { return pad + (i / Math.max(1, labels.length - 1)) * (W - pad * 2); }
    function py(v) { return H - pad - ((v - min) / range) * (H - pad * 2 - 10); }
    var grid = "";
    for (var g = 0; g <= 4; g++) {
      var gy = pad + g * ((H - pad * 2 - 10) / 4);
      grid += '<line x1="' + pad + '" y1="' + gy.toFixed(1) + '" x2="' + (W - pad) + '" y2="' + gy.toFixed(1) + '" stroke="#eef2f6"/>';
    }
    var paths = "";
    sets.forEach(function (s) {
      var col = s.borderColor || "#10b981";
      var d = "";
      (s.data || []).forEach(function (v, i) { d += (i ? "L" : "M") + px(i).toFixed(1) + " " + py(v).toFixed(1) + " "; });
      paths += '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="2.5"/>';
      (s.data || []).forEach(function (v, i) { paths += '<circle cx="' + px(i).toFixed(1) + '" cy="' + py(v).toFixed(1) + '" r="3" fill="' + col + '"/>'; });
    });
    var xl = "";
    labels.forEach(function (l, i) { xl += '<text x="' + px(i).toFixed(1) + '" y="' + (H - pad + 12) + '" text-anchor="middle" class="cc-axis">' + esc(l) + "</text>"; });
    return '<svg viewBox="0 0 ' + W + " " + H + '" class="cc-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Line chart">' + grid + paths + xl + "</svg>";
  }

  function render(id, type, data, options) {
    var c = document.getElementById(id);
    if (!c) return;
    var svgStr;
    if (type === "doughnut") svgStr = doughnutSVG(data);
    else if (type === "line") svgStr = lineSVG(data);
    else svgStr = barSVG(data);

    if (c.parentNode) {
      var prev = c.parentNode.querySelector(".cc-chart");
      if (prev) prev.parentNode.removeChild(prev);
    }
    var wrap = document.createElement("div");
    wrap.className = "cc-chart";
    wrap.innerHTML = svgStr;
    c.style.display = "none";
    if (c.parentNode) c.parentNode.insertBefore(wrap, c);
    return wrap;
  }

  window.CircuvaCharts = { render: render, barSVG: barSVG, doughnutSVG: doughnutSVG, lineSVG: lineSVG };
})();
