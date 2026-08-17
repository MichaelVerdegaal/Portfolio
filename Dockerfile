FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY ./src .

RUN uv sync --group serve  --no-editable

EXPOSE 8040

# Run the application
CMD ["uv", "run", "uvicorn", "src.app:app", "--port", "8040"]