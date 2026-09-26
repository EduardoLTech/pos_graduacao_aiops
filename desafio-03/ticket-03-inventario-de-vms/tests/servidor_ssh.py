"""Servidor SSH em processo (paramiko) para testar a conexão real sem host.

Não substitui a evidência contra VM: não há sshd, systemd nem shell do outro lado. Responde a
cada comando com o que a função `responder(comando)` devolver:
  ("saida", texto, codigo) · ("dorme", segundos) · ("grande", n_bytes) · ("derruba",)
"""

import socket
import threading

import paramiko


class _Interface(paramiko.ServerInterface):
    def __init__(self, autorizada: paramiko.PKey, responder, transporte_ref):
        self.autorizada = autorizada
        self.responder = responder
        self.transporte_ref = transporte_ref

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return "publickey"

    def check_auth_publickey(self, username, key):
        if key.asbytes() == self.autorizada.asbytes():
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_exec_request(self, channel, command):
        # Responder só depois que o paramiko confirmar o exec ao cliente; fechar o canal antes
        # disso faz o cliente ver "Channel closed" no próprio exec_command.
        temporizador = threading.Timer(0.05, self._responder, args=(channel, command.decode()))
        temporizador.daemon = True
        temporizador.start()
        return True

    def _responder(self, canal, comando):
        acao = self.responder(comando)
        try:
            if acao[0] == "saida":
                canal.sendall(acao[1].encode())
                canal.send_exit_status(acao[2])
            elif acao[0] == "dorme":
                threading.Event().wait(acao[1])
                canal.send_exit_status(0)
            elif acao[0] == "grande":
                bloco = b"x" * 65536
                enviado = 0
                while enviado < acao[1] and not canal.closed:
                    canal.sendall(bloco)
                    enviado += len(bloco)
                canal.send_exit_status(0)
            elif acao[0] == "derruba":
                self.transporte_ref[0].close()
                return
            canal.close()
        except Exception:
            pass


class ServidorSSH:
    def __init__(self, autorizada: paramiko.PKey, responder):
        self.chave_de_host = paramiko.RSAKey.generate(2048)
        self.autorizada = autorizada
        self.responder = responder
        self._socket = socket.socket()
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(5)
        self.porta = self._socket.getsockname()[1]
        self._transportes = []
        threading.Thread(target=self._aceitar, daemon=True).start()

    def _aceitar(self):
        while True:
            try:
                conexao, _ = self._socket.accept()
            except OSError:
                return
            ref = [None]
            transporte = paramiko.Transport(conexao)
            ref[0] = transporte
            transporte.add_server_key(self.chave_de_host)
            self._transportes.append(transporte)
            try:
                transporte.start_server(server=_Interface(self.autorizada, self.responder, ref))
            except Exception:
                pass

    def fechar(self):
        self._socket.close()
        for t in self._transportes:
            t.close()
