FROM python:3.11

WORKDIR /app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# instalăm supervisor
RUN apt-get update && apt-get install -y supervisor

# copiem aplicația
COPY app/ .

# copiem configurarea supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-n"]