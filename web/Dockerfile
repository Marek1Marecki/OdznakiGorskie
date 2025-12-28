# 1. Obraz bazowy: Python 3.13 na lekkim Debianie (Bookworm)
FROM python:3.13-slim-bookworm

# 2. Zmienne środowiskowe dla Pythona
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Katalog roboczy w kontenerze
WORKDIR /app

# 4. Instalacja zależności systemowych (GDAL/GEOS dla PostGIS)
# 'netcat-openbsd' przyda się do skryptu entrypoint (czekanie na bazę)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     binutils \
     libproj-dev \
     gdal-bin \
     libgdal-dev \
     libpq-dev \
     gcc \
     netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

# 5. Instalacja zależności Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 6. Kopiowanie kodu aplikacji
COPY . /app/

# 7. (Opcjonalnie) Skrypt startowy - utworzymy go za chwilę
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 8. Domyślna komenda (uruchomienie serwera)
ENTRYPOINT ["/app/entrypoint.sh"]
