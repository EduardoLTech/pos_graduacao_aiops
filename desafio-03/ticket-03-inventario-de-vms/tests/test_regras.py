import pytest

from inventario_vm import baseline, coleta, inventario, regras
from inventario_vm.conexao import ResultadoComando
from tests.amostras import (
    COM_SWAP, OS_RELEASE, UNIDADES, SessaoFalsa, chave_publica, linha_de_chaves, saidas_conforme,
)

BASE = baseline.carregar()
SSHD_ROOT_NO = "uid=0 rc=0\npermitrootlogin no\nauthorizedkeysfile .ssh/authorized_keys\nauthorizedkeyscommand none\n"


def _conformidade(**trocas):
    saidas = saidas_conforme()
    saidas.update(trocas)
    resultado = inventario.montar(coleta.coletar(SessaoFalsa(saidas)))
    return {e["regra"]: e for e in regras.avaliar(BASE, resultado)}, resultado


def _regra(nome, **trocas):
    return _conformidade(**trocas)[0][nome]


def _chaves_totalmente_legiveis(*linhas_de_chave):
    conteudo = "".join(l + "\n" for l in linhas_de_chave)
    return linha_de_chaves("coleta", "lida", conteudo) + "\nfim\n"


# --- host sem desvio, entradas e resumo (P1, P3) -------------------------------------------


def test_host_conforme_com_usuario_comum_sai_4():
    por_regra, _ = _conformidade()
    lista = list(por_regra.values())
    assert [e["regra"] for e in lista] == list(BASE.regras)
    assert not [e for e in lista if e["veredito"] == "desvio"]
    assert por_regra["ssh.login_de_root"]["veredito"] == "nao_verificado"
    assert por_regra["chaves_ssh.emitidas_por"]["veredito"] == "nao_verificado"
    assert regras.codigo_de_saida(lista) == 4


def test_host_totalmente_legivel_e_conforme_sai_0():
    chaves = _chaves_totalmente_legiveis(chave_publica("coleta@metacortex-platform"))
    por_regra, _ = _conformidade(sshd=SSHD_ROOT_NO, chaves=chaves)
    lista = list(por_regra.values())
    assert {e["veredito"] for e in lista} == {"conforme"}
    assert regras.codigo_de_saida(lista) == 0


def test_resumo_soma_as_entradas_e_por_severidade_so_desvios():
    por_regra, _ = _conformidade(swap=COM_SWAP, kernel="5.15.0-118-generic\n")
    lista = list(por_regra.values())
    resumo = regras.resumir(lista)
    assert resumo["conforme"] + resumo["desvio"] + resumo["nao_verificado"] == 11
    assert resumo["por_severidade"] == {"critico": 1, "alto": 0, "medio": 1}


@pytest.mark.parametrize("vereditos, codigo", [
    ({"desvio", "nao_verificado"}, 1),
    ({"conforme", "nao_verificado"}, 4),
    ({"conforme"}, 0),
])
def test_precedencia_do_codigo_de_saida(vereditos, codigo):
    assert regras.codigo_de_saida([{"veredito": v} for v in vereditos]) == codigo


# --- desvio e não verificado (P2, P4) ------------------------------------------------------


def test_desvio_carrega_severidade_e_esperado_encontrado():
    e = _regra("swap.habilitado", swap=COM_SWAP)
    # encontrado com o tipo do esperado (comparável por máquina); a frase é só do Markdown
    assert e == {"regra": "swap.habilitado", "esperado": False, "encontrado": True,
                 "veredito": "desvio", "severidade": "critico", "encontrado_texto": "true (4G)"}


def test_nao_verificado_nao_tem_severidade_e_tem_motivo():
    e = _regra("ssh.login_de_root")
    assert "severidade" not in e
    assert e["motivo"] == "exige privilégio que o usuário da coleta não tem"
    assert e["encontrado"] is None


