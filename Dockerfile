FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir \
    --timeout=300 \
    --retries=5 \
    --index-url https://repo.hmirror.ir/python/simple \
    -r requirements.txt

COPY . .

RUN mkdir -p logs

RUN adduser --disabled-password --no-create-home django && \
    chown -R django:django /app

USER django

EXPOSE 80

CMD ["bash", "entrypoint"]