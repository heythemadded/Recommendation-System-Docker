FROM python:3.10-slim

WORKDIR /app

COPY annoteur_man.py .
COPY templates/ templates/

RUN pip install flask pika 

EXPOSE 5000

CMD ["python", "annoteur_man.py"]