def test_falha_de_uma_leitura_so_afeta_suas_regras():
    por_regra, _ = _conformidade(unidades=ResultadoComando(127, ""))
    assert por_regra["servicos.ativos"]["veredito"] == "nao_verificado"
    assert por_regra["servicos.proibidos"]["motivo"].startswith("falha de coleta")
    assert por_regra["swap.habilitado"]["veredito"] == "conforme"


# --- versões (P16, P17) ---------------------------------------------------------------------


def test_kernel_comparado_como_numero():
    e = _regra("kernel.versao_minima", kernel="6.11.0-1015-gcp\n")
    assert (e["veredito"], e["encontrado"]) == ("conforme", "6.11.0-1015-gcp")


def test_kernel_abaixo_do_minimo():
    e = _regra("kernel.versao_minima", kernel="5.15.0-118-generic\n")
    assert (e["veredito"], e["severidade"]) == ("desvio", "medio")


def test_versao_do_so_abaixo_do_minimo():
    e = _regra("so.versao_minima", os_release=OS_RELEASE.replace("24.04", "20.04"))
    assert (e["veredito"], e["severidade"], e["encontrado"]) == ("desvio", "alto", "20.04.1")


def test_outra_distribuicao():
    por_regra, _ = _conformidade(os_release='ID=debian\nVERSION_ID="12"\n')
    assert (por_regra["so.distribuicao"]["veredito"], por_regra["so.distribuicao"]["severidade"]) == ("desvio", "alto")
    versao = por_regra["so.versao_minima"]
    assert (versao["veredito"], versao["motivo"], versao["encontrado"]) == (
        "nao_verificado", "distribuição diferente da esperada", "12")


# --- serviços (P18, P19) ---------------------------------------------------------------------


def test_ssh_satisfeito_so_pelo_socket():
    unidades = UNIDADES.replace("ssh.service            loaded active running OpenBSD Secure Shell server\n", "")
    assert _regra("servicos.ativos", unidades=unidades)["veredito"] == "conforme"


def test_nome_de_pacote_diferente_nao_satisfaz():
    unidades = UNIDADES.replace("node_exporter.service ", "prometheus-node-exporter.service ")
    e = _regra("servicos.ativos", unidades=unidades)
    assert (e["veredito"], e["encontrado"]) == ("desvio", ["ssh", "containerd", "chrony"])
    assert e["encontrado_texto"] == "ausente: node_exporter"


def test_rpcbind_ativo_e_proibido():
    unidades = UNIDADES + "rpcbind.socket loaded active listening RPCbind Server Activation Socket\n"
    e = _regra("servicos.proibidos", unidades=unidades)
    assert (e["veredito"], e["severidade"], e["encontrado"]) == ("desvio", "alto", ["rpcbind.socket"])


# --- portas (P21–P23) ------------------------------------------------------------------------


@pytest.mark.parametrize("bind, interno", [
    ("127.0.0.1", True), ("::1", True), ("10.128.0.5", True), ("172.20.1.1", True),
    ("192.168.0.9", True), ("fd00::1", True), ("169.254.169.254", True), ("fe80::1", True),
    ("0.0.0.0", False), ("::", False), ("*", False), ("34.74.10.20", False),
    ("172.32.0.1", False), ("::ffff:10.0.0.1", True),
])
def test_classificacao_do_bind(bind, interno):
    assert regras.bind_interno(bind) is interno


def test_porta_publica_nao_permitida():
    portas = "LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 4096 0.0.0.0:8080 0.0.0.0:*\n"
    e = _regra("portas_em_escuta.publicas_permitidas", portas=portas)
    assert (e["veredito"], e["severidade"]) == ("desvio", "critico")
    assert e["encontrado"] == [{"porta": 22, "bind": "0.0.0.0"}, {"porta": 8080, "bind": "0.0.0.0"}]
    assert e["encontrado_texto"] == "8080 em 0.0.0.0"


