FROM python:3.10-slim

WORKDIR /app

COPY annoteur.py .

RUN pip install pillow scikit-learn webcolors numpy

CMD ["python", "annoteur.py"]
