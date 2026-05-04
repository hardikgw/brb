# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single-file static "coming soon" landing page for **Backroom Brewery** (Middletown, VA) — `backroombreweryva.com`. All site content lives in `web/`: `web/index.html` (markup + inline `<style>` + inline `<script>`) and `web/images/logo.png`.

There is **no build system, package manager, bundler, framework, or test suite**. Edits to `web/index.html` are the deploy artifact.

## Running locally

Serve the `web/` directory:

```sh
cd web && python3 -m http.server 8000   # then visit http://localhost:8000
```

## Architecture notes worth knowing before editing

- **Single-file site by design.** Don't extract CSS/JS into separate files or introduce a build step unless explicitly asked — the deploy model is "upload this one HTML file."
- **Page sections, top to bottom:** `.stage` (hero with hand-coded SVG of the barn building), `.mission`, `.offerings`, `.signup`, `footer`. Each section is self-contained and styled in the same `<style>` block.
- **Brand palette and typography live in CSS custom properties** at `:root` (`--ink`, `--paper`, `--bronze`, `--barn`, `--wood`, `--display`, `--body`). Reuse these tokens rather than hardcoding colors/fonts. Fraunces (display) and Newsreader (body) are loaded from Google Fonts.
- **The barn illustration in `.stage-building` is hand-authored inline SVG** (gradients defined in `<defs>`, structural rects/paths for siding, gable, porch, columns, windows, flowerbeds). Coordinates are in a `0 0 1400 900` viewBox. Edit with care — geometry is interdependent (e.g., column x-positions are referenced by the arch paths and mullion lines).
- **SEO is heavy and intentional.** The `<head>` has primary meta, Open Graph, Twitter Card, geo tags, and a JSON-LD `@graph` declaring the business as `Brewery / Restaurant / EventVenue / LocalBusiness`. When changing address, hours, phone, or branding copy, update **all** of: visible text, meta description/keywords, OG/Twitter tags, and the JSON-LD block — these must stay in sync.
- **Reveal animations** are driven by an `IntersectionObserver` at the bottom of the file that adds `.visible` to elements with class `reveal`. Add `reveal` (plus `delay-1`…`delay-4`) to new elements you want to fade in.
- **Signup form** (`#signupForm` in `web/index.html`) POSTs JSON to the URL in its `action` attribute. The current value `https://YOUR-API-GATEWAY-URL.amazonaws.com/prod/signup` is a **placeholder** — replace it with the real API Gateway endpoint before shipping. The form includes a `_gotcha` honeypot field; don't remove it.
- **ALTCHA captcha gates the submit button.** The `<altcha-widget>` (loaded from jsdelivr CDN) fetches a signed challenge from `challengeurl` (also a `YOUR-API-GATEWAY-URL...` placeholder) and computes a proof-of-work. The "Notify Me…" button is hidden via CSS until the widget fires `statechange` with `state === 'verified'`, at which point the form gets a `.altcha-verified` class. `handleSignup` also short-circuits if the class is missing (so Enter-key submissions can't bypass it). The widget injects a hidden `altcha` field into the form payload that the signup Lambda re-verifies server-side.

## Infrastructure (`iac/`)

Python AWS CDK app that uploads the static site to a **pre-existing** S3 bucket and deploys the signup Lambda. Each AWS resource lives in its own file under `iac/stacks/resources/`.

- **Config is layered YAML.** `iac/config/common.yml` holds shared defaults; `iac/config/<env>.yml` (e.g. `dev.yml`) holds per-env overrides and is deep-merged on top. Pick env via `BRB_ENV` (default `dev`). The bucket is **referenced by name from config** (`existingBucketName`) — the stack does not create or own it.
- **Tagging + naming convention** lives in `iac/stacks/naming.py` as the `Naming` class. Pattern is `<prefix>-<core>-<suffix>` where `prefix` defaults to `project` and `suffix` defaults to `env` (both can be overridden in config). The "core" is **owned by each resource construct** as a class-level `CORE_NAME` constant (e.g. `SignupFunction.CORE_NAME = "signup-lambda"`, `SiteStack.CORE_NAME = "static-site"`) — there are **no resource names in config**. `naming.apply_default_tags(self)` is called once on the stack, and CDK's tag aspect propagates `project` + `env` tags to every taggable resource inside. **Exception**: `existingBucketName` is the literal name of an external bucket — it doesn't follow this convention.
- **`SiteDeployment` runs with `prune=False`** because the bucket is shared/pre-existing — never let it delete objects it didn't put there.
- **`SignupFunction`** code lives at `lambda/signup/handler.py` (project root, **not** under `iac/`). Path is set in `iac/config/common.yml` as `lambda.codePath` (relative to project root). The CDK stack does not create API Gateway; wire that separately when ready, then update the form `action` in `web/index.html` (currently a `YOUR-API-GATEWAY-URL...` placeholder).
- **`AltchaChallengeFunction`** at `lambda/altcha-challenge/handler.py` issues HMAC-signed ALTCHA proof-of-work challenges for the captcha widget. Both this Lambda and the signup Lambda share an HMAC secret resolved at synth in this order: `ALTCHA_HMAC_KEY` env var → `altcha.hmacKey` in config → auto-generated and cached at `iac/.altcha-hmac-key` (gitignored). For prod/CI, **always set `ALTCHA_HMAC_KEY`** so the key is reproducible across machines; the on-disk cache is a single-developer convenience only. Wire this Lambda to a separate API Gateway route (matching `challengeurl` in the widget).
- **`SiteDeployment` source path** is `../web` (relative to `iac/`), set in `iac/config/common.yml` as `siteSourcePath`. Only `web/` gets uploaded — repo metadata, IaC, and docs are not part of the deploy bundle.
- **Deploy:** `cd iac && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cdk deploy` (requires AWS credentials and `cdk bootstrap` in the target account/region).

## Other files

- `response.json` — a stray AWS Bedrock error payload, unrelated to the site. Safe to ignore (or delete if doing housekeeping).
- `README.md` — contains only the project name; not a source of guidance.
