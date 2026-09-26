from inventario_vm import coleta, inventario
from inventario_vm.coleta import FALHA, LIDA, SEM_PRIVILEGIO
from inventario_vm.conexao import ResultadoComando
from tests.amostras import (
    COM_SWAP, SessaoFalsa, b64, chave_publica, linha_de_chaves, saidas_conforme,
)


def _montar(**trocas):
    saidas = saidas_conforme()
    saidas.update(trocas)
    return inventario.montar(coleta.coletar(SessaoFalsa(saidas)))


def test_inventario_de_host_conforme():
    r = _montar()
    inv = r.inventario
    assert r.hostname == "construct-node-14"
    assert inv["so"] == {"distribuicao": "ubuntu", "versao": "24.04.1"}
    assert inv["kernel"] == {"versao": "6.8.0-1015-gcp"}
    assert [s["nome"] for s in inv["servicos"]] == sorted(s["nome"] for s in inv["servicos"])
    assert {"nome": "ssh.socket", "tipo": "socket", "estado": "active"} in inv["servicos"]
    assert inv["swap"] == {"habilitado": False, "tamanho": None}
    # processo ilegível (outro usuário), mas conta dona e unidade vêm do ss -e (PRD P24)
    assert inv["portas_em_escuta"] == [
        {"porta": 22, "bind": "0.0.0.0", "processo": None, "conta": "root", "unidade": "ssh.socket"},
        {"porta": 22, "bind": "::", "processo": None, "conta": "root", "unidade": "ssh.socket"},
        {"porta": 53, "bind": "127.0.0.53", "processo": None, "conta": "systemd-resolve",
         "unidade": "systemd-resolved.service"},
        {"porta": 9100, "bind": "10.128.0.5", "processo": None, "conta": "node_exporter",
         "unidade": "node_exporter.service"},
    ]
    assert inv["chaves_ssh"] == [{"identificacao": "coleta@metacortex-platform", "conta": "coleta"}]
    assert inv["chaves_ssh_fontes_nao_lidas"] == [inventario.FONTE_CONFIG_SSHD, "root"]
    assert inv["ssh"] == {"login_de_root": None}
    assert inv["ntp"] == {"sincronizado": True, "mecanismo": "chrony"}
    assert r.evidencia["sshd"].status == SEM_PRIVILEGIO


def test_todas_as_leituras_levam_o_prefixo_de_idioma():
    sessao = SessaoFalsa(saidas_conforme())
    coleta.coletar(sessao)
    assert all(c.startswith("export LC_ALL=C LANG=C; ") for c in sessao.comandos)


def test_swap_de_4_gib():
    assert _montar(swap=COM_SWAP).inventario["swap"] == {"habilitado": True, "tamanho": "4G"}


def test_formatar_tamanho():
    assert inventario.formatar_tamanho(512 * 1024**2) == "512M"
    assert inventario.formatar_tamanho(1536 * 1024**2) == "2G"
    assert inventario.formatar_tamanho(2 * 1024**4) == "2T"


def test_swap_de_1_gib_com_pagina_de_cabecalho_descontada():
    # Medido no laboratório: swapfile de 1 GiB aparece como 1048572 KiB no /proc/swaps.
    swap = "Filename\tType\tSize\tUsed\tPriority\n/swapfile file 1048572 0 -1\n"
    assert _montar(swap=swap).inventario["swap"] == {"habilitado": True, "tamanho": "1G"}


def test_processo_dono_quando_legivel():
    portas = ('LISTEN 0 4096 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=812,fd=3)) '
              'uid:1002 ino:1 sk:1 cgroup:/user.slice/user-1002.slice/session-5.scope <->\n')
    assert _montar(portas=portas).inventario["portas_em_escuta"] == [
        {"porta": 8080, "bind": "127.0.0.1", "processo": "python3", "conta": "coleta",
         "unidade": "session-5.scope"}
    ]


def test_contas_ilegiveis_deixam_conta_nula():
    r = _montar(contas=ResultadoComando(2, ""))
    assert {p["conta"] for p in r.inventario["portas_em_escuta"]} == {None}
    assert r.evidencia["contas"].status == FALHA


def test_script_de_chaves_percorre_todas_as_contas():
    # Chave em conta com shell nologin/false ainda autentica: nenhuma conta pode ser pulada.
    assert "nologin" not in coleta.SCRIPT_CHAVES and "continue" not in coleta.SCRIPT_CHAVES


