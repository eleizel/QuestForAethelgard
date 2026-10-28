"""Injects PWA metadata and manifest into Pyxel's generated index.html."""

from pathlib import Path

dist_index = Path("dist/index.html")
if not dist_index.exists():
    raise FileNotFoundError("dist/index.html not found")

html = dist_index.read_text(encoding="utf-8")

tags = """
    <!-- PWA Manifest & Meta -->
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#000000">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link rel="apple-touch-icon" href="icon-512.png">
</head>"""

# Case-insensitive replacement of </head> or fallback before <body>
if "</head>" in html:
    html = html.replace("</head>", tags, 1)
elif "</HEAD>" in html:
    html = html.replace("</HEAD>", tags, 1)
else:
    html = tags + "\n" + html

dist_index.write_text(html, encoding="utf-8")
print("Successfully patched dist/index.html with PWA tags.")