# Deploy

The site is deployed as Cloudflare Workers Static Assets from the `static/`
directory. No Python web server is part of the serving path.

## Prerequisites

- Bun installed locally.
- Node.js kept installed as a compatibility fallback for Wrangler entrypoints.
- A Cloudflare account with the target zone available.

Install the pinned project dependencies:

```bash
bun install
```

Authenticate Wrangler:

```bash
bunx wrangler login
bunx wrangler whoami
```

## Local preview

Preview the same asset configuration used in production:

```bash
bun run dev
```

This runs `bunx wrangler dev` and uses `wrangler.jsonc`, including the `static/`
asset directory, trailing-slash handling, and 404 behavior.

## Render updated assets

When the graph or animation changes, regenerate the committed site assets:

```bash
uv run python export_video.py
```

Check that `static/hero-loop.mp4` and `static/hero-poster.webp` are present before
deploying.

## Deploy from the CLI

From the repository root:

```bash
bun run deploy
```

The deploy script runs:

```bash
bunx wrangler deploy
```

The committed `wrangler.jsonc` publishes `static/` at the site root and returns
real 404 responses for missing files.

## Workers Builds

1. Commit and push `wrangler.jsonc`, `package.json`, `bun.lock`, and `static/` to
   `MichaelVerdegaal/Portfolio`.
2. In Cloudflare, open **Workers & Pages** → **Create application** → **Get
   started** next to **Import a repository**.
3. Select the repository and authorize the Cloudflare GitHub app if prompted.
4. Use the repository root as the root directory.
5. Set the build command to:

   ```text
   bun install
   ```

6. Set the deploy command to:

   ```text
   bunx wrangler deploy
   ```

7. Save and deploy, then verify the generated `workers.dev` URL.

Workers Builds should detect Bun from `bun.lock`. Check the first build log for
lines similar to:

```text
Detected the following tools from environment: bun@..., nodejs@...
Installing project dependencies: bun install --frozen-lockfile
```

If the build uses a different package manager, keep the explicit `bun install`
build command above rather than relying on automatic detection.

Preview builds for non-production branches can be enabled under **Settings** →
**Build** → **Branch control**.

## Custom domain

After the Worker is live:

1. Open the Worker in **Workers & Pages**.
2. Go to **Settings** → **Domains & Routes** → **Add** → **Custom Domain**.
3. Add `mverdegaal.com` and, if desired, `www.mverdegaal.com`.
4. Wait for DNS and TLS activation, then test both HTTPS URLs.

Cloudflare manages the DNS record and certificate when the zone is already in
the same account.

## Verify the deployment

Check these paths on the deployed domain:

- `/`
- `/favicon.ico`
- `/fonts/jetbrains-mono-latin.woff2`
- `/hero-poster.webp`
- `/hero-loop.mp4`
- `/robots.txt`
- `/llms.txt`

The static site uses root-relative asset URLs, so none of these paths should
contain `/static/`.
