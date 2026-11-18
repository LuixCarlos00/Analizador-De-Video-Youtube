"""Transcrição de arquivos de áudio usando o reconhecimento de fala do Google."""

import io
import threading

from .config import IDIOMA_TRANSCRICAO, TAMANHO_TRECHO_MS

TIMEOUT_SERVICO_S = 30


class TranscricaoCancelada(Exception):
    """O usuário cancelou a transcrição."""


class ErroServicoTranscricao(Exception):
    """O serviço de reconhecimento de fala ficou indisponível (rede, cota, etc.)."""


def calcular_trechos(duracao_ms, tamanho_trecho_ms):
    """Divide a duração total em intervalos (início, fim) de no máximo ``tamanho_trecho_ms``.

    Args:
        duracao_ms (int): duração do áudio em milissegundos.
        tamanho_trecho_ms (int): tamanho máximo de cada trecho em milissegundos.

    Returns:
        list[tuple[int, int]]: intervalos sem trechos vazios.

    Raises:
        ValueError: se ``tamanho_trecho_ms`` não for positivo.
    """
    if tamanho_trecho_ms <= 0:
        raise ValueError("O tamanho do trecho deve ser positivo.")
    return [
        (inicio, min(inicio + tamanho_trecho_ms, duracao_ms))
        for inicio in range(0, max(duracao_ms, 0), tamanho_trecho_ms)
    ]


def _carregar_audio_padrao(caminho):
    from pydub import AudioSegment  # import tardio: requer ffmpeg instalado

    return AudioSegment.from_file(caminho)


class Transcritor:
    """Transcreve áudio dividindo-o em trechos curtos e enviando cada um ao Google.

    Os trechos são exportados em memória (BytesIO), sem gerar arquivos temporários
    na pasta onde o programa está rodando.
    """

    def __init__(self, idioma=IDIOMA_TRANSCRICAO, tamanho_trecho_ms=TAMANHO_TRECHO_MS,
                 carregar_audio=_carregar_audio_padrao, reconhecedor=None):
        """
        Args:
            idioma (str): código do idioma (ex.: "pt-BR").
            tamanho_trecho_ms (int): tamanho de cada trecho enviado ao serviço.
            carregar_audio (Callable[[str], AudioSegment]): carrega o arquivo; injetável para testes.
            reconhecedor (speech_recognition.Recognizer | None): injetável para testes.
        """
        self.idioma = idioma
        self.tamanho_trecho_ms = tamanho_trecho_ms
        self._carregar_audio = carregar_audio
        self._reconhecedor = reconhecedor
        self._cancelar = threading.Event()

    def cancelar(self):
        """Interrompe a transcrição antes do próximo trecho."""
        self._cancelar.set()

    def transcrever(self, caminho_audio, ao_progredir=None):
        """Transcreve o arquivo de áudio inteiro.

        Args:
            caminho_audio (str): arquivo mp3/mp4/m4a/wav etc.
            ao_progredir (Callable[[float], None] | None): recebe o percentual (0-100).

        Returns:
            tuple[str, int]: (texto transcrito, quantidade de trechos que não foram entendidos).

        Raises:
            TranscricaoCancelada: o usuário cancelou.
            ErroServicoTranscricao: falha de comunicação com o serviço do Google.
        """
        import speech_recognition as sr

        reconhecedor = self._reconhecedor or sr.Recognizer()
        # Sem limite, uma rede instável trava o trecho para sempre (e o Cancelar só age entre trechos).
        reconhecedor.operation_timeout = TIMEOUT_SERVICO_S
        audio = self._carregar_audio(caminho_audio)
        trechos = calcular_trechos(len(audio), self.tamanho_trecho_ms)

        partes_texto, nao_entendidos = [], 0
        for indice, (inicio, fim) in enumerate(trechos, start=1):
            if self._cancelar.is_set():
                raise TranscricaoCancelada()

            buffer = io.BytesIO()
            audio[inicio:fim].export(buffer, format="wav")
            buffer.seek(0)
            with sr.AudioFile(buffer) as fonte:
                dados = reconhecedor.record(fonte)

            try:
                partes_texto.append(reconhecedor.recognize_google(dados, language=self.idioma))
            except sr.UnknownValueError:
                nao_entendidos += 1  # silêncio/ruído: segue para o próximo trecho
            except (sr.RequestError, OSError) as erro:  # OSError inclui timeout de rede
                raise ErroServicoTranscricao(
                    f"Falha no serviço de reconhecimento de fala (trecho {indice}): {erro}"
                ) from erro

            if ao_progredir:
                ao_progredir(indice / len(trechos) * 100)

        return " ".join(partes_texto).strip(), nao_entendidos
