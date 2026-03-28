FROM python:3.11-slim

# Keep Python behavior predictable in containers.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

# We intentionally skip apt-get here because some restricted networks block
# Debian HTTP mirrors during builds. The current Python dependencies are wheels,
# so we can keep the image smaller and the build more reliable without OS packages.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /app/requirements.txt

COPY app /app/app

EXPOSE 8101

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8101"]
