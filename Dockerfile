# Serving image for the outbound voice agent.
#
# WHAT IS AND IS NOT IN HERE
#
# NOT: PyTorch, parler-tts, any TTS model. ADR-005 renders every approved line offline, so the
# serving box plays WAV files and never loads a speech synthesiser. That is why this image is
# ~1 GB and not ~6 GB, and why a bank's InfoSec review has one large unsigned dependency to
# assess (onnxruntime) instead of three.
#
# IS: onnxruntime for ASR, the engine, the content pack, and the pre-rendered audio cache.
#
# The ASR model is NOT baked in - it is ~2.5 GB, it changes on a different cadence from the code,
# and ADR-006 means the choice is not final. Mount it:
#
#   docker run -p 8078:8078 \
#     -e OUTBOUND_API_TOKEN=... \
#     -v /srv/models:/app/models:ro \
#     -v /srv/audio_cache:/app/audio_cache:ro \
#     -v /srv/runs:/app/runs \
#     outbound-voice:0.1.0
#
# India-resident by construction (constraint 4): nothing in this image calls out. The only
# network the runtime needs is the partner's SIP and CRM.

FROM python:3.11-slim

# libsndfile for soundfile; nothing else. Kept deliberately thin - every apt package is
# something a security review has to account for.
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/   ./engine/
COPY apps/     ./apps/
COPY tools/    ./tools/
COPY content/  ./content/
COPY cost_model.py .

# Fail the BUILD if the content pack is unsound. A pack with a dangling transition or a pitch
# reachable without its disclosure must never reach a registry, let alone a customer. This is
# the same validator CI runs, at the last moment it can still stop something.
RUN python tools/validate_content.py

# Non-root. Obvious, and routinely skipped.
RUN useradd --create-home --uid 10001 bot && chown -R bot:bot /app
USER bot

ENV OUTBOUND_API_PORT=8078 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

EXPOSE 8078

# /ready fails closed when the content pack is unloadable, so an orchestrator pulls a broken
# deploy out of rotation instead of serving calls from it.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8078/ready',timeout=4).status==200 else 1)"

CMD ["python", "apps/api.py"]
