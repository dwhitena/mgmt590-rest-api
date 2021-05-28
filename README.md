# MGMT 590 (Prod Scale Data Products) - Assignment #2 REST API

This repo contains the master solution for Assignment #2 in the Summer 2021 edition of MGMT 590 (Production Scale Data Products) at Purdue University. Specifically, this repo includes code and config for running a REST API for question answering using pre-trained models from [Hugging Face Transformers](https://huggingface.co/models).

## Dependencies

The REST API depends on the following:

- [Flask](https://flask.palletsprojects.com/en/2.0.x/)
- [Transformers](https://huggingface.co/transformers/)
- [TensorFlow 2.x](https://www.tensorflow.org/)
- [PyTorch](https://pytorch.org/)

The API has been tested with Python version 3.6.9 and TensorFlow 2.5.0. See [requirements.txt](requirements.txt) and our [Dockerfile](Dockerfile) for more information about supported versions of these dependencies.

## Getting Started

The Dockerized version of the API can be built as run as follows:

```
$ docker build -t mgmt590 .
$ docker run -it -p 8080:8080 mgmt590
```

Once the API is running, you can do a health check via cURL as follows:

```
$ curl http://<host>:8080 
<p>The question answering API is healthy!</p>
```

## Routes / Functionality

### List Available Models

This route allows a user to obtain a list of the models currently loaded into the server and available for inference.

Method and path:

```
GET /models
```

Expected Response Format:

```
[
  {
    "name": "distilled-bert",
    "tokenizer": "distilbert-base-uncased-distilled-squad",
    "model": "distilbert-base-uncased-distilled-squad"
  },
  {
    "name": "deepset-roberta",
    "tokenizer": "deepset/roberta-base-squad2",
    "model": "deepset/roberta-base-squad2"
  }
]
```

###Add a Model

This route allows a user to add a new model into the server and make it available for inference.

Method and path:

```
PUT /models
```

Expected Request Body Format:

```
{
  "name": "bert-tiny",
  "tokenizer": "mrm8488/bert-tiny-5-finetuned-squadv2",
  "model": "mrm8488/bert-tiny-5-finetuned-squadv2"
}
```

Expected Response Format (updated list of available models):

```
[
  {
    "name": "distilled-bert",
    "tokenizer": "distilbert-base-uncased-distilled-squad",
    "model": "distilbert-base-uncased-distilled-squad"
  },
  {
    "name": "deepset-roberta",
    "tokenizer": "deepset/roberta-base-squad2",
    "model": "deepset/roberta-base-squad2"
  },
  {
    "name": "bert-tiny",
    "tokenizer": "mrm8488/bert-tiny-5-finetuned-squadv2",
    "model": "mrm8488/bert-tiny-5-finetuned-squadv2"
  }
]
```

### Delete a Model

This route allows a user to delete an existing model on the server such that it is no longer available for inference.

Method and path:

```
DELETE /models?model=<model name>
```

Query Parameters:
- `model` (required) - The name of the model to be deleted

Expected Response Format (updated list of available models):

```
[
  {
    "name": "distilled-bert",
    "tokenizer": "distilbert-base-uncased-distilled-squad",
    "model": "distilbert-base-uncased-distilled-squad"
  },
  {
    "name": "deepset-roberta",
    "tokenizer": "deepset/roberta-base-squad2",
    "model": "deepset/roberta-base-squad2"
  }
]
```

### Answer a Question

This route uses one of the available models to answer a question, given the context provided in the JSON payload.

Method and path:

```
POST /answer?model=<model name>
```

Query Parameters:
- `model` (optional) - The name of the model to be used in answering the question. If no model name is provided use a default model.

Expected Request Body Format:

```
{
  "question": "who did holly matthews play in waterloo rd?",
  "context": "She attended the British drama school East 15 in 2005, and left after winning a high-profile role in the BBC drama Waterloo Road, playing the bully Leigh-Ann Galloway.[6] Since that role, Matthews has continued to act in BBC's Doctors, playing Connie Whitfield; in ITV's The Bill playing drug addict Josie Clarke; and she was back in the BBC soap Doctors in 2009, playing Tansy Flack."
}
```

Expected Response Format:

```
{
  "timestamp": 1621602784,
  "model": "deepset-roberta",
  "answer": "Leigh-Ann Galloway",
  "question": "who did holly matthews play in waterloo rd?",
  "context": "She attended the British drama school East 15 in 2005, and left after winning a high-profile role in the BBC drama Waterloo Road, playing the bully Leigh-Ann Galloway.[6] Since that role, Matthews has continued to act in BBC's Doctors, playing Connie Whitfield; in ITV's The Bill playing drug addict Josie Clarke; and she was back in the BBC soap Doctors in 2009, playing Tansy Flack."
}
```

### List Recently Answered Questions

This route returns recently answered questions.

Method and path:

```
GET /answer?model=<model name>&start=<start timestamp>&end=<end timestamp>
```

Query Parameters:
- `model` (optional) - Filter the results by providing a certain model name, such that the results only include answered questions that were answered using the provided model.
- `start` (required) - The starting timestamp, such that answers to questions prior to this timestamp won't be returned. This should be a Unix timestamp.
- `end` (required) - The ending timestamp, such that answers to questions after this timestamp won't be returned. This should be a Unix timestamp.

Expected Response Format (updated list of available models):

```
[
  {
    "timestamp": 1621602784,
    "model": "deepset-roberta",
    "answer": "Leigh-Ann Galloway",
    "question": "who did holly matthews play in waterloo rd?",
    "context": "She attended the British drama school East 15 in 2005, and left after winning a high-profile role in the BBC drama Waterloo Road, playing the bully Leigh-Ann Galloway.[6] Since that role, Matthews has continued to act in BBC's Doctors, playing Connie Whitfield; in ITV's The Bill playing drug addict Josie Clarke; and she was back in the BBC soap Doctors in 2009, playing Tansy Flack."
  },
  {
    "timestamp": 1621602930,
    "model": "distilled-bert",
    "answer": "Travis Pastrana",
    "question": "who did the first double backflip on a dirt bike?",
    "context": "2006 brought footage of Travis Pastrana completing a double backflip on an uphill/sand setup on his popular /"Nitro Circus/" Freestyle Motocross movies. On August 4, 2006, at X Games 12 in Los Angeles, he became the first rider to land a double backflip in competition. Having landed another trick that many had considered impossible, he vowed never to do it again."
  }
]
```


