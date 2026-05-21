# Vibelton landing page

Self-contained static site for [vibelton.live](https://vibelton.live).

## Files

- `index.html` — the page itself, CSS embedded
- `CNAME` — tells GitHub Pages to serve at `vibelton.live`
- `.nojekyll` — tells GitHub Pages to skip Jekyll processing

No build step. No dependencies. Open `index.html` in a browser to preview.

## Deploy via GitHub Pages

Two paths. Pick one.

### Option A — separate repo (recommended for a custom domain)

Cleanest separation between app and marketing site.

```bash
# from your local machine, NOT from the app repo
mkdir vibelton-landing && cd vibelton-landing
# copy index.html, CNAME, .nojekyll into here, then:
git init -b main
git add .
git commit -m "Initial landing page"
gh repo create jimbrouw/vibelton-landing --public --source=. --push
# or, without gh CLI:
#   create the repo via github.com UI first, then:
#   git remote add origin https://github.com/jimbrouw/vibelton-landing.git
#   git push -u origin main
```

Then in the GitHub UI:

1. Repo → Settings → Pages
2. Source: `Deploy from a branch`
3. Branch: `main`, folder: `/ (root)`
4. Save
5. Custom domain: `vibelton.live` → Save
6. Tick "Enforce HTTPS" once the cert provisions (5-15 mins)

DNS at your domain registrar:
- Add four A records for the apex `vibelton.live`:
  - `185.199.108.153`
  - `185.199.109.153`
  - `185.199.110.153`
  - `185.199.111.153`
- Add a CNAME for `www.vibelton.live` → `jimbrouw.github.io`

### Option B — `/landing` subfolder of the existing `vibelton` repo

Faster, but mixes app and marketing code in one repo.

```bash
# from your existing vibelton repo
git checkout main
git pull
git checkout -b landing-page
git add landing/
git commit -m "Add vibelton.live landing page"
git push -u origin landing-page
# open a PR, merge to main
```

Then in the GitHub UI for `jimbrouw/vibelton`:

1. Repo → Settings → Pages
2. Source: `Deploy from a branch`
3. Branch: `main`, folder: `/landing`
4. Save
5. Custom domain: `vibelton.live`

Same DNS as Option A.

## Before you push

Two TODOs in `index.html` you should resolve first:

1. **Email form endpoint.** Both forms have empty `action=""`. Search the file for `Swap action=""` and pick one of the listed services (Formspree is the fastest — no signup needed, just paste the form ID).
2. **GitHub URL.** I assumed `github.com/jimbrouw/vibelton`. Update the nav link and footer link if the repo lives elsewhere.

## After it's live

Smoke checks:
- `curl -I https://vibelton.live` returns 200
- `https://vibelton.live` redirects from www correctly
- The waitlist form actually delivers an email to your inbox (test from an incognito window)
- OG preview looks right: paste the URL into Slack/Discord and check the link unfurl
