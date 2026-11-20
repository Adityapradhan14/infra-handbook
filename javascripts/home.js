// Home page only: type the tree command once per visit, and run the "Revise one" panel.
document$.subscribe(function () {
  var home = document.querySelector(".ih-home");
  if (!home) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- tree typing ----
  var tree = home.querySelector(".ih-tree");
  var seen = false;
  try { seen = sessionStorage.getItem("ih-typed") === "1"; } catch (e) {}
  if (tree && !reduce && !seen && !tree.dataset.done) {
    tree.dataset.done = "1";
    try { sessionStorage.setItem("ih-typed", "1"); } catch (e) {}
    var cmd = tree.querySelector(".cmd");
    var lines = tree.querySelectorAll(".out");
    var text = cmd.textContent;
    cmd.textContent = "";
    tree.classList.add("is-typing");
    var i = 0;
    var tick = setInterval(function () {
      cmd.textContent = text.slice(0, ++i);
      if (i >= text.length) {
        clearInterval(tick);
        tree.classList.remove("is-typing");
        lines.forEach(function (el, n) {
          setTimeout(function () { el.classList.add("is-shown"); }, 180 + n * 55);
        });
      }
    }, 38);
  } else if (tree) {
    tree.querySelectorAll(".out").forEach(function (el) { el.classList.add("is-shown"); });
  }

  // ---- revise one ----
  var box = home.querySelector("[data-revise]");
  if (!box) return;
  var q = box.querySelector(".ih-revise__q");
  var src = box.querySelector(".ih-revise__src");
  var meta = box.querySelector(".ih-revise__meta");
  var btn = box.querySelector(".ih-revise__next");

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function render(md) {
    return esc(md).replace(/``\s?(.+?)\s?``|`([^`]+)`/g, function (_, a, b) {
      return "<code>" + (a || b) + "</code>";
    });
  }

  fetch("assets/revise.json")
    .then(function (r) { return r.json(); })
    .then(function (points) {
      if (!points.length) return;
      var chapters = new Set(points.map(function (p) { return p.url; })).size;
      meta.textContent = points.length + " points from " + chapters + " chapters";
      var last = -1;
      function show() {
        var n;
        do { n = Math.floor(Math.random() * points.length); } while (points.length > 1 && n === last);
        last = n;
        var p = points[n];
        q.innerHTML = render(p.text);
        src.innerHTML = 'From <a href="' + p.url + '">' + esc(p.title) + "</a>";
      }
      show();
      btn.hidden = false;
      btn.onclick = show;
    })
    .catch(function () {});
});
