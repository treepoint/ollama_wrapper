Специальный класс-обработчик ответов от Ollama для:
- Кеширования ответов через SQlite. Если придет второй такой же запрос с такими же параметрами и промптами, то он будет взят из кэша.
- Проверками ответа:
    - На лету (is_response_stream_have_errors) — для примера проверяется наличие китайского языка в ответе.
    - Всего ответа сразу (is_all_response_have_errors) — для примера проверяется что длина ответа больше 0.

Пример использования:

```
from OllamaWrapper import OllamaWrapper


ollama_wrapper = OllamaWrapper()

options  = {
    "temperature" : 0.3,
    "mirostat" : 2,
    "mirostat_tau" : 5, 
    "mirostat_eta" : 0.1,
    "repeat_last_n" : 0,
    "seed" : 0
}

model = "qwen3:14b"
num_ctx = 3000

system = "You are helpful and accurate assistant. You should to give adequate, meaningful and accurate answer to user query"
prompt = "Скажи, сколько будет два плюс два?"

response = ollama_wrapper.request(prompt, model, system, num_ctx, options, save_to_cache = True)
```