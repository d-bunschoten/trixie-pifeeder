FROM python:3

WORKDIR /usr/src/

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir /var/log/voerautomaat && touch /var/log/voerautomaat/voerautomaat.log && touch /var/log/voerautomaat/error.log

COPY . .

CMD [ "/bin/bash" ]