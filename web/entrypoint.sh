#!/bin/sh

# Sprawdź, czy baza danych to Postgres
if [ "$DATABASE" = "postgres" ]
then
    echo "Czekam na bazę danych PostgreSQL..."

    # Pętla sprawdzająca dostępność hosta i portu
    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
      sleep 0.5
    done

    echo "PostgreSQL wystartował!"
fi

# Wykonaj migracje (bezpieczne w dev, w prod robi się to ręcznie)
# python manage.py migrate

# Uruchom komendę przekazaną w Dockerfile (czyli runserver)
exec "$@"
