import json
import tensorflow as tf
from huggingface_hub import hf_hub_download
from tensorflow.keras.preprocessing.text import tokenizer_from_json
from tensorflow.keras.preprocessing.sequence import pad_sequences


HF_REPO_ID = "pollitoconpapass/aldimi-dorm"

model_local_path = hf_hub_download(HF_REPO_ID, filename='dni_classification_model.h5')
model = tf.keras.models.load_model(model_local_path)

tokenizer_local_path = hf_hub_download(HF_REPO_ID, filename='tokenizer.json')
with open(tokenizer_local_path, 'r', encoding='utf-8') as f:
    full_tokenizer_data = json.load(f)

max_len = full_tokenizer_data['max_len']
tokenizer_for_keras_load = {
    'class_name': full_tokenizer_data['class_name'],
    'config': full_tokenizer_data['config']
}

tokenizer_config_json_string = json.dumps(tokenizer_for_keras_load)
tokenizer = tokenizer_from_json(tokenizer_config_json_string)

def predict_document_type(sentence: str):
    sequence = tokenizer.texts_to_sequences([sentence])
    padded_sequence = pad_sequences(sequence, max_len)
    prediction_prob = model.predict(padded_sequence, verbose=0)[0][0]
    
    doc_type = "medical_report" if prediction_prob >= 0.5 else "dni"
    return doc_type
