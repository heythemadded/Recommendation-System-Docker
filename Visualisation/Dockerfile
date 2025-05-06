FROM python:3.8

WORKDIR /app

COPY requirements.txt .
COPY recommandation.ipynb .
COPY visualisation.ipynb .

RUN apt-get update && apt-get install -y netcat-openbsd
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8888

ENV NAME World

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]