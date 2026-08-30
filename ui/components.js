/* ReqShift components.
 *
 * Factory functions, not a framework. Each returns a DOM node, so the page is
 * composed rather than written out as one long string of HTML. There is no
 * build step in this project and adding one would mean rewriting the server
 * and the way GoalShift shares its design system, so this is the component
 * architecture the existing stack can actually carry.
 *
 * Nothing here talks to the API. Callers pass data in and hand back handlers.
 */
(function (global) {
  "use strict";

  /* ------------------------------------------------------------ helpers */
  const esc = s => String(s ?? "").replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  const SVGNS = "http://www.w3.org/2000/svg";
  function svg(view, inner, cls) {
    const s = document.createElementNS(SVGNS, "svg");
    s.setAttribute("viewBox", view);
    s.setAttribute("fill", "none");
    if (cls) s.setAttribute("class", cls);
    s.innerHTML = inner;
    return s;
  }

  /* ---------------------------------------------------------------- icons
     Line icons at 24, stroked with currentColor. Deliberately plain: this is
     an analysis tool, so an icon is a label, never an illustration. */
  const ICON = {
    paste:  '<path d="M9 4h6v3H9zM7 5H5v15h14V5h-2" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    upload: '<path d="M12 15V4m0 0L8 8m4-4 4 4M4 16v3h16v-3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    link:   '<path d="M10 13a4 4 0 0 0 5.7 0l2.6-2.6a4 4 0 1 0-5.7-5.7L11 6.3M14 11a4 4 0 0 0-5.7 0l-2.6 2.6a4 4 0 1 0 5.7 5.7L13 17.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    layers: '<path d="M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5M3 17l9 5 9-5" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    proof:  '<path d="M4 6h5M4 18h5M20 6h-5M20 18h-5M6.5 6v12M17.5 6v12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><rect x="10.6" y="10.6" width="2.8" height="2.8" fill="currentColor"/>',
    moon:   '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    sun:    '<circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.6"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    page:   '<path d="M6 3h8l4 4v14H6z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M14 3v4h4" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    arrow:  '<path d="M5 12h13m0 0-5-5m5 5-5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    check:  '<path d="M4 6h4M4 18h4M20 6h-4M20 18h-4M6 6v12M18 6v12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
  };
  const icon = (name, cls) => svg("0 0 24 24", ICON[name] || "", cls);

  /* ====================================================================
     Logo
     ====================================================================
     Requirement, shift, proof, in three marks and nothing else.

       [   a bracket. In engineering notation a bracket is a bound, which is
           exactly what this product is about: the constraint a specification
           places on how many of a thing there can be.
       ]   the same bracket, mirrored and SHIFTED down. Two states of one
           system, offset. That offset is the whole product name.
       .   a filled square between them, sitting on the axis where the two
           brackets line up. The tombstone that closes a proof, which is real
           mathematical notation and not a tick.

     Those three shapes sit INSIDE a filled brand square, and that container is
     not decoration. Rendered bare, the mark was a smudge at 16 and 22px: the
     brackets read as two black blobs and the proof square disappeared into
     them. Reversing it out of a solid field separates the shapes at every size
     and gives the mark the presence a bare outline never had beside a wordmark.
     It also puts ReqShift in the same family as GoalShift, whose mark is built
     the same way, which is honest since one is the front end of the other.  */

  /* The geometry, once, so the live mark and the favicon cannot drift apart.
     `field` fills the container, `ink` draws the three shapes reversed out of it. */
  function markShapes(field, ink, w) {
    return '<rect x="1" y="1" width="22" height="22" rx="5.6" fill="' + field + '"/>' +
      '<path d="M10 5.6H6.2V12.4" stroke="' + ink + '" stroke-width="' + w +
        '" stroke-linecap="square" fill="none"/>' +
      '<path d="M14 18.4h3.8V11.6" stroke="' + ink + '" stroke-width="' + w +
        '" stroke-linecap="square" fill="none"/>' +
      '<rect x="10.4" y="10.4" width="3.2" height="3.2" rx="0.4" fill="' + ink + '"/>';
  }

  function logoMark(size, opts) {
    opts = opts || {};
    const s = svg("0 0 24 24", "", "rx-mark");
    s.setAttribute("width", size);
    s.setAttribute("height", size);
    s.setAttribute("aria-hidden", "true");
    // Heavier strokes below 20px, or the shapes close up at favicon size.
    s.innerHTML = markShapes(opts.field || "var(--brand)",
                             opts.ink || "var(--brand-ink)",
                             size < 20 ? 2.7 : 2.4);
    return s;
  }

  function Logo(opts) {
    opts = opts || {};
    const a = el(opts.href ? "a" : "div", "rx-logo");
    if (opts.href) { a.href = opts.href; a.setAttribute("aria-label", "ReqShift home"); }
    a.appendChild(logoMark(opts.size || 22, opts));
    if (opts.wordmark !== false) {
      a.appendChild(el("span", "rx-word",
        '<span class="a">Req</span><span class="b">Shift</span>'));
    }
    return a;
  }

  /* The same mark as a data URI, for <link rel="icon"> and app icons. */
  function faviconHref(dark) {
    // Literal colours, never CSS variables: a data URI has no stylesheet to
    // resolve them against and the mark would come out unpainted.
    const field = dark ? "#3fae6d" : "#1f6f43";
    const s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' +
      markShapes(field, "#ffffff", 2.7) + "</svg>";
    return "data:image/svg+xml," + encodeURIComponent(s);
  }

  function applyFavicon() {
    const dark = document.documentElement.dataset.theme === "dark";
    let l = document.querySelector('link[rel="icon"]');
    if (!l) { l = document.createElement("link"); l.rel = "icon"; document.head.appendChild(l); }
    l.type = "image/svg+xml";
    l.href = faviconHref(dark);
  }

  /* ==================================================================== */
  /* TopNavigation                                                        */
  /* ==================================================================== */

  function TopNavigation(opts) {
    opts = opts || {};
    const nav = el("nav", "rx-nav");
    nav.setAttribute("aria-label", "Primary");
    const inner = el("div", "rx-nav-in");
    inner.appendChild(Logo({ href: opts.home || "#top", size: 22 }));

    const links = el("div", "rx-navlinks");
    (opts.links || []).forEach(l => {
      const a = el("a", null, esc(l.label));
      a.href = l.href;
      if (l.onClick) a.addEventListener("click", e => { e.preventDefault(); l.onClick(); });
      links.appendChild(a);
    });
    inner.appendChild(links);

    const end = el("div", "rx-nav-end");
    (opts.actions || []).forEach(n => end.appendChild(n));
    inner.appendChild(end);
    nav.appendChild(inner);
    return nav;
  }

  /* Figure Mode: a spec switch, not a dark button. */
  function FigureModeButton(onToggle, isOn) {
    const b = el("button", "rx-figbtn",
      '<span class="dot"></span><span>Figure Mode</span>');
    b.type = "button";
    b.title = "Redraw every diagram for print: white ground, thicker strokes, "
            + "greyscale-safe colours";
    const sync = () => b.setAttribute("aria-pressed", isOn() ? "true" : "false");
    b.addEventListener("click", () => { onToggle(); sync(); });
    sync();
    return b;
  }

  function ThemeButton(onToggle, current) {
    const b = el("button", "rx-iconbtn");
    b.type = "button";
    const sync = () => {
      const dark = current() === "dark";
      b.innerHTML = "";
      b.appendChild(icon(dark ? "sun" : "moon"));
      b.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      b.title = b.getAttribute("aria-label");
    };
    b.addEventListener("click", () => { onToggle(); sync(); applyFavicon(); });
    sync();
    return b;
  }

  /* ==================================================================== */
  /* Small pieces                                                         */
  /* ==================================================================== */

  function TechnicalLabel(text, tone) {
    return el("div", "rx-label" + (tone ? " on-" + tone : ""), esc(text));
  }

  function PageHeader(o) {
    const h = el("header");
    if (o.label) h.appendChild(TechnicalLabel(o.label, o.tone));
    h.appendChild(el("h2", null, esc(o.title)));
    if (o.lede) h.appendChild(el("p", null, o.lede));
    return h;
  }

  function Button(label, o) {
    o = o || {};
    const b = el("button", "rx-btn " + (o.variant || "secondary") + (o.size ? " " + o.size : ""));
    b.type = "button";
    if (o.icon) b.appendChild(icon(o.icon));
    b.appendChild(el("span", null, esc(label)));
    if (o.onClick) b.addEventListener("click", o.onClick);
    if (o.disabled) b.disabled = true;
    if (o.title) b.title = o.title;
    return b;
  }

  function SeverityBadge(kind, label) {
    return el("span", "rx-sev " + kind, esc(label || kind));
  }

  function SourceReference(sentence, label) {
    const n = el("div", "rx-src");
    n.appendChild(el("div", "k", esc(label || "From your specification")));
    n.appendChild(el("div", "q", '"' + esc(sentence) + '"'));
    return n;
  }

  function MetricCard(o) {
    const n = el("div", "rx-metric" + (o.tone ? " " + o.tone : ""));
    n.appendChild(el("div", "k", esc(o.label)));
    n.appendChild(el("div", "v", esc(String(o.value))));
    if (o.unit) n.appendChild(el("div", "u", esc(o.unit)));
    if (o.flag) n.appendChild(el("div", "flag", esc(o.flag)));
    return n;
  }

  function MetricRow(cards) {
    const row = el("div", "rx-metrics");
    cards.forEach(c => row.appendChild(c instanceof Node ? c : MetricCard(c)));
    return row;
  }

  /* A gap, as the customer reads it: what is missing, why it matters, and the
     sentence it came from. The severity is passed in, never guessed here. */
  function GapCard(o) {
    const n = el("div", "rx-gap " + (o.severity || "medium"));
    const top = el("div", "rx-gap-top");
    top.appendChild(el("h3", null, esc(o.title)));
    top.appendChild(SeverityBadge(o.severity, o.severityLabel));
    n.appendChild(top);
    if (o.what) n.appendChild(el("p", "what", esc(o.what)));
    if (o.why) n.appendChild(el("div", "why", o.why));
    if (o.source) n.appendChild(SourceReference(o.source, o.sourceLabel));
    if (o.body) n.appendChild(o.body);
    return n;
  }

  function PipelineStep(o) {
    const n = el("div", "rx-step" + (o.tone ? " is-" + o.tone : ""));
    n.appendChild(el("div", "n", esc(o.index)));
    n.appendChild(el("h3", null, esc(o.title)));
    if (o.lede) n.appendChild(el("p", null, o.lede));
    if (o.points) {
      const ul = el("ul");
      o.points.forEach(p => ul.appendChild(el("li", null, p)));
      n.appendChild(ul);
    }
    return n;
  }

  function EvidenceCard(o) {
    const n = el("div");
    n.className = "rx-trust";
    (o.items || []).forEach(it => {
      const d = el("div");
      const t = el("div", "t");
      if (it.icon) t.appendChild(icon(it.icon));
      t.appendChild(el("span", null, esc(it.title)));
      d.appendChild(t);
      if (it.body) d.appendChild(el("div", "s", it.body));
      if (it.chain) d.appendChild(el("div", "chain", it.chain));
      n.appendChild(d);
    });
    return n;
  }

  function EmptyState(o) {
    const n = el("div", "rx-empty");
    n.appendChild(el("h3", null, esc(o.title)));
    if (o.body) n.appendChild(el("p", null, o.body));
    return n;
  }

  global.RX = {
    el, esc, icon, svg,
    Logo, logoMark, faviconHref, applyFavicon,
    TopNavigation, FigureModeButton, ThemeButton,
    TechnicalLabel, PageHeader, Button, SeverityBadge, SourceReference,
    MetricCard, MetricRow, GapCard, PipelineStep, EvidenceCard, EmptyState
  };
})(window);
