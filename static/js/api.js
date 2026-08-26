/*
 * Circuva — Data / Service layer.
 * All backend communication lives here so UI components never touch fetch
 * or endpoint URLs directly. This keeps business logic separate from the DOM.
 */
(function () {
  "use strict";

  async function req(method, path, options) {
    options = options || {};
    const headers = {};
    if (!options.isForm) headers["Content-Type"] = "application/json";
    const token = window.currentToken;
    if (token) headers["Authorization"] = "Bearer " + token;

    const init = { method: method, headers: headers };
    if (options.body) init.body = options.isForm ? options.body : JSON.stringify(options.body);

    const res = await fetch(path, init);

    if (res.status === 204) return null;
    if (!res.ok) {
      let detail = "Request failed (" + res.status + ")";
      try {
        const data = await res.json();
        if (data && data.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      } catch (e) { /* ignore parse error */ }
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return res.json();
  }

  const Api = {
    meta: () => req("GET", "/api/v1/auth/meta"),
    personas: () => req("GET", "/api/v1/auth/personas"),
    login: (email, password) => req("POST", "/api/v1/auth/login", { body: { email: email, password: password } }),
    demoLogin: (role) => req("POST", "/api/v1/auth/demo-login/" + role),
    me: () => req("GET", "/api/v1/auth/me"),
    users: (role) => req("GET", "/api/v1/auth/users?role=" + encodeURIComponent(role || "")),

    reports: (params) => {
      const q = new URLSearchParams();
      params = params || {};
      Object.keys(params).forEach(function (k) {
        const v = params[k];
        if (v !== undefined && v !== null && v !== "") q.append(k, v);
      });
      const qs = q.toString();
      return req("GET", "/api/v1/reports" + (qs ? "?" + qs : ""));
    },
    report: (id) => req("GET", "/api/v1/reports/" + id),
    upload: (file) => {
      const fd = new FormData();
      fd.append("file", file);
      return req("POST", "/api/v1/reports/upload-photo", { body: fd, isForm: true });
    },
    createReport: (data, imageUrls) => {
      let path = "/api/v1/reports";
      if (imageUrls && imageUrls.length) {
        path += "?" + imageUrls.map(function (u) { return "image_urls=" + encodeURIComponent(u); }).join("&");
      }
      return req("POST", path, { body: data });
    },

    acknowledge: (id) => req("POST", "/api/v1/reports/" + id + "/acknowledge"),
    assign: (id, payload) => req("POST", "/api/v1/reports/" + id + "/assign", { body: payload }),
    setStatus: (id, status) => req("PATCH", "/api/v1/reports/" + id + "/status", { body: { status: status } }),
    resolve: (id, payload) => req("POST", "/api/v1/reports/" + id + "/resolve", { body: payload }),
    verify: (id, payload) => req("POST", "/api/v1/reports/" + id + "/verify", { body: payload }),

    overview: () => req("GET", "/api/v1/analytics/overview"),
    hotspots: () => req("GET", "/api/v1/analytics/hotspots"),
    activity: () => req("GET", "/api/v1/analytics/activity"),
    charts: () => req("GET", "/api/v1/analytics/charts-data"),
  };

  window.Api = Api;
})();
