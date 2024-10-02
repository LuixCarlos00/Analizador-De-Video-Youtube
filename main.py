import google.generativeai as genai
import pyttsx3
import speech_recognition as sr

# pip install SpeechRecognition
# pip install pyaudio
# pip install pyttsx3
# pip install --upgrade
# pip install google-generativeai 

def main():
    assistente_falante = True
    ligar_microfone = True

    genai.configure(api_key="AIzaSyAXCVnzZWz04KnBYbR27yQhvbpLlWk3gvw")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

    model = genai.GenerativeModel('gemini-pro')
    chat = model.start_chat(history=[])

    ### configuração de voz
    if assistente_falante:
        var = pyttsx3.init()
        Voz = var.getProperty('voices')
        var.setProperty('rate', 180)  # velocidade da fala 180
        
        bem_vindo = "# Ola seja bem vindo ao Garoto de Progama #"
        print("")
        print(len(bem_vindo) * "#")
        print(bem_vindo)
        print("  !False it's Funny Because it's True #")
        print(len(bem_vindo) * "#")
        print("###   Digite ou fale 'desligar' para encerrar    ###")
        print("")

        print("\n===Lista de Vozes - Verifique o número===\n")
        voz_portugues = None

        for indice, voz in enumerate(Voz):
            print(indice, voz.name)
            if "Portuguese" in voz.name:  # Procura por voz em português
                voz_portugues = voz.id  # Armazena a voz em português

        if voz_portugues is not None:
            var.setProperty('voice', voz_portugues)
        else:
            print("Voz em português não encontrada!")

    if ligar_microfone:
        pop = sr.Recognizer()
        mic = sr.Microphone()

   

    while True:
        if ligar_microfone:
            with mic as fonte:
                pop.adjust_for_ambient_noise(fonte)
                print("Fale alguma coisa (ou diga 'desligar')" )
                audio = pop.listen(fonte)
                print("Enviando para reconhecimento")
                try:
                    texto = pop.recognize_google(audio, language="pt-BR")
                    print("Você disse: {}".format(texto))
                except Exception as e:
                    print("Não entendi o que você disse. Erro:", e)
                    texto = ""
        else:
            texto = input("Escreva sua mensagem (ou #sair): ")

        if texto.lower() == "desligar":
            break

        if texto.strip():
            texto_Modificado = "Responda de uma maneira sarcastica e sem educação "+ texto
            response = chat.send_message(texto_Modificado)
            print("Gemini:", response.text, "\n")

            if assistente_falante:
                var.say(response.text)
                var.runAndWait()
        else:
            print("Nenhuma entrada válida para enviar.")

    print("Encerrando Chat")

if __name__ == '__main__':
    main()
