import json
from pathlib import Path
import numpy as np
import tensorflow as tf
from .llm import LLM
from huggingface_hub import hf_hub_download
from schemas.api_schemas import ChatIntention
from tensorflow.keras.preprocessing.text import tokenizer_from_json
from tensorflow.keras.preprocessing.sequence import pad_sequences

repo_id = "pollitoconpapass/intent_classification_model"
tokenizer_path = hf_hub_download(repo_id=repo_id, filename="tokenizer.json")

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

_PROMPT_DIR = Path(__file__).parent / "prompts"

def predict_chat_intention(sentence) -> tuple[str, float]:
    sequence = loaded_tokenizer.texts_to_sequences([sentence])
    padded_sequence = pad_sequences(sequence, maxlen=loaded_max_len, padding='post')

    prediction = loaded_model.predict(padded_sequence, verbose=0)[0] # -> top prediction

    predicted_class = np.argmax(prediction)
    confidence = float(prediction[predicted_class]) * 100

    intent = INTENT_MAP[predicted_class]
    return intent, confidence


def final_chat_intention_predictor(llm: LLM, sentence: str): # -> solo para cuando el confidence del modelo es bajo... (por si las moscas)
    decision, confidence = predict_chat_intention(sentence)
    print(f"=== Result of the trained model: {decision} with {confidence:.2f}% of confidence ===")

    if confidence < 85.0:
        print("Using LLM to predict the intention...")
        intention_prompt_path = _PROMPT_DIR / "chat_intention_prompt.txt"
        prompt_text = intention_prompt_path.read_text(encoding="utf-8")
        decision = llm.extract_structured(sentence, ChatIntention, prompt=prompt_text)

        print(f"=== Result of the LLM: {decision} ===")

        if decision.administrative_question:
            return "administrative_question"
        if decision.patient_information:
            return "patient_information"
        return "normal_conversation"

    return decision