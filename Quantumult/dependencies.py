"""Mirror functional QX dependencies without changing comments or static URLs.

Only recognized executable URL contexts are rewritten. Dependencies failing to
mirror retain their original URL and are reported; build can be made strict.
"""
import re
from urllib.parse import urlsplit

# Bare URLs in rewrite resource lines must be limited to script-path or
# script-url assignments; redirect destinations and ad match patterns stay put.
URL = r"https?://[^\s,;\"'<>]+"
ASSIGNMENT = re.compile(r"(?i)(\b(?:script-path|script-url)\s*=\s*|\bscript-(?:request|response)-(?:body|header)\s+)(" + URL + r")")
SCRIPTS = re.compile(r"(?i)(\bevent-interaction\s+)(" + URL + r")")
PARSER = re.compile(r"(?i)(\bresource_parser_url\s*=\s*)(" + URL + r")")
# A few QX remote rewrite files embed further script references as JS/CSS
# resource URLs in their own content. We don't crawl arbitrary JS imports.
DEPENDENCY_SUFFIXES = {".js", ".mjs", ".conf", ".snippet", ".list", ".yaml", ".yml"}


def replace_matches(text, pattern, mirror):
    def sub(match):
        url = match.group(2)
        return match.group(1) + mirror(url)
    return pattern.sub(sub, text)


def rewrite_resource(text, mirror):
    """Rewrite active script-path/script-url values; leave comments intact."""
    output = []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("#", ";", "//")):
            output.append(line)
        else:
            output.append(replace_matches(line, ASSIGNMENT, mirror))
    return "".join(output)


def rewrite_profile(text, mirror):
    """Rewrite active task JS and general resource parser JS only."""
    section = ""
    output = []
    for line in text.splitlines(keepends=True):
        matched = re.match(r"^\s*\[([^]]+)\]", line)
        if matched:
            section = matched.group(1).lower()
        if line.lstrip().startswith(("#", ";", "//")) or re.search(r"(?:^|,)\s*enabled\s*=\s*false\b", line, re.I):
            output.append(line)
        elif section == "general":
            output.append(replace_matches(line, PARSER, mirror))
        elif section == "task_local":
            output.append(replace_matches(line, SCRIPTS, mirror))
        elif section == "rewrite_local":
            output.append(replace_matches(line, ASSIGNMENT, mirror))
        else:
            output.append(line)
    return "".join(output)


def is_supported(url):
    return urlsplit(url).path.lower().endswith(tuple(DEPENDENCY_SUFFIXES))
