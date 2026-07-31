# main.py - ORIGINAL RESTAURADO
import threading
import time
import tkinter as tk
from tkinter import messagebox

from config import Config
from database import Database
from firebase_auth import FirebaseAuth
from telegram_manager import TelegramManager
from ssh_manager import SSHManager
from monitor import Monitor
from backup_manager import BackupManager
from email_manager import EmailManager
from tunnel_manager import iniciar_flask, esperar_flask_pronto, iniciar_tunel_com_reconexao, get_url, flask_esta_pronto, parar_tunel
from interface import InterfaceApp


def main():
    print("=" * 60)
    print("INICIANDO My Network - Sistema de Monitoramento")
    print("=" * 60)
    
    print("Inicializando banco de dados...")
    db = Database()
    
    print("Carregando configuracoes...")
    config = Config()
    
    print("Configurando Telegram...")
    telegram_config = config.get_telegram_config()
    telegram_manager = TelegramManager(
        token=telegram_config.get("token", ""),
        chat_id=telegram_config.get("chat_id", "")
    )
    if telegram_manager.esta_configurado():
        print("Telegram configurado!")
    
    print("Configurando Email...")
    email_manager = EmailManager()
    email_config = config.get_email_config()
    if email_config:
        email_manager.configurar(
            provedor=email_config.get("provedor", ""),
            email_envio=email_config.get("email_envio", ""),
            senha=email_config.get("senha", ""),
            email_destino=email_config.get("email_destino", "")
        )
        if email_manager.esta_configurado():
            print("Email configurado!")
    
    print("Configurando SSH...")
    ssh_manager = SSHManager(config)
    # Não inicia aqui - InterfaceApp registra o callback e inicia o SSH Manager
    # (evita que a primeira coleta seja salva antes do callback existir)
    
    print("Configurando Backup...")
    backup_manager = BackupManager(config, ssh_manager, email_manager)
    
    print("Configurando Firebase Auth...")
    firebase_auth = FirebaseAuth()
    credenciais = config.get_firebase_credenciais()
    if credenciais.get("lembrar", False) and credenciais.get("email") and credenciais.get("senha"):
        firebase_auth.configurar(credenciais["email"], credenciais["senha"])
        print("Credenciais carregadas do config.json")
    
    print("Configurando Monitor...")
    monitor = Monitor(telegram_manager=telegram_manager, firebase_manager=None)
    equipamentos = db.listar_equipamentos()
    clientes = db.listar_clientes()
    monitor.atualizar_configuracoes(equipamentos, config.get_configuracoes(), clientes)
    monitor.iniciar()
    print("Monitor iniciado!")
    
    print("Iniciando servidor Flask...")
    porta = config.get_configuracoes().get("porta_flask", 8080)
    print(f"DEBUG: Porta lida do config: {porta}")
    flask_thread = threading.Thread(target=iniciar_flask, args=(db, monitor, firebase_auth, porta), daemon=True)
    flask_thread.start()
    
    if esperar_flask_pronto(max_tentativas=10):
        print("Flask iniciado com sucesso!")
    else:
        resposta = messagebox.askyesno("Flask não iniciou", "O servidor Flask não respondeu após 10 segundos.\n\nDeseja tentar novamente?")
        if resposta:
            if not esperar_flask_pronto(max_tentativas=10):
                print("Flask não respondeu, mas continuando...")
        else:
            print("Continuando sem Flask...")
    
    print("Iniciando Cloudflare Tunnel...")
    tunel_thread = threading.Thread(target=iniciar_tunel_com_reconexao, daemon=True)
    tunel_thread.start()
    
    time.sleep(3)
    url_publica = get_url()
    if url_publica:
        print(f"TUNEL ATIVO: {url_publica}")
    else:
        print("Aguardando tunel... (pode levar alguns segundos)")
    
    backup_config = config.get_backup_config()
    if backup_config.get("agendado", False):
        backup_manager.iniciar_agendamento()
    
    print("Iniciando Interface Grafica...")
    print("=" * 60)
    
    class TunnelWrapper:
        @staticmethod
        def get_url():
            return get_url()
        @staticmethod
        def tunel_ativo():
            return url_publica is not None
    
    # NOTA: InterfaceApp.__init__() registra o callback do SSH Manager
    # e inicia a coleta (se habilitada) ANTES de chamar mainloop().
    # Como mainloop() bloqueia aqui dentro, qualquer código colocado
    # depois desta chamada só executa quando a janela for fechada.
    app = InterfaceApp(
        config=config, db=db, firebase_auth=firebase_auth,
        telegram_manager=telegram_manager, ssh_manager=ssh_manager,
        monitor=monitor, backup_manager=backup_manager,
        email_manager=email_manager, tunnel_manager=TunnelWrapper()
    )

    print("Encerrando...")
    parar_tunel()


if __name__ == "__main__":
    main()