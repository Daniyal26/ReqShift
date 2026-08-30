"""Replay a finished run in the real UI, without paying for another extraction.

    py -3 bench/ui_harness.py runs/bottling.job.json        then open :8022

Extraction costs one to ten minutes and a real API call, which makes it a poor way
to check a change to `ui/index.html` or to show the two-step flow to somebody. This
serves the REAL `ui/index.html`, hands it one finished job that was captured
earlier, and proxies `/api/reanalyze` to a running `app.py` (8020 by default) so step 2 still
runs the actual solver. Nothing here is used by the product.

Capture a job to replay with:

    curl -s "http://127.0.0.1:8020/api/job?id=<id>" > runs/whatever.job.json

Query string, all optional:
    ?step=2&vals=1,2,1,2   fill the gap inputs in DOM order and press the button
    &back=1                then press "Change the numbers you gave"
    &open=tech             open a fold, so its sections can be checked

Useful with headless Chrome, which is how this was tested on Windows:

    chrome --headless=new --disable-gpu --user-data-dir=... \
           --virtual-time-budget=20000 --dump-dom "http://127.0.0.1:8022/?step=1"

Two traps worth knowing. `--dump-dom` prints the value ATTRIBUTE, and values set from
JavaScript never appear there, so read inputs back through `document.title` instead.
`--screenshot` prints "Access is denied" on Windows and writes the file anyway.
"""
import io
import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(os.path.dirname(HERE), "shared")
# Where the real app.py is listening. app.py defaults to 8020; override with
# REQSHIFT_APP if you started it somewhere else, or step 2 will fail with a toast.
APP = os.environ.get("REQSHIFT_APP", "http://127.0.0.1:8020")

BOOT = """
<script>
window.addEventListener('load', async () => {
  try {
    const q = new URLSearchParams(location.search);
    if (q.get('theme')) Shift.setTheme(q.get('theme'));
    if (q.get('click')){
      await new Promise(r => setTimeout(r, 400));
      document.querySelector(q.get('click')).click();
      await new Promise(r => setTimeout(r, 1200));
      const t = document.querySelector('#txt');
      document.title = 'SAMPLES ' + document.querySelector('#sampleList').children.length
        + ' LISTSHOWN ' + (!document.querySelector('#sampleList').hidden)
        + ' WORDS ' + (t.value.trim().split(/\s+/).length)
        + ' CTA ' + (document.querySelector('#goBtn').disabled ? 'disabled' : 'enabled')
        + ' MODE ' + document.querySelector('.rx-seg [aria-selected=true]').dataset.mode;
      return;
    }
    if (q.get('wide')){
      await new Promise(r => setTimeout(r, 600));
      const vw = document.documentElement.clientWidth;
      const over = [...document.querySelectorAll('*')]
        .filter(n => n.getBoundingClientRect().right > vw + 1)
        .slice(0, 6)
        .map(n => n.tagName + '.' + (n.className || '').toString().slice(0,26)
                  + '@' + Math.round(n.getBoundingClientRect().right));
      document.title = 'VW ' + vw + ' OVER ' + over.join(' | ');
      return;
    }
    if (q.get('entry')){        // stay on the input screen and show an intake note
      showIntake({name: 'customer_spec.pdf', pages: 67, words: 14911, notes: [
        'Removed 49 running header or footer lines that repeated across pages.',
        'Rejoined 95 words broken across a line end.',
        'Rejoined 599 sentences that wrapped over more than one line.']});
      document.title = 'ENTRY';
      return;
    }
    await poll('replay');
    if (q.get('step') === '2'){
      const vals = (q.get('vals') || '').split(',');
      document.querySelectorAll('.ans input').forEach((i, k) => {
        i.value = vals[k] ?? ''; i.dispatchEvent(new Event('input')); });
      document.querySelector('.gapbar .go').click();
      await new Promise(r => setTimeout(r, 2000));   // step 2 re-renders
      if (q.get('back')){
        await new Promise(r => setTimeout(r, 2500));
        const b = [...document.querySelectorAll('button')]
          .find(x => x.textContent.startsWith('Change the numbers'));
        if (!b) { document.title = 'NO BACK BUTTON'; return; }
        b.click();
      }
    }
    if (q.get('open')){
      const d = document.querySelector('.techbox[data-host="' + q.get('open') + '"]');
      if (d) { d.open = true; d.dispatchEvent(new Event('toggle')); }
      await new Promise(r => setTimeout(r, 300));
    }
    await new Promise(r => setTimeout(r, 400));
    document.title = 'RAIL ' + document.querySelectorAll('.rx-rail a').length + ' VALUES ' + JSON.stringify(
      [...document.querySelectorAll('.ans input')].map(i => i.value));
  } catch (e) { document.title = 'THREW ' + e.message; }
});
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, data, ctype):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            html = io.open(os.path.join(HERE, "ui", "index.html"),
                           encoding="utf-8").read()
            return self._send(html + BOOT, "text/html; charset=utf-8")
        if p in ("/reqshift.css", "/components.js"):
            name = os.path.basename(p)
            kind = "text/css" if name.endswith(".css") else "application/javascript"
            return self._send(io.open(os.path.join(HERE, "ui", name), "rb").read(),
                              kind + "; charset=utf-8")
        if p.startswith("/shared/"):
            name = os.path.basename(p)
            kind = {"css": "text/css", "js": "application/javascript"}.get(
                name.rsplit(".", 1)[-1])
            path = os.path.join(SHARED, name)
            if not kind or not os.path.exists(path):
                return self._send("{}", "application/json")
            return self._send(io.open(path, "rb").read(), kind + "; charset=utf-8")
        if p == "/api/job":
            return self._send(json.dumps(JOB), "application/json")
        if p == "/api/backends":
            return self._send(json.dumps({"backends": ["replay"], "model": "replay",
                                          "smt": False}), "application/json")
        if p in ("/api/examples", "/api/example"):
            # Proxied to the real server, so a click on a sample in the harness
            # exercises the same route the product uses.
            try:
                out = urllib.request.urlopen(APP + self.path, timeout=30).read()
            except Exception as e:
                out = json.dumps({"error": str(e)}).encode()
            return self._send(out, "application/json")
        return self._send("{}", "application/json")

    def do_POST(self):
        # Step 2 is proxied to the real server, so the solver genuinely runs.
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        req = urllib.request.Request(APP + self.path, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            out = urllib.request.urlopen(req, timeout=120).read()
        except Exception as e:
            out = json.dumps({"error": "app.py must be running at " + APP + ". " + str(e)}).encode()
        return self._send(out, "application/json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    JOB = json.load(io.open(sys.argv[1], encoding="utf-8"))
    JOB["id"] = "replay"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8022
    print("replaying %s  ->  http://127.0.0.1:%d" % (sys.argv[1], port))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
