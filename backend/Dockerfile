FROM python:3.13.16-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
RUN mkdir -p /var/lib/aerolinea/private-media /var/lib/aerolinea/passwords \
    && chown -R app:app /var/lib/aerolinea \
    && chmod 700 /var/lib/aerolinea/private-media /var/lib/aerolinea/passwords
ENV PRIVATE_MEDIA_ROOT=/var/lib/aerolinea/private-media \
    PASSWORD_CORPUS_DIR=/var/lib/aerolinea/passwords/current

FROM base AS development
COPY requirements/development.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
COPY --chown=app:app . /app
USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.development
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production
COPY requirements/production.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
COPY --chown=app:app . /app
USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.production
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "config/gunicorn.py"]
