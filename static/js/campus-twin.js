(function () {
  "use strict";
  var canvas = document.getElementById("heroTwin");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var stage = canvas.parentElement;
  var W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
  var t = 0;

  function resize() {
    var r = stage.getBoundingClientRect();
    W = Math.max(320, r.width);
    H = Math.max(220, r.height);
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  var buildings = [
    { x: -120, y: -40, w: 90, d: 70, h: 70, c: "#7fb4e6" },
    { x: 20, y: -90, w: 110, d: 80, h: 110, c: "#8fc0ec" },
    { x: 150, y: 10, w: 80, d: 90, h: 60, c: "#74aadf" },
    { x: -40, y: 90, w: 120, d: 70, h: 90, c: "#9cc8f0" },
    { x: -180, y: 80, w: 70, d: 60, h: 50, c: "#86bbea" }
  ];
  var markers = [
    { x: 60, y: -20, color: "#f1a13b" },
    { x: -90, y: 40, color: "#37c26b" },
    { x: 120, y: 70, color: "#e0584f" }
  ];
  var vehicles = [
    { p: 0, sp: 0.0009, path: [[-200, -10], [40, -10], [40, 120], [-200, 120]] },
    { p: 0.4, sp: 0.0007, path: [[180, 60], [-20, 60], [-20, -80], [180, -80]] }
  ];

  function iso(x, y, z) {
    var ox = W / 2, oy = H / 2 - 10;
    return { x: ox + (x - y) * 0.62, y: oy + (x + y) * 0.34 - z };
  }

  function drawGround() {
    var g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "#eef5fc");
    g.addColorStop(1, "#d6e6f4");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(120,160,200,0.18)";
    ctx.lineWidth = 1;
    for (var i = -320; i <= 320; i += 40) {
      var a = iso(i, -320, 0), b = iso(i, 320, 0);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      var c = iso(-320, i, 0), d = iso(320, i, 0);
      ctx.beginPath(); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.stroke();
    }
    // roads
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    var r1a = iso(-220, -30, 0), r1b = iso(220, -30, 0), r1c = iso(220, -10, 0), r1d = iso(-220, -10, 0);
    ctx.beginPath(); ctx.moveTo(r1a.x, r1a.y); ctx.lineTo(r1b.x, r1b.y); ctx.lineTo(r1c.x, r1c.y); ctx.lineTo(r1d.x, r1d.y); ctx.fill();
  }

  function drawBuilding(b) {
    var top = iso(b.x + b.w / 2, b.y + b.d / 2, b.h);
    var f1 = iso(b.x, b.y, 0), f2 = iso(b.x + b.w, b.y, 0), f3 = iso(b.x + b.w, b.y + b.d, 0), f4 = iso(b.x, b.y + b.d, 0);
    var t1 = iso(b.x, b.y, b.h), t2 = iso(b.x + b.w, b.y, b.h), t3 = iso(b.x + b.w, b.y + b.d, b.h), t4 = iso(b.x, b.y + b.d, b.h);
    // right face
    ctx.fillStyle = shade(b.c, -18);
    ctx.beginPath(); ctx.moveTo(f2.x, f2.y); ctx.lineTo(f3.x, f3.y); ctx.lineTo(t3.x, t3.y); ctx.lineTo(t2.x, t2.y); ctx.fill();
    // left face
    ctx.fillStyle = shade(b.c, -34);
    ctx.beginPath(); ctx.moveTo(f1.x, f1.y); ctx.lineTo(f3.x, f3.y); ctx.lineTo(t3.x, t3.y); ctx.lineTo(t4.x, t4.y); ctx.fill();
    // top
    ctx.fillStyle = b.c;
    ctx.beginPath(); ctx.moveTo(t1.x, t1.y); ctx.lineTo(t2.x, t2.y); ctx.lineTo(t3.x, t3.y); ctx.lineTo(t4.x, t4.y); ctx.fill();
    // windows
    ctx.fillStyle = "rgba(255,255,255,0.35)";
    for (var wx = 0; wx < 3; wx++) for (var wy = 0; wy < Math.max(1, b.h / 25); wy++) {
      var pp = iso(b.x + 18 + wx * 24, b.y + 14, 14 + wy * 22);
      ctx.fillRect(pp.x - 5, pp.y - 7, 9, 11);
    }
  }

  function shade(hex, amt) {
    var n = parseInt(hex.slice(1), 16);
    var r = Math.max(0, Math.min(255, (n >> 16) + amt));
    var g = Math.max(0, Math.min(255, ((n >> 8) & 255) + amt));
    var b = Math.max(0, Math.min(255, (n & 255) + amt));
    return "rgb(" + r + "," + g + "," + b + ")";
  }

  function drawMarkers() {
    for (var i = 0; i < markers.length; i++) {
      var m = markers[i];
      var p = iso(m.x, m.y, 0);
      var pulse = reduceMotion ? 0 : (Math.sin(t * 0.05 + i) + 1) / 2;
      ctx.strokeStyle = m.color;
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.35 + pulse * 0.45;
      ctx.beginPath(); ctx.arc(p.x, p.y, 8 + pulse * 10, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillStyle = m.color;
      ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(p.x, p.y, 2, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawVehicles() {
    for (var i = 0; i < vehicles.length; i++) {
      var v = vehicles[i];
      if (!reduceMotion) { v.p += v.sp; if (v.p > 1) v.p -= 1; }
      var seg = v.p * (v.path.length - 1);
      var idx = Math.floor(seg);
      var fr = seg - idx;
      var a = v.path[idx], b = v.path[idx + 1] || v.path[idx];
      var x = a[0] + (b[0] - a[0]) * fr;
      var y = a[1] + (b[1] - a[1]) * fr;
      var p = iso(x, y, 0);
      ctx.fillStyle = "rgba(54,180,140,0.25)";
      ctx.beginPath(); ctx.arc(p.x, p.y, 9, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#2bb673";
      ctx.beginPath(); ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawSweep() {
    if (reduceMotion) return;
    var ang = t * 0.012;
    var cx = W / 2, cy = H / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(ang);
    var lg = ctx.createLinearGradient(0, 0, 220, 0);
    lg.addColorStop(0, "rgba(54,180,140,0.18)");
    lg.addColorStop(1, "rgba(54,180,140,0)");
    ctx.fillStyle = lg;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, 260, -0.18, 0.18);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function frame() {
    drawGround();
    for (var i = 0; i < buildings.length; i++) drawBuilding(buildings[i]);
    drawSweep();
    drawVehicles();
    drawMarkers();
    if (!reduceMotion) { t += 1; requestAnimationFrame(frame); }
  }

  resize();
  if (window.ResizeObserver) { new ResizeObserver(resize).observe(stage); }
  else { window.addEventListener("resize", resize); }
  frame();
  if (reduceMotion) { /* draw one static frame only */ }
})();
