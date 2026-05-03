# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single-file static "coming soon" landing page for **Backroom Brewery** (Middletown, VA) — `backroombreweryva.com`. The entire site is `index.html`: markup, inline `<style>`, and inline `<script>`. The only asset is `images/logo.png`.

There is **no build system, package manager, bundler, framework, or test suite**. Edits to `index.html` are the deploy artifact.

## Running locally

Open `index.html` directly in a browser, or serve the directory:

```sh
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Architecture notes worth knowing before editing

- **Single-file site by design.** Don't extract CSS/JS into separate files or introduce a build step unless explicitly asked — the deploy model is "upload this one HTML file."
- **Page sections, top to bottom:** `.stage` (hero with hand-coded SVG of the barn building), `.mission`, `.offerings`, `.signup`, `footer`. Each section is self-contained and styled in the same `<style>` block.
- **Brand palette and typography live in CSS custom properties** at `:root` (`--ink`, `--paper`, `--bronze`, `--barn`, `--wood`, `--display`, `--body`). Reuse these tokens rather than hardcoding colors/fonts. Fraunces (display) and Newsreader (body) are loaded from Google Fonts.
- **The barn illustration in `.stage-building` is hand-authored inline SVG** (gradients defined in `<defs>`, structural rects/paths for siding, gable, porch, columns, windows, flowerbeds). Coordinates are in a `0 0 1400 900` viewBox. Edit with care — geometry is interdependent (e.g., column x-positions are referenced by the arch paths and mullion lines).
- **SEO is heavy and intentional.** The `<head>` has primary meta, Open Graph, Twitter Card, geo tags, and a JSON-LD `@graph` declaring the business as `Brewery / Restaurant / EventVenue / LocalBusiness`. When changing address, hours, phone, or branding copy, update **all** of: visible text, meta description/keywords, OG/Twitter tags, and the JSON-LD block — these must stay in sync.
- **Reveal animations** are driven by an `IntersectionObserver` at the bottom of the file that adds `.visible` to elements with class `reveal`. Add `reveal` (plus `delay-1`…`delay-4`) to new elements you want to fade in.
- **Signup form** (`#signupForm`) POSTs JSON to the URL in its `action` attribute. The current value `https://YOUR-API-GATEWAY-URL.amazonaws.com/prod/signup` is a **placeholder** — replace it with the real API Gateway endpoint before shipping. The form includes a `_gotcha` honeypot field; don't remove it.

## Other files

- `response.json` — a stray AWS Bedrock error payload, unrelated to the site. Safe to ignore (or delete if doing housekeeping).
- `README.md` — contains only the project name; not a source of guidance.
