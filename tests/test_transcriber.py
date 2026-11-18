import pytest
import speech_recognition as sr

from analisador.transcriber import (
    ErroServicoTranscricao,
    TranscricaoCancelada,
    Transcritor,
    calcular_trechos,
)


@pytest.mark.parametrize("duracao,tamanho,esperado", [
    (25_000, 10_000, [(0, 10_000), (10_000, 20_000), (20_000, 25_000)]),
    (20_000, 10_000, [(0, 10_000), (10_000, 20_000)]),  # sem trecho vazio no final
    (3_000, 10_000, [(0, 3_000)]),
    (0, 10_000, []),
])
def test_calcular_trechos(duracao, tamanho, esperado):
    assert calcular_trechos(duracao, tamanho) == esperado


def test_calcular_trechos_tamanho_invalido():
    with pytest.raises(ValueError):
        calcular_trechos(1000, 0)


class AudioFalso:
    """Imita um AudioSegment: len() em ms, fatiamento e export de WAV silencioso válido."""

    def __init__(self, duracao_ms):
        self._duracao = duracao_ms

    def __len__(self):
        return self._duracao

    def __getitem__(self, fatia):
        return AudioFalso(fatia.stop - fatia.start)

    def export(self, buffer, format):
        import wave
        with wave.open(buffer, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x00\x00" * 80)


class ReconhecedorFalso(sr.Recognizer):
    def __init__(self, respostas):
        super().__init__()
        self._respostas = list(respostas)

    def recognize_google(self, _dados, language):
        assert language == "pt-BR"
        resposta = self._respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def criar(respostas, duracao_ms=30_000):
    return Transcritor(carregar_audio=lambda _c: AudioFalso(duracao_ms),
                       reconhecedor=ReconhecedorFalso(respostas))


def test_transcreve_juntando_trechos_e_conta_nao_entendidos():
    progresso = []
    texto, nao_entendidos = criar(["olá", sr.UnknownValueError(), "mundo"]).transcrever("x.mp3", progresso.append)
    assert texto == "olá mundo"
    assert nao_entendidos == 1
    assert progresso[-1] == 100


def test_erro_de_servico_vira_excecao_clara():
    with pytest.raises(ErroServicoTranscricao, match="trecho 2"):
        criar(["olá", sr.RequestError("sem internet")]).transcrever("x.mp3")


def test_timeout_de_rede_vira_erro_de_servico_e_timeout_e_configurado():
    t = criar([TimeoutError("timed out")])
    with pytest.raises(ErroServicoTranscricao, match="trecho 1"):
        t.transcrever("x.mp3")
    assert t._reconhecedor.operation_timeout == 30


def test_cancelar_interrompe():
    t = criar(["a", "b", "c"])
    with pytest.raises(TranscricaoCancelada):
        t.transcrever("x.mp3", lambda _p: t.cancelar())
