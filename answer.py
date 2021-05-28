import os
import time
import sqlite3

from transformers.pipelines import pipeline
from flask import Flask
from flask import request, jsonify


#--------------#
#  VARIABLES   #
#--------------#

# Create my flask app
app = Flask(__name__)

# Create a variable that will hold our models in memory
models = {}

# The database file
db = 'answers.db'

#--------------#
#    ROUTES    #
#--------------#

# Define a handler for the / path, which
# returns a message and allows Cloud Run to 
# health check the API.
@app.route("/")
def hello_world():
    return "<p>The question answering API is healthy!</p>"


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
            data['question'], data['context'])
    timestamp = int(time.time())

    # Insert our answer in the database
    con = sqlite3.connect(db)
    cur = con.cursor()
    sql = "INSERT INTO answers VALUES ('{question}','{context}','{model}','{answer}',{timestamp})"
    cur.execute(sql.format(
        question=data['question'].replace("'", "''"), 
        context=data['context'].replace("'", "''"), 
        model=model_name, 
        answer=answer, 
        timestamp=str(timestamp)))
    con.commit()
    con.close()

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
    con = sqlite3.connect(db)
    cur = con.cursor()
    out = []
    for row in cur.execute(sql_rev):
        out.append({
            "question": row[0],
            "context": row[1],
            "answer": row[2],
            "model": row[3],
            "timestamp": row[4]
        })
    con.close()

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
    if not validate_model(data['name']):
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



#--------------#
#  FUNCTIONS   #
#--------------#

# Validate that a model is available
def validate_model(model_name):
    
    # Get the loaded models
    model_names = []
    for m in models['models']:
        model_names.append(m['name'])

    return model_name in model_names


# Answer a question with a given model name
def answer_question(model_name, question, context):
    
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
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''CREATE TABLE answers
               (question text, context text, model text, answer text, timestamp int)''')
    con.commit()
    con.close()

    # Run our Flask app and start listening for requests!
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), threaded=True)
