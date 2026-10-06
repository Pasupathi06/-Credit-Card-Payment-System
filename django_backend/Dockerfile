FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir \
    django \
    djangorestframework \
    djangorestframework-simplejwt \
    mysqlclient \
    django-cors-headers \
    drf-spectacular \
    coverage

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]