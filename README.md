# Portfolio

Personal portfolio site with a graph visualizer rendered by Python, NetworkX,
and Matplotlib. The generated site assets live in `static/` and are served as a
Cloudflare Workers Static Assets deployment.

## Render assets

The Python project renders `hero-loop.mp4` and `hero-poster.webp` into `static/`:

```bash
uv run python export_video.py
```

See [`DEPLOY.md`](DEPLOY.md) for local preview and Cloudflare deployment instructions.