"""Render ReqShift reports as a browsable page.

ReqShift is a command line tool. This is only a viewer for what it already wrote, so
that a report can be read and shown to someone without a Markdown editor.

    py -3 viewer.py            serve every out* folder, open the browser
    py -3 viewer.py --port 8015

Nothing here analyses anything. It reads report.md files off disk.
"""
import argparse
import glob
import html
import http.server
import io
import json
import os
import socketserver
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{--bg:#f7f9f8;--fg:#17211c;--mut:#5d6b64;--line:#dde5e0;--card:#fff;
      --accent:#1a6b3c;--bad:#b3261e;--warn:#8a6d00}
@media (prefers-color-scheme:dark){:root{--bg:#121614;--fg:#e6ede9;--mut:#9aa8a1;
      --line:#2a332e;--card:#1a201d;--accent:#5fbf87;--bad:#f2837b;--warn:#e0b73a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:16px/1.65 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--line);
       padding:14px 28px;display:flex;gap:18px;align-items:baseline;flex-wrap:wrap;z-index:9}
header b{color:var(--accent);font-size:18px}
header a{color:var(--mut);text-decoration:none;font-size:14px;padding:3px 10px;
         border:1px solid var(--line);border-radius:99px}
header a:hover{color:var(--fg);border-color:var(--accent)}
header a.on{color:var(--accent);border-color:var(--accent)}
main{max-width:900px;margin:0 auto;padding:28px}
h1{font-size:28px;margin:.2em 0 .6em}
h2{font-size:21px;margin:1.7em 0 .5em;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:17px;margin:1.4em 0 .4em}
h4{font-size:15px;margin:1.2em 0 .3em;color:var(--mut)}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:14px;display:block;
      overflow-x:auto;white-space:nowrap}
th,td{border:1px solid var(--line);padding:7px 11px;text-align:left}
th{background:var(--card);font-weight:600}
code{background:var(--card);border:1px solid var(--line);border-radius:4px;
     padding:1px 5px;font-size:13px;white-space:nowrap}
pre{background:var(--card);border:1px solid var(--line);border-radius:8px;
    padding:14px;overflow-x:auto}
pre code{border:0;background:none;padding:0;white-space:pre}
blockquote{margin:1em 0;padding:.4em 1em;border-left:3px solid var(--line);color:var(--mut)}
hr{border:0;border-top:1px solid var(--line);margin:2em 0}
em{color:var(--mut)}
li{margin:.25em 0}
.empty{color:var(--mut);padding:40px 0}
"""

PAGE = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{css}</style>
<header><b>ReqShift</b>{nav}</header>
<main>{body}</main>
"""


def reports():
    out = []
    for d in sorted(glob.glob(os.path.join(HERE, "out*"))):
        p = os.path.join(d, "report.md")
        if os.path.exists(p):
            out.append((os.path.basename(d), p))
    for p in sorted(glob.glob(os.path.join(HERE, "examples", "*.report.md"))):
        out.append(("examples/" + os.path.basename(p), p))
    return out


def render(path, name, all_names):
    import markdown
    text = io.open(path, encoding="utf-8").read()
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    nav = "".join(
        '<a class="{on}" href="/{n}">{label}</a>'.format(
            on="on" if n == name else "", n=n, label=html.escape(n))
        for n in all_names)
    return PAGE.format(title="ReqShift " + name, css=CSS, nav=nav, body=body)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        found = reports()
        names = [n for n, _ in found]
        if not found:
            self._send(PAGE.format(title="ReqShift", css=CSS, nav="",
                                   body='<p class="empty">No reports yet. Run '
                                        '<code>py -3 reqshift.py &lt;file&gt;</code> first.</p>'))
            return
        want = self.path.strip("/") or names[0]
        match = dict(found).get(want)
        if not match:
            self.send_response(302)
            self.send_header("Location", "/" + names[0])
            self.end_headers()
            return
        self._send(render(match, want, names))

    def _send(self, text):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ap = argparse.ArgumentParser(description="Browse ReqShift reports.")
    ap.add_argument("--port", type=int, default=8015)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    found = reports()
    print("ReqShift viewer on http://localhost:%d" % a.port)
    for n, p in found:
        print("   /%s" % n)
    if not found:
        print("   (no reports yet)")
    if not a.no_open:
        try:
            webbrowser.open("http://localhost:%d/" % a.port)
        except Exception:
            pass
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", a.port), Handler) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    main()
