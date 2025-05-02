FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY collecteur.py .


RUN apt-get update && apt-get install -y netcat-openbsd
RUN pip install -r requirements.txt

RUN mkdir -p /data/images

CMD ["python","-u","collecteur.py"]