def test_ss_bind_curinga_e_ipv6_com_interface():
    portas = "LISTEN 0 128 *:9100 *:*\nLISTEN 0 128 [fe80::1%ens4]:9100 [::]:*\n"
    binds = [p["bind"] for p in _montar(portas=portas).inventario["portas_em_escuta"]]
    assert binds == ["*", "fe80::1"]


def test_os_release_sem_revisao_pontual():
    saida = 'ID=debian\nVERSION_ID="12"\nVERSION="12 (bookworm)"\n'
    assert _montar(os_release=saida).inventario["so"] == {"distribuicao": "debian", "versao": "12"}


def test_sshd_legivel_como_root():
    r = _montar(sshd="uid=0 rc=0\npermitrootlogin prohibit-password\nauthorizedkeysfile .ssh/authorized_keys .ssh/authorized_keys2\nauthorizedkeyscommand none\n")
    assert r.inventario["ssh"]["login_de_root"] == "prohibit-password"
    assert inventario.FONTE_CONFIG_SSHD not in r.inventario["chaves_ssh_fontes_nao_lidas"]


def test_sshd_com_authorized_keys_command_declara_fonte():
    r = _montar(sshd="uid=0 rc=0\npermitrootlogin no\nauthorizedkeyscommand /usr/bin/google_authorized_keys\n")
    assert "AuthorizedKeysCommand" in r.inventario["chaves_ssh_fontes_nao_lidas"]


def test_sshd_ausente_e_falha_nao_privilegio():
    r = _montar(sshd="uid=1001 rc=127\n")
    assert r.evidencia["sshd"].status == FALHA


def test_ntp_pelo_criterio_do_timedated():
    assert _montar(ntp="0 8193\n").inventario["ntp"]["sincronizado"] is True
    assert _montar(ntp="5 8193\n").inventario["ntp"]["sincronizado"] is False  # TIME_ERROR
    assert _montar(ntp="0 65\n").inventario["ntp"]["sincronizado"] is False  # STA_UNSYNC
    assert _montar(ntp="-1 0\n").evidencia["ntp"].status == FALHA


def test_nenhuma_leitura_usa_timedatectl():
    # timedatectl ativa o systemd-timedated no host (medido no laboratório): fere o "só lê".
    assert not any("timedatectl" in c for c in coleta.LEITURAS.values())


def test_saida_irreconhecivel_vira_falha_de_coleta():
    r = _montar(ntp="talvez\n")
    assert r.evidencia["ntp"].status == FALHA
    assert r.evidencia["ntp"].motivo.startswith("falha de coleta")
    assert r.inventario["ntp"]["sincronizado"] is None


def test_leitura_com_limite_excedido():
    r = _montar(portas=ResultadoComando(None, "", "tamanho"))
    assert r.evidencia["portas"].motivo == "falha de coleta: limite excedido (tamanho)"
    assert r.inventario["portas_em_escuta"] is None


def test_chaves_truncadas_sem_marcador_de_fim():
    r = _montar(chaves=linha_de_chaves("coleta", "lida", chave_publica("x@y")) + "\n")
    assert r.evidencia["chaves"].status == FALHA
    assert r.inventario["chaves_ssh"] is None


def test_conta_com_nome_hostil_nao_quebra_o_formato():
    conteudo = chave_publica("a@metacortex-platform") + "\n"
    saida = f"{b64('evil user\n| x |')} authorized_keys lida {b64(conteudo)}\nfim\n"
    r = _montar(chaves=saida)
    assert r.inventario["chaves_ssh"][0]["conta"] == "evil user\n| x |"


# --- linhas de authorized_keys, como o sshd as interpreta (PRD P25) --------------------------


def test_linha_com_opcoes_antes_do_tipo():
    linha = chave_publica("ops@metacortex-platform", opcoes='from="10.0.0.0/8",command="echo a b"')
    assert inventario.interpretar_linha_de_chave(linha) == "ops@metacortex-platform"


def test_comentario_com_espacos_e_inteiro():
    linha = chave_publica("chave do  neo @ laptop")
    assert inventario.interpretar_linha_de_chave(linha) == "chave do  neo @ laptop"


def test_linhas_ignoradas():
    conteudo = "\n".join([
        "",
        "# comentario",
        "ssh-ed25519 nao-e-base64 x@y",
        "lixo qualquer",
        "ssh-rsa " + chave_publica().split()[1] + " tipo@errado",  # blob ed25519 com tipo rsa
        chave_publica(),
    ])
    assert inventario.identificacoes(conteudo) == [None]
