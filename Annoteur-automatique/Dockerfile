FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY annoteur.py .

RUN apt-get update && apt-get install -y netcat-openbsd
RUN pip install -r requirements.txt

CMD ["python", "annoteur.py"]
