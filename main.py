# main.py - ATUALIZADO (porta via parâmetro)
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
    
    # ========== 1. INICIAR BANCO DE DADOS ==========
    print("Inicializando banco de dados...")
    db = Database()
    
    # ========== 2. CARREGAR CONFIGURAÇÕES ==========
    print("Carregando configuracoes...")
    config = Config()
    
    # ========== 3. INICIAR TELEGRAM ==========
    print("Configurando Telegram...")
    telegram_config = config.get_telegram_config()
    telegram_manager = TelegramManager(
        token=telegram_config.get("token", ""),
        chat_id=telegram_config.get("chat_id", "")
    )
    if telegram_manager.esta_configurado():
        print("Telegram configurado!")
    
    # ========== 4. INICIAR EMAIL ==========
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
    
    # ========== 5. INICIAR SSH ==========
    print("Configurando SSH...")
    ssh_manager = SSHManager(config)
    ssh_manager.iniciar()
    
    # ========== 6. INICIAR BACKUP ==========
    print("Configurando Backup...")
    backup_manager = BackupManager(config, ssh_manager, email_manager)
    
    # ========== 7. INICIAR FIREBASE AUTH ==========
    print("Configurando Firebase Auth...")
    firebase_auth = FirebaseAuth()
    
    credenciais = config.get_firebase_credenciais()
    if credenciais.get("lembrar", False) and credenciais.get("email") and credenciais.get("senha"):
        firebase_auth.configurar(credenciais["email"], credenciais["senha"])
        print("Credenciais carregadas do config.json")
    
    # ========== 8. INICIAR MONITOR ==========
    print("Configurando Monitor...")
    monitor = Monitor(
        telegram_manager=telegram_manager,
        firebase_manager=None
    )
    
    equipamentos = db.listar_equipamentos()
    clientes = db.listar_clientes()
    
    monitor.atualizar_configuracoes(
        equipamentos,
        config.get_configuracoes(),
        clientes
    )
    
    monitor.iniciar()
    print("Monitor iniciado!")
    
    # ========== 9. INICIAR FLASK (COM MONITOR + FIREBASE + PORTA) ==========
    print("Iniciando servidor Flask...")
    
    # ✅ Lê a porta do config e passa pro Flask
    porta = config.get_configuracoes().get("porta_flask", 8080)
    print(f"DEBUG: Porta lida do config: {porta}")
    flask_thread = threading.Thread(target=iniciar_flask, args=(db, monitor, firebase_auth, porta), daemon=True)
    flask_thread.start()
    
    if esperar_flask_pronto(max_tentativas=10):
        print("Flask iniciado com sucesso!")
    else:
        resposta = messagebox.askyesno(
            "Flask não iniciou",
            "O servidor Flask não respondeu após 10 segundos.\n\n"
            "Deseja tentar novamente?"
        )
        if resposta:
            if not esperar_flask_pronto(max_tentativas=10):
                print("Flask não respondeu, mas continuando...")
        else:
            print("Continuando sem Flask...")
    
    # ========== 10. INICIAR TÚNEL COM RECONEXÃO ==========
    print("Iniciando Cloudflare Tunnel...")
    tunel_thread = threading.Thread(target=iniciar_tunel_com_reconexao, daemon=True)
    tunel_thread.start()
    
    time.sleep(3)
    url_publica = get_url()
    if url_publica:
        print(f"TUNEL ATIVO: {url_publica}")
    else:
        print("Aguardando tunel... (pode levar alguns segundos)")
    
    # ========== 11. INICIAR BACKUP AGENDADO ==========
    backup_config = config.get_backup_config()
    if backup_config.get("agendado", False):
        backup_manager.iniciar_agendamento()
    
    # ========== 12. INICIAR INTERFACE ==========
    print("Iniciando Interface Grafica...")
    print("=" * 60)
    
    class TunnelWrapper:
        @staticmethod
        def get_url():
            return get_url()
        
        @staticmethod
        def tunel_ativo():
            return url_publica is not None
    
    app = InterfaceApp(
        config=config,
        db=db,
        firebase_auth=firebase_auth,
        telegram_manager=telegram_manager,
        ssh_manager=ssh_manager,
        monitor=monitor,
        backup_manager=backup_manager,
        email_manager=email_manager,
        tunnel_manager=TunnelWrapper()
    )
    
    print("Encerrando...")
    parar_tunel()


if __name__ == "__main__":
    main()