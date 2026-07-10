import instructor
from groq import Groq
from typing import TypeVar

T = TypeVar('T')

class LLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Groq(api_key=self.api_key)
        self.client_instructor = instructor.from_groq(Groq(api_key=self.api_key), mode=instructor.Mode.JSON)
        self.model_name = "openai/gpt-oss-20b"


    def generate_response(self, question: str, prompt: str = None, context: str = None, conversation_history: str = None):
        full_system = prompt + (f"\n\nContexto médico del paciente:\n{context}" if context else "") + (f"\n\nHistorial de conversación:\n{conversation_history}" if conversation_history else "")

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
            max_tokens=5000,
            stream=True
        )

        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def extract_structured(self, text: str, schema: T, prompt: str) -> T:
        response = self.client_instructor.chat.completions.create(
            model=self.model_name,
            response_model=schema,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            stream=False
        )

        return response
