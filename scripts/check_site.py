#!/usr/bin/env python3
"""Validate publication landing pages and static HTML/CSS local references.

Does not fetch external URLs or execute JavaScript/dynamic requests.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit

LANDINGS = ("index.html", "atlas/index.html", "local-ai/index.html", "hollow-square/index.html")


def css_references(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", text, flags=re.I | re.S):
        yield match.group(2).strip()
    for match in re.finditer(r"@import\s+(['\"])(.*?)\1", text, flags=re.I):
        yield match.group(2)


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []
        self.base = None
        self.has_html = False
        self.has_title = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.has_html |= tag == "html"
        self.has_title |= tag == "title"
        self.in_style = tag == "style" or self.in_style
        if tag == "base" and self.base is None:
            self.base = attributes.get("href")
        else:
            for name in ("src", "href", "poster"):
                if attributes.get(name):
                    self.references.append((self.getpos()[0], attributes[name]))
            if tag == "object" and attributes.get("data"):
                self.references.append((self.getpos()[0], attributes["data"]))
        if attributes.get("style"):
            self.references.extend((self.getpos()[0], ref) for ref in css_references(attributes["style"]))
        if tag == "meta" and attributes.get("http-equiv", "").lower() == "refresh":
            match = re.search(r"(?:^|;)\s*url\s*=\s*['\"]?([^'\"]+)", attributes.get("content", ""), re.I)
            if match:
                self.references.append((self.getpos()[0], match.group(1).strip()))

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.references.extend((self.getpos()[0], ref) for ref in css_references(data))


def check(root: Path) -> dict:
    root = root.resolve(strict=True)
    issues = []
    checked = 0
    local_hosts = {"publication.invalid"}
    if (root / "CNAME").is_file():
        local_hosts.add((root / "CNAME").read_text().strip().lower())
    for name in LANDINGS:
        if not (root / name).is_file():
            issues.append({"file": name, "issue": "Missing landing page"})
    documents = sorted([*root.rglob("*.html"), *root.rglob("*.css")])
    for document in documents:
        relative = document.relative_to(root).as_posix()
        if document.is_symlink():
            issues.append({"file": relative, "issue": "Symlink document is not read"})
            continue
        base = "https://publication.invalid/" + relative
        text = document.read_text(encoding="utf-8")
        if document.suffix == ".html":
            parser = References()
            parser.feed(text)
            if relative in LANDINGS and not (parser.has_html and parser.has_title):
                issues.append({"file": relative, "issue": "Landing must be an HTML document with a title"})
            references = parser.references
            if parser.base:
                base = urljoin(base, parser.base)
        else:
            references = [(None, ref) for ref in css_references(text)]
        for line, reference in references:
            if not reference or reference.startswith("#"):
                continue
            try:
                url = urlsplit(urljoin(base, reference))
            except ValueError:
                issues.append({"file": relative, "line": line, "issue": "Malformed reference URL; value withheld"})
                continue
            if url.scheme not in {"http", "https"} or url.hostname not in local_hosts:
                continue
            target = (root / unquote(url.path).lstrip("/")).resolve()
            if target.is_dir():
                target /= "index.html"
            checked += 1
            if not target.is_relative_to(root) or not target.is_file():
                issues.append({"file": relative, "line": line, "reference_path": url.path,
                               "issue": "Missing/outside local reference"})
    return {"scope": "Landing HTML and static src/href/poster/object/meta-refresh/CSS references; external URLs and dynamic JavaScript/srcset requests not executed",
            "html_css_documents": len(documents), "local_references_checked": checked, "issues": issues}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    report = check(args.site)
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["issues"] else 0)
