FROM python:3

ENV TZ="Europe/Amsterdam"

WORKDIR /usr/src/

COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
RUN mkdir /var/log/voerautomaat && touch /var/log/voerautomaat/voerautomaat.log && touch /var/log/voerautomaat/error.log

ENTRYPOINT ["python3", "-u", "./app/main.py", "verbose"]