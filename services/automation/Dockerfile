FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --root-user-action=ignore --no-cache-dir .

EXPOSE 8095
CMD ["python", "-m", "uvicorn", "job_search_automation.app:get_app", "--factory", "--host", "0.0.0.0", "--port", "8095"]