def test_porta_22_so_interna_e_conforme():
    e = _regra("portas_em_escuta.publicas_permitidas", portas="LISTEN 0 4096 10.0.0.2:22 0.0.0.0:*\n")
    assert e["veredito"] == "conforme"


def test_9100_aberta_para_o_mundo():
    portas = "LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 4096 0.0.0.0:9100 0.0.0.0:*\n"
    por_regra, _ = _conformidade(portas=portas)
    e = por_regra["portas_em_escuta.somente_rede_interna"]
    assert (e["veredito"], e["severidade"], e["encontrado_texto"]) == ("desvio", "critico", "9100 em 0.0.0.0")
    assert e["encontrado"] == [{"porta": 9100, "bind": "0.0.0.0"}]
    # a 9100 é julgada só por somente_rede_interna: o mesmo bind não vira dois desvios
    assert por_regra["portas_em_escuta.publicas_permitidas"]["veredito"] == "conforme"
    assert regras.resumir(list(por_regra.values()))["por_severidade"]["critico"] == 1


def test_9100_sem_escuta_e_conforme():
    e = _regra("portas_em_escuta.somente_rede_interna", portas="LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*\n")
    assert (e["veredito"], e["encontrado"], e["encontrado_texto"]) == ("conforme", [], "sem escuta")


# --- chaves (P25) ------------------------------------------------------------------------------


def test_chave_pessoal_e_desvio_mesmo_com_fontes_nao_lidas():
    conteudo = chave_publica("coleta@metacortex-platform") + "\n" + chave_publica("neo@laptop") + "\n"
    chaves = "\n".join([linha_de_chaves("root", "sem_permissao"),
                        linha_de_chaves("coleta", "lida", conteudo), "fim"])
    e = _regra("chaves_ssh.emitidas_por", chaves=chaves)
    assert (e["veredito"], e["severidade"], e["encontrado_texto"]) == ("desvio", "critico", "neo@laptop")
    assert e["encontrado"] == ["coleta@metacortex-platform", "neo@laptop"]


def test_chave_sem_comentario_nao_e_da_plataforma():
    e = _regra("chaves_ssh.emitidas_por", chaves=_chaves_totalmente_legiveis(chave_publica()), sshd=SSHD_ROOT_NO)
    assert (e["veredito"], e["encontrado"], e["encontrado_texto"]) == ("desvio", [None], "(sem comentário)")


def test_sufixo_precisa_ser_exato():
    chaves = _chaves_totalmente_legiveis(chave_publica("x@metacortex-platform.evil"))
    assert _regra("chaves_ssh.emitidas_por", chaves=chaves, sshd=SSHD_ROOT_NO)["veredito"] == "desvio"


def test_fontes_nao_lidas_sem_desvio_e_nao_verificado():
    e = _regra("chaves_ssh.emitidas_por")
    assert e["veredito"] == "nao_verificado"
    assert "root" in e["motivo"]
    assert e["encontrado"] == ["coleta@metacortex-platform"]
    assert e["encontrado_texto"] == "1 chave(s) lida(s), todas da plataforma"


# --- login de root e ntp (P26, P27) --------------------------------------------------------------


def test_prohibit_password_e_desvio():
    e = _regra("ssh.login_de_root", sshd="uid=0 rc=0\npermitrootlogin prohibit-password\n")
    assert (e["veredito"], e["severidade"]) == ("desvio", "alto")


def test_login_de_root_no_e_conforme():
    assert _regra("ssh.login_de_root", sshd=SSHD_ROOT_NO)["veredito"] == "conforme"


def test_relogio_nao_sincronizado():
    e = _regra("ntp.sincronizado", ntp="5 65\n")  # TIME_ERROR; STA_PLL | STA_UNSYNC
    assert (e["veredito"], e["severidade"], e["encontrado"]) == ("desvio", "medio", False)
    assert e["encontrado_texto"] == "false (chrony)"
