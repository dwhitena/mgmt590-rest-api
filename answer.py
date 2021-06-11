import os
import time

from werkzeug.utils import secure_filename
from transformers.pipelines import pipeline
from flask import Flask
from flask import request, jsonify
import psycopg2

# Process SSL certificates
if not os.path.exists('.ssl'):
    os.makedirs('.ssl')

filecontents = os.environ.get('GCS_CREDS')
decoded_creds = base64.b64decode(filecontents)
with open('/app/creds.json', 'w') as f:
    f.write(decoded_creds)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '/app/creds.json'

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

# Format DB connection information
sslmode = "sslmode=verify-ca"
sslrootcert = "sslrootcert=.ssl/server-ca.pem"
sslcert = "sslcert=.ssl/client-cert.pem"
sslkey = "sslkey=.ssl/client-key.pem"
hostaddr = "hostaddr={}".format(os.environ.get('PG_HOST'))
user = "user=postgres"
password = "password={}".format(os.environ.get('PG_PASSWORD'))
dbname = "dbname=mgmt590"

# Construct database connect string
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

# Connect to your postgres DB
con = psycopg2.connect(db_connect_string)

# Create a variable that will hold our models in memory
models = {}


#-----------------#
#   FLASK APP     #
#-----------------#

def create_app(models, con):

    # Create my flask app
    app = Flask(__name__)

    #--------------#
    #    ROUTES    #
    #--------------#

    # Define a handler for the / path, which
    # returns a message and allows Cloud Run to 
    # health check the API.
    @app.route("/")
    def hello_world():
        return "<p>The question answering API is healthy!</p>"

    @app.route('/upload', methods = ['POST'])
    def upload_file():
      f = request.files['file']
      f.save(os.path.join)('/tmp', secure_filename(f.filename)))
      return jsonify({"upload_status": 'file uploaded successfully'})

    # Define a handler for the /answer path, which
    # processes a JSON payload with a question and
    # context and returns an answer using a Hugging
    # Face model.
    @app.route("/answer", methods=['POST'])
    def answer():

        # Get the request body data
        data = request.json

        # Validate model name if given
        if request.args.get('model') != None:
            if not validate_model(request.args.get('model')):
                return "Model not found", 400

        # Answer the question
        answer, model_name = answer_question(request.args.get('model'), 
                data['question'], data['context'], models)
        timestamp = int(time.time())

        # Insert our answer in the database
        cur = con.cursor()
        sql = "INSERT INTO answers VALUES ('{question}','{context}','{model}','{answer}',{timestamp})"
        cur.execute(sql.format(
            question=data['question'].replace("'", "''"), 
            context=data['context'].replace("'", "''"), 
            model=model_name, 
            answer=answer, 
            timestamp=str(timestamp)))
        con.commit()

        # Create the response body.
        out = {
            "question": data['question'],
            "context": data['context'],
            "answer": answer,
            "model": model_name,
            "timestamp": timestamp
        }

        return jsonify(out)


    # List historical answers from the database.
    @app.route("/answer", methods=['GET'])
    def list_answer():

        # Validate timestamps
        if request.args.get('start') == None or request.args.get('end') == None:
            return "Query timestamps not provided", 400

        # Prep SQL query
        if request.args.get('model') != None:
            sql = "SELECT * FROM answers WHERE timestamp >= {start} AND timestamp <= {end} AND model == '{model}'"
            sql_rev = sql.format(start=request.args.get('start'), 
                    end=request.args.get('end'), model=request.args.get('model'))
        else:
            sql = 'SELECT * FROM answers WHERE timestamp >= {start} AND timestamp <= {end}'
            sql_rev = sql.format(start=request.args.get('start'), end=request.args.get('end'))

        # Query the database
        cur = con.cursor()
        cur.execute(sql_rev)
        out = []
        for row in cur.fetchall():
            out.append({
                "question": row[0],
                "context": row[1],
                "answer": row[2],
                "model": row[3],
                "timestamp": row[4]
            })

        return jsonify(out)


    # List models currently available for inference
    @app.route("/models", methods=['GET'])
    def list_model():

        # Get the loaded models
        models_loaded = []
        for m in models['models']:
            models_loaded.append({
                'name': m['name'],
                'tokenizer': m['tokenizer'],
                'model': m['model']
            })

        return jsonify(models_loaded)


    # Add a model to the models available for inference
    @app.route("/models", methods=['PUT'])
    def add_model():

        # Get the request body data
        data = request.json
        
        # Load the provided model
        if not validate_model(data['name'], models):
            models_rev = []
            for m in models['models']:
                models_rev.append(m)
            models_rev.append({
                    'name': data['name'],
                    'tokenizer': data['tokenizer'],
                    'model': data['model'],
                    'pipeline': pipeline('question-answering', 
                        model=data['model'], 
                        tokenizer=data['tokenizer'])
            })
            models['models'] = models_rev

        # Get the loaded models
        models_loaded = []
        for m in models['models']:
            models_loaded.append({
                'name': m['name'],
                'tokenizer': m['tokenizer'],
                'model': m['model']
            })

        return jsonify(models_loaded)


    # Delete a model from the models available for inference
    @app.route("/models", methods=['DELETE'])
    def delete_model():

        # Validate model name if given
        if request.args.get('model') == None:
            return "Model name not provided in query string", 400

        # Error if trying to delete default model
        if request.args.get('model') == models['default']:
            return "Can't delete default model", 400

        # Load the provided model
        models_rev = []
        for m in models['models']:
            if m['name'] != request.args.get('model'):
                models_rev.append(m)
        models['models'] = models_rev

        # Get the loaded models
        models_loaded = []
        for m in models['models']:
            models_loaded.append({
                'name': m['name'],
                'tokenizer': m['tokenizer'],
                'model': m['model']
            })

        return jsonify(models_loaded)

    return app


#--------------#
#  FUNCTIONS   #
#--------------#

# Validate that a model is available
def validate_model(model_name, models):
    
    # Get the loaded models
    model_names = []
    for m in models['models']:
        model_names.append(m['name'])

    return model_name in model_names


# Answer a question with a given model name
def answer_question(model_name, question, context, models):
    
    # Get the right model pipeline
    if model_name == None:
        for m in models['models']:
            if m['name'] == models['default']:
                model_name = m['name']
                hg_comp = m['pipeline']
    else:
        for m in models['models']:
            if m['name'] == model_name:
                hg_comp = m['pipeline']

    # Answer the answer
    answer = hg_comp({'question': question, 'context': context})['answer']

    return answer, model_name


# Run main by default if running "python answer.py"
if __name__ == '__main__':

    # Initialize our default model.
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

    # Database setup
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS answers 
        (question text, context text, model text, answer text, timestamp int)""")

    # Create our Flask App
    app = create_app(models, con)

    # Run our Flask app and start listening for requests!
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), threaded=True)
