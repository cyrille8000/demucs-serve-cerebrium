FROM ghcr.io/cyrille8000/ffmpeg-demucs-runpod-template:serverless

# Install FastAPI + uvicorn (base image has httpx already)
RUN pip install --no-cache-dir fastapi uvicorn

# Copy our HTTP server
COPY main.py /workspace/main.py

WORKDIR /workspace/mvsep

EXPOSE 8185

CMD ["python3", "-u", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8185"]
