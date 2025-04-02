FROM bitnami/spark:latest

USER root
RUN install_packages python3 python3-pip

COPY recommandation.py /app/analyse_recommandation_spark.py

RUN pip3 install pandas scikit-learn matplotlib webcolors

CMD ["spark-submit", "/app/analyse_recommandation_spark.py"]
