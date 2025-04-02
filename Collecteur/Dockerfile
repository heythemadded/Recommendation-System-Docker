FROM python:3.10-slim

WORKDIR /app

COPY collecteur.py .

RUN pip install requests Pillow

RUN mkdir -p /data/images

CMD ["python", "collecteur.py"]

