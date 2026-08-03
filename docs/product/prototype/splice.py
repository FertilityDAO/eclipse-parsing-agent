#!/usr/bin/env python3
"""Build prototype-globe.html from prototype.html + the globe additions.
prototype.html is never modified: it stays as the fallback."""
import io, sys

D = r"C:\Users\amoor\AppData\Local\Temp\claude\C--Users-amoor-eclipse-parsing-agent\eeb97a69-6897-407d-9ef0-c74ad9672895\scratchpad"
rd = lambda n: io.open(D + "\\" + n, encoding="utf-8").read()

html = rd("prototype.html")
css, markup, js, data = rd("globe_style.css"), rd("globe_markup.html"), rd("globe_script.js"), rd("globe.json")

def sub(old, new, why):
    global html
    if old not in html:
        sys.exit("MISSING ANCHOR: " + why)
    html = html.replace(old, new, 1)

# 1. title
sub("<title>The Eclipse Fingerprint — Clickable Prototype</title>",
    "<title>The Eclipse Fingerprint — Living Globe Prototype</title>", "title")

# 2. css
sub("/* ============================================================ reduced motion */",
    css + "\n/* ============================================================ reduced motion */", "css anchor")

# 3. markup — before the S3 verdict section
sub("<!-- ══════════════════════════════════════════════ S3 · VERDICT -->",
    markup + "\n<!-- ══════════════════════════════════════════════ S3 · VERDICT -->", "s3 anchor")

# 4. globe data payload
sub('<script id="fixtures" type="application/json">',
    '<script id="globedata" type="application/json">' + data + '</script>\n\n<script id="fixtures" type="application/json">',
    "data anchor")

# 5. register the screen
sub('const ORDER = ["s0","s1","s2","s3","s4","s5","s6","s7"];',
    'const ORDER = ["s0","s1","s2","s2g","s3","s4","s5","s6","s7"];', "ORDER")

# 6. keep the masthead out of the globe
sub('$("masthead").hidden = (id === "s0" || id === "s2");',
    '$("masthead").hidden = (id === "s0" || id === "s2" || id === "s2g");\n'
    '  if (id !== "s2g" && typeof stopGlobe === "function") stopGlobe();', "masthead")

# 7. the globe code, inside the same IIFE so it can see D / key / show()
sub("/* ─────────────────────────────────────────── wiring */",
    js + "\n/* ─────────────────────────────────────────── wiring */", "js anchor")

# 8. Compute now enters the globe rather than the line-by-line reckoning
sub('$("compute").addEventListener("click", () => { show("s2"); runReckoning(); });',
    '$("compute").addEventListener("click", () => { show("s2g"); runGlobe(); });\n'
    '$("gbSkip").addEventListener("click", () => { stopGlobe(); show("s3"); });', "compute")

# 9. dev switcher must not strand the user mid-sequence
sub('show(active === "s2" ? "s3" : active);',
    'if (active === "s2g"){ show("s2g"); runGlobe(); }\n'
    '  else show(active === "s2" ? "s3" : active);', "dev switcher")

io.open(D + r"\prototype-globe.html", "w", encoding="utf-8").write(html)
print("wrote prototype-globe.html —", len(html), "bytes")
print("prototype.html untouched —", len(rd("prototype.html")), "bytes")
