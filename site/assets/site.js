/* Alternative Paths: listing filters, copy and share buttons, optional cookieless counts, and a
   self-test (?selftest=1) that headless Chrome runs in CI against the built and the live site. */
(function () {
  "use strict";
  var errors = [];
  window.addEventListener("error", function (e) { errors.push(String(e.message || e)); });
  function count(name) { try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: name, event: true }); } catch (e) { /* optional */ } }
  function flash(btn, text) { var old = btn.textContent; btn.textContent = text; setTimeout(function () { btn.textContent = old; }, 1600); }

  var list = document.getElementById("list");
  var q = document.getElementById("q"), group = document.getElementById("group"), county = document.getElementById("county"),
      minwage = document.getElementById("minwage"), shown = document.getElementById("shown");
  function apply() {
    if (!list) return 0;
    var text = q ? q.value.trim().toLowerCase() : "", g = group ? group.value : "", c = county ? county.value : "",
        w = minwage ? Number(minwage.value) : 0, n = 0;
    Array.prototype.forEach.call(list.querySelectorAll("tbody tr"), function (tr) {
      var ok = (!text || tr.getAttribute("data-text").indexOf(text) >= 0) && (!g || tr.getAttribute("data-group") === g) &&
               (!c || tr.getAttribute("data-counties").indexOf("|" + c + "|") >= 0) && Number(tr.getAttribute("data-wage")) >= w;
      tr.hidden = !ok;
      if (ok) n++;
    });
    if (shown) shown.textContent = n + " of " + list.getAttribute("data-count") + " shown";
    return n;
  }
  [q, group, county, minwage].forEach(function (el) {
    if (el) el.addEventListener(el === q ? "input" : "change", function () { apply(); count("filter"); });
  });
  apply();

  Array.prototype.forEach.call(document.querySelectorAll("[data-share]"), function (btn) {
    btn.addEventListener("click", function () {
      var url = (document.querySelector("link[rel=canonical]") || {}).href || location.href;
      if (navigator.share) navigator.share({ title: document.title, url: url }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { flash(btn, "Link copied"); });
      count("share");
    });
  });
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a.src, a.button");
    if (a) count(a.classList.contains("src") ? "source-click" : "apply-click");
  });

  if (/[?&]selftest=1/.test(location.search)) {
    window.addEventListener("load", function () {
      setTimeout(function () {
        var fails = [];
        var ok = function (cond, msg) { if (!cond) fails.push(msg); };
        ok(document.querySelector("h1"), "page has a heading");
        ok(document.querySelector("link[rel=canonical]"), "page has a canonical URL");
        Array.prototype.forEach.call(document.querySelectorAll('script[type="application/ld+json"]'), function (s, i) {
          try { JSON.parse(s.textContent); } catch (e) { fails.push("structured data block " + i + " parses"); }
        });
        if (list) {
          var rows = list.querySelectorAll("tbody tr");
          ok(rows.length > 0 && rows.length === Number(list.getAttribute("data-count")), "every listing is in the table");
          Array.prototype.forEach.call(rows, function (tr, i) {
            if (i < 400) ok(/^https:\/\//.test((tr.querySelector("a.src") || {}).getAttribute ? tr.querySelector("a.src").getAttribute("href") : ""), "listing " + i + " links its official record");
          });
          if (q) {
            var first = rows[0] && rows[0].getAttribute("data-text").split(" ")[0];
            q.value = first || "";
            var n = apply();
            ok(n > 0 && n <= rows.length, "search narrows the list");
            q.value = "";
            ok(apply() === rows.length, "clearing the search shows everything again");
          }
        }
        var quotes = document.querySelectorAll("blockquote.q");
        Array.prototype.forEach.call(quotes, function (b, i) { ok(b.querySelector("a.src"), "quote " + i + " links to its source"); });
        if (document.querySelector(".scorebox")) {
          ok(quotes.length > 0, "program page shows quotes");
          ok(document.querySelector(".scorebox time"), "program page shows an as-of date");
          ok(document.querySelector("a.correction"), "program page has a problem link");
        }
        ok(errors.length === 0, "no script errors: " + errors.join("; "));
        var out = document.getElementById("selftest");
        out.hidden = false;
        out.setAttribute("data-selftest", fails.length ? "fail" : "pass");
        out.textContent = fails.length ? "FAIL\n" + fails.slice(0, 20).join("\n") : "PASS";
      }, 300);
    });
  }
})();
