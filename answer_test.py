import os
import time

from transformers.pipelines import pipeline
import pytest
from answer import create_app
import psycopg2

# initialize testing environment
models = {}
models = { 
        "default": "distilled-bert",
        "models": [
            {
                "name": "distilled-bert",
                "tokenizer": "distilbert-base-uncased-distilled-squad",
                "model": "distilbert-base-uncased-distilled-squad",
                "pipeline": pipeline('question-answering', 
                    model="distilbert-base-uncased-distilled-squad", 
                    tokenizer="distilbert-base-uncased-distilled-squad")
            }
        ]
    }
if not os.path.exists('.ssl'):
    os.makedirs('.ssl')
filecontents = os.environ.get('PG_SSLROOTCERT')
with open('.ssl/server-ca.pem', 'w') as f:
    f.write(filecontents)
filecontents = os.environ.get('PG_SSLCERT').replace("@", "=")
with open('.ssl/client-cert.pem', 'w') as f:
    f.write(filecontents)
filecontents = os.environ.get('PG_SSLKEY').replace("@", "=")
with open('.ssl/client-key.pem', 'w') as f:
    f.write(filecontents)
os.chmod(".ssl/server-ca.pem", 0o600)
os.chmod(".ssl/client-cert.pem", 0o600)
os.chmod(".ssl/client-key.pem", 0o600)
sslmode = "sslmode=verify-ca"
sslrootcert = "sslrootcert=.ssl/server-ca.pem"
sslcert = "sslcert=.ssl/client-cert.pem"
sslkey = "sslkey=.ssl/client-key.pem"
hostaddr = "hostaddr={}".format(os.environ.get('PG_HOST'))
user = "user=postgres"
password = "password={}".format(os.environ.get('PG_PASSWORD'))
dbname = "dbname=mgmt590-test"
db_connect_string = " ".join([
      sslmode,
      sslrootcert,
      sslcert,
      sslkey,
      hostaddr,
      user,
      password,
      dbname
    ])
con = psycopg2.connect(db_connect_string)
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS answers 
        (question text, context text, model text, answer text, timestamp int)""")


@pytest.fixture
def client():
    app = create_app(models, con)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# Health check route test
def test_health(client):
    r = client.get("/")
    assert 200 == r.status_code


# List model route test
def test_model_list(client):
    r = client.get("/models")
    assert 200 == r.status_code
    assert len(r.json) >= 1


# Add model route test
def test_model_add(client):
    payload = {
        "name": "deepset-roberta",
        "tokenizer": "deepset/roberta-base-squad2",
        "model": "deepset/roberta-base-squad2"
    }
    r = client.put("/models", json=payload)
    assert 200 == r.status_code


# Delete model route test
def test_model_delete(client):
    r = client.delete("/models?model=deepset-roberta")
    assert 200 == r.status_code


# Answer question route test
def test_answer(client):
    payload = {
        "question": "who did holly matthews play in waterloo rd?",
        "context": "She attended the British drama school East 15 in 2005, and left after winning a high-profile role in the BBC drama Waterloo Road, playing the bully Leigh-Ann Galloway.[6] Since that role, Matthews has continued to act in BBC's Doctors, playing Connie Whitfield; in ITV's The Bill playing drug addict Josie Clarke; and she was back in the BBC soap Doctors in 2009, playing Tansy Flack."
    }
    r = client.post("/answer", json=payload)
    assert 200 == r.status_code


# List answers route test
def test_list_answers(client):
    r = client.get("/answer?start=1622125686&end=1722298486")
    assert 200 == r.status_code
    assert len(r.json) >= 1

