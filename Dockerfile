FROM tensorflow/tensorflow

COPY requirements.txt . 

RUN pip install -r requirements.txt 

COPY answer.py /app/answer.py
COPY answer_test.py /app/answer_test.py

CMD ["python3", "/app/answer.py"]
