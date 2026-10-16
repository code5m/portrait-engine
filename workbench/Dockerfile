FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends blender libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY workbench/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && python -m playwright install --with-deps chromium
COPY . /app
RUN useradd -m -u 10001 portrait && mkdir -p /app/data/workbench && chown -R portrait:portrait /app/data
ENV PORTRAIT_DATA=/app/data/workbench
USER portrait
EXPOSE 4186
# A real >=32-character PORTRAIT_TOKEN must be supplied before network binding.
CMD ["python","workbench/server.py","--host","0.0.0.0","--port","4186"]
