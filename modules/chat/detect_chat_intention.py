import json
import numpy as np
import tensorflow as tf
from huggingface_hub import hf_hub_download
from tensorflow.keras.preprocessing.text import tokenizer_from_json
from tensorflow.keras.preprocessing.sequence import pad_sequences

repo_id = "pollitoconpapass/intent_classification_model"
tokenizer_path = hf_hub_download(repo_id=repo_id, filename="tokenizer.json")

# with open(tokenizer_path, 'r', encoding='utf-8') as f:
#     loaded_tokenizer_config = json.load(f)
#     loaded_tokenizer = tokenizer_from_json(loaded_tokenizer_config)

with open(tokenizer_path, 'r', encoding='utf-8') as f:
    loaded_tokenizer_config = json.load(f)
    loaded_max_len = loaded_tokenizer_config['config']['max_len']
    del loaded_tokenizer_config['config']['max_len']
    loaded_tokenizer = tokenizer_from_json(json.dumps(loaded_tokenizer_config))

model_file_path = hf_hub_download(repo_id=repo_id, filename="intent_classification_model.keras")
loaded_model = tf.keras.models.load_model(model_file_path)

INTENT_MAP = {
    0: "normal_conversation",
    1: "patient_information",
    2: "administrative_question"
}

def predict_single_sentence(sentence, max_len=10) -> tuple[str, float]:
    # Preprocess the whole sentence
    sequence = loaded_tokenizer.texts_to_sequences([sentence])
    padded_sequence = pad_sequences(sequence, maxlen=max_len, padding='post')

    prediction = loaded_model.predict(padded_sequence, verbose=0)[0] # -> get 1st prediction

    # Prediction + confidence
    predicted_class = np.argmax(prediction)
    confidence = prediction[predicted_class] * 100

    intent = INTENT_MAP[predicted_class]
    return intent, confidence