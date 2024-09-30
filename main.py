import openai

openai.api_key = 'sua_chave_api_aqui'  # Use variáveis de ambiente para segurança

openai.api_key = 'chave_API';

messages = [
    {"role": "system", "content": "Você é um assistente."},
]

input_message = input('Esperando input: ')
messages.append({"role": "user", "content": input_message})

while input_message != 'fim':
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=messages,
        temperature=1,
        max_tokens=200
    )

    resposta = response['choices'][0]['message']['content']
    print("Resposta: ", resposta)

    input_message = input('Esperando input: ')
    messages.append({"role": "user", "content": input_message})

link do tutorial    https://www.youtube.com/watch?v=VQZWtBW-Vbs&ab_channel=Alura    