## Local preview

Preview the same static-asset configuration used in production:

```sh
npm install
npm run dev
```

## Render assets

The Python project renders `hero-loop.mp4` and `hero-poster.webp` into `static/`:

```sh
uv run python export_video.py
```

## Deploy

```sh
npm run deploy
```