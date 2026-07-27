# interface.py - COMPLETO E CORRIGIDO
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os

from aba_equipamentos import AbaEquipamentos
from aba_localidades import AbaLocalidades
from aba_configuracoes import AbaConfiguracoes
from aba_clientes import AbaClientes
from aba_backup import AbaBackup
from aba_telegram import AbaTelegram
from aba_conta import AbaConta
from aba_servidores import AbaServidores
from aba_energias import AbaEnergias
from aba_servicos import AbaServicos


class InterfaceApp:
    def __init__(self, config, db, firebase_auth, telegram_manager, ssh_manager, monitor, backup_manager=None, email_manager=None, tunnel_manager=None):
        self.config = config
        self.db = db
        self.firebase_auth = firebase_auth
        self.telegram_manager = telegram_manager
        self.ssh_manager = ssh_manager
        self.monitor = monitor
        self.backup_manager = backup_manager
        self.email_manager = email_manager
        self.tunnel_manager = tunnel_manager
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        self.janela = ctk.CTk()
        self.janela.title("My Network - Sistema de Monitoramento")
        self.janela.geometry("1400x800")
        self.janela.minsize(1200, 700)

        self.janela.update_idletasks()
        x = (self.janela.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.janela.winfo_screenheight() // 2) - (800 // 2)
        self.janela.geometry(f"1400x800+{x}+{y}")
        
        self.equipamentos = db.listar_por_tipo('equipamento')
        self.localidades = db.listar_localidades()
        self.clientes = db.listar_clientes()
        self.servidores = db.listar_por_tipo('servidor')
        self.energias = db.listar_por_tipo('energia')
        self.servicos = db.listar_por_tipo('servico')
        
        self.monitor.atualizar_configuracoes(self._todos_equipamentos(), config.get_configuracoes(), self.clientes)
        
        if not hasattr(monitor, 'thread') or not monitor.thread or not monitor.thread.is_alive():
            self.monitor.iniciar()
        
        ssh_config = config.get_snmp_config()
        if ssh_config.get("enabled", False):
            self.ssh_manager.iniciar()
        
        if self.backup_manager:
            backup_config = config.get_backup_config()
            if backup_config.get("agendado", False):
                self.backup_manager.iniciar_agendamento()
        
        self.criar_interface()
        
        credenciais = config.get_firebase_credenciais()
        reconexao = config.get_reconexao()
        if credenciais.get("lembrar", False) and reconexao.get("ativa", False):
            self.iniciar_autenticacao_automatica()
        
        self.atualizar_interface()
        self.janela.mainloop()
    
    def _todos_equipamentos(self):
        return self.equipamentos + self.servidores + self.energias + self.servicos
    
    def _atualizar_item_lista(self, lista, item_atualizado):
        for i, item in enumerate(lista):
            if item.get('id') == item_atualizado.get('id'):
                lista[i] = item_atualizado
                return
        lista.append(item_atualizado)
    
    def _remover_item_das_listas(self, id_removido):
        """Remove um item de todas as listas locais (quando excluído)"""
        self.equipamentos = [e for e in self.equipamentos if e.get('id') != id_removido]
        self.servidores = [s for s in self.servidores if s.get('id') != id_removido]
        self.energias = [e for e in self.energias if e.get('id') != id_removido]
        self.servicos = [s for s in self.servicos if s.get('id') != id_removido]
    
    def iniciar_autenticacao_automatica(self):
        credenciais = self.config.get_firebase_credenciais()
        email = credenciais.get("email", "")
        senha = credenciais.get("senha", "")
        if email and senha:
            self.firebase_auth.configurar(email, senha)
            def autenticar():
                if self.firebase_auth.autenticar():
                    url = self.tunnel_manager.get_url() if self.tunnel_manager else None
                    if url: self.firebase_auth.salvar_url(url)
            threading.Thread(target=autenticar, daemon=True).start()
    
    def _reiniciar_sistemas(self):
        self.equipamentos = self.db.listar_por_tipo('equipamento')
        self.localidades = self.db.listar_localidades()
        self.clientes = self.db.listar_clientes()
        self.servidores = self.db.listar_por_tipo('servidor')
        self.energias = self.db.listar_por_tipo('energia')
        self.servicos = self.db.listar_por_tipo('servico')
        self.monitor.atualizar_configuracoes(self._todos_equipamentos(), self.config.get_configuracoes(), self.clientes)
        ssh_config = self.config.get_snmp_config()
        self.ssh_manager.parar()
        if ssh_config.get("enabled", False): self.ssh_manager.iniciar()
        if self.tunnel_manager:
            from tunnel_manager import reiniciar_tunel
            threading.Thread(target=reiniciar_tunel, daemon=True).start()
        self.atualizar_dados()
    
    def criar_interface(self):
        self.main_frame = ctk.CTkFrame(self.janela)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.criar_barra_titulo()
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_equipamentos = self.tabview.add("Equipamentos")
        self.tab_servidores = self.tabview.add("Servidores")
        self.tab_energias = self.tabview.add("Energias")
        self.tab_servicos = self.tabview.add("Servicos")
        self.tab_clientes = self.tabview.add("Clientes")
        self.tab_localidades = self.tabview.add("Localidades")
        self.tab_backup = self.tabview.add("Backup/Email")
        self.tab_ssh = self.tabview.add("SSH")
        self.tab_configuracoes = self.tabview.add("Configuracoes")
        self.tab_telegram = self.tabview.add("Telegram")
        self.tab_conta = self.tabview.add("Conta")
        
        self.aba_equipamentos = AbaEquipamentos(self.tab_equipamentos, self.config, self.db, self.monitor, self.ssh_manager, self.atualizar_dados)
        self.aba_equipamentos.equipamentos = self.equipamentos
        self.aba_equipamentos.localidades = self.localidades
        
        self.aba_servidores = AbaServidores(self.tab_servidores, self.config, self.db, self.monitor, self.atualizar_dados)
        self.aba_servidores.servidores = self.servidores
        
        self.aba_energias = AbaEnergias(self.tab_energias, self.config, self.db, self.monitor, self.atualizar_dados)
        self.aba_energias.energias = self.energias
        
        self.aba_servicos = AbaServicos(self.tab_servicos, self.config, self.db, self.monitor, self.atualizar_dados)
        self.aba_servicos.servicos = self.servicos
        
        self.aba_localidades = AbaLocalidades(self.tab_localidades, self.config, self.db, self.atualizar_dados)
        self.aba_localidades.localidades = self.localidades
        
        self.aba_clientes = AbaClientes(self.tab_clientes, self.config, self.db, self.monitor, self.atualizar_dados)
        self.aba_clientes.clientes = self.clientes
        self.aba_clientes.equipamentos = self.equipamentos
        self.aba_clientes.localidades = self.localidades
        
        if self.backup_manager and self.email_manager:
            self.aba_backup = AbaBackup(self.tab_backup, self.config, None, self.backup_manager, self.email_manager)
            self.adicionar_botoes_importacao()
        
        self.aba_telegram = AbaTelegram(self.tab_telegram, self.config, self.telegram_manager, None)
        self.aba_conta = AbaConta(self.tab_conta, self.config, self.firebase_auth, self.tunnel_manager)
        self.aba_configuracoes = AbaConfiguracoes(self.tab_configuracoes, self.config, self.monitor, self.atualizar_dados, None)
        
        self.configurar_aba_ssh()
        self.criar_barra_status()
    
    def adicionar_botoes_importacao(self):
        container = self.aba_backup.container
        ctk.CTkFrame(container, height=2, fg_color="gray").pack(fill="x", pady=15)
        frame_import = ctk.CTkFrame(container)
        frame_import.pack(fill="x", pady=10)
        ctk.CTkLabel(frame_import, text="Importar / Restaurar", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        btn_frame = ctk.CTkFrame(frame_import)
        btn_frame.pack(anchor="w", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Importar Banco de Dados (DB)", command=lambda: self.importar_arquivo("db"), width=220).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Importar Configuracao (JSON)", command=lambda: self.importar_arquivo("json"), width=220).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Restaurar Backup (ZIP)", command=self.restaurar_backup_zip, width=220, fg_color="#00aa55").pack(side="left", padx=5)
        self.lbl_import_status = ctk.CTkLabel(frame_import, text="", font=("Arial", 11))
        self.lbl_import_status.pack(anchor="w", padx=10, pady=10)
    
    def importar_arquivo(self, tipo):
        extensoes = [("Banco SQLite", "*.db")] if tipo == "db" else [("Arquivo JSON", "*.json")]
        arquivo = filedialog.askopenfilename(title="Selecionar arquivo", filetypes=extensoes)
        if not arquivo: return
        if not messagebox.askyesno("Confirmar", f"Importar {os.path.basename(arquivo)}?"): return
        self.lbl_import_status.configure(text="Importando...", text_color="orange")
        def importar():
            sucesso, mensagem = self.backup_manager.importar_arquivo(arquivo, tipo, self._reiniciar_sistemas)
            self.lbl_import_status.after(0, lambda s=sucesso, m=mensagem: self.lbl_import_status.configure(text=m, text_color="green" if s else "red"))
        threading.Thread(target=importar, daemon=True).start()
    
    def restaurar_backup_zip(self):
        arquivo = filedialog.askopenfilename(title="Selecionar backup", filetypes=[("Arquivo ZIP", "*.zip")])
        if not arquivo: return
        if not messagebox.askyesno("Confirmar", f"Restaurar {os.path.basename(arquivo)}?"): return
        self.lbl_import_status.configure(text="Restaurando...", text_color="orange")
        def restaurar():
            sucesso, mensagem = self.backup_manager.restaurar_backup(arquivo, self._reiniciar_sistemas)
            self.lbl_import_status.after(0, lambda s=sucesso, m=mensagem: self.lbl_import_status.configure(text=m, text_color="green" if s else "red"))
        threading.Thread(target=restaurar, daemon=True).start()
    
    def criar_barra_titulo(self):
        titulo_frame = ctk.CTkFrame(self.main_frame, height=50)
        titulo_frame.pack(fill="x", padx=10, pady=(5, 10))
        titulo_frame.pack_propagate(False)
        ctk.CTkLabel(titulo_frame, text="My Network", font=("Arial", 24, "bold")).pack(side="left", padx=10)
        self.lbl_status = ctk.CTkLabel(titulo_frame, text="ONLINE", font=("Arial", 14, "bold"), text_color="green")
        self.lbl_status.pack(side="right", padx=10)
    
    def criar_barra_status(self):
        self.status_frame = ctk.CTkFrame(self.main_frame, height=35)
        self.status_frame.pack(fill="x", padx=10, pady=(5, 5))
        self.status_frame.pack_propagate(False)
        self.lbl_resumo = ctk.CTkLabel(self.status_frame, text="Resumo: 0 equipamentos | 0 online | 0 offline", font=("Arial", 11))
        self.lbl_resumo.pack(side="left", padx=10)
        self.lbl_ultima = ctk.CTkLabel(self.status_frame, text="Ultima verificacao: --:--:--", font=("Arial", 11))
        self.lbl_ultima.pack(side="right", padx=10)
    
    def configurar_aba_ssh(self):
        scroll_frame = ctk.CTkScrollableFrame(self.tab_ssh)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame = ctk.CTkFrame(scroll_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text="Teste de Conexao SSH", font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 15))
        ctk.CTkLabel(frame, text="IP:").pack(anchor="w", pady=(10, 0))
        self.entry_ssh_ip = ctk.CTkEntry(frame, width=350)
        self.entry_ssh_ip.pack(anchor="w", pady=5)
        ctk.CTkLabel(frame, text="Usuario:").pack(anchor="w", pady=(10, 0))
        self.entry_ssh_usuario = ctk.CTkEntry(frame, width=350)
        self.entry_ssh_usuario.insert(0, "ubnt")
        self.entry_ssh_usuario.pack(anchor="w", pady=5)
        ctk.CTkLabel(frame, text="Senha:").pack(anchor="w", pady=(10, 0))
        self.entry_ssh_senha = ctk.CTkEntry(frame, width=350, show="*")
        self.entry_ssh_senha.pack(anchor="w", pady=5)
        ctk.CTkButton(frame, text="TESTAR SSH", command=self.testar_ssh_simples, width=150).pack(anchor="w", pady=20)
        self.ssh_resultado_texto = ctk.CTkTextbox(frame, height=250, width=600)
        self.ssh_resultado_texto.pack(fill="both", expand=True, pady=5)
    
    def testar_ssh_simples(self):
        ip = self.entry_ssh_ip.get().strip()
        usuario = self.entry_ssh_usuario.get().strip() or "ubnt"
        senha = self.entry_ssh_senha.get().strip()
        if not ip or not senha: return
        self.ssh_resultado_texto.delete("1.0", "end")
        self.ssh_resultado_texto.insert("1.0", f"Testando SSH em {ip}:22...\n\n")
        def executar_teste():
            resultados = self.ssh_manager.testar(ip, usuario, senha, 22)
            for r in resultados: self.ssh_resultado_texto.after(0, lambda r=r: self.ssh_resultado_texto.insert("end", r + "\n"))
        threading.Thread(target=executar_teste, daemon=True).start()
    
    def atualizar_dados(self):
        estado = self.monitor.estado_dispositivos
        
        for eq in self.equipamentos:
            ip = eq.get("ip", "")
            if ip in estado:
                eq["status"] = "ONLINE" if estado[ip].get("online") else "OFFLINE"
                eq["latencia"] = estado[ip].get("latencia", 0)
        
        for cli in self.clientes:
            ip = cli.get("ip", "")
            if ip in estado:
                cli["status"] = "ONLINE" if estado[ip].get("online") else "OFFLINE"
                cli["latencia"] = estado[ip].get("latencia", 0)
        
        for srv in self.servidores:
            ip = srv.get("ip", "")
            if ip in estado:
                srv["status"] = "ONLINE" if estado[ip].get("online") else "OFFLINE"
                srv["latencia"] = estado[ip].get("latencia", 0)
        
        for en in self.energias:
            ip = en.get("ip", "")
            if ip in estado:
                en["status"] = "ONLINE" if estado[ip].get("online") else "OFFLINE"
                en["latencia"] = estado[ip].get("latencia", 0)
        
        for svc in self.servicos:
            ip = svc.get("ip", "")
            if ip in estado:
                svc["status"] = "ONLINE" if estado[ip].get("online") else "OFFLINE"
                svc["latencia"] = estado[ip].get("latencia", 0)
        
        if hasattr(self, 'aba_equipamentos'):
            self.aba_equipamentos.equipamentos = self.equipamentos
            self.aba_equipamentos.localidades = self.localidades
            self.aba_equipamentos.atualizar_lista()
        
        if hasattr(self, 'aba_servidores'):
            self.aba_servidores.servidores = self.servidores
            self.aba_servidores.atualizar_lista()
        
        if hasattr(self, 'aba_energias'):
            self.aba_energias.energias = self.energias
            self.aba_energias.atualizar_lista()
        
        if hasattr(self, 'aba_servicos'):
            self.aba_servicos.servicos = self.servicos
            self.aba_servicos.atualizar_lista()
        
        if hasattr(self, 'aba_localidades'):
            self.aba_localidades.localidades = self.localidades
            self.aba_localidades.atualizar_lista()
        
        if hasattr(self, 'aba_clientes'):
            self.aba_clientes.clientes = self.clientes
            self.aba_clientes.equipamentos = self.equipamentos
            self.aba_clientes.localidades = self.localidades
            self.aba_clientes.atualizar_lista()
    
    def atualizar_interface(self):
        import tunnel_manager
        if tunnel_manager.ultima_alteracao is not None:
            id_alterado = tunnel_manager.ultima_alteracao
            
            if id_alterado == -1:
                # Localidades
                self.localidades = self.db.listar_localidades()
            elif id_alterado:
                todos = self.db.listar_equipamentos()
                item_atualizado = None
                for novo in todos:
                    if novo.get('id') == id_alterado:
                        item_atualizado = novo
                        break
                
                if item_atualizado:
                    tipo = item_atualizado.get('tipo', 'equipamento')
                    if tipo == 'equipamento':
                        self._atualizar_item_lista(self.equipamentos, item_atualizado)
                    elif tipo == 'servidor':
                        self._atualizar_item_lista(self.servidores, item_atualizado)
                    elif tipo == 'energia':
                        self._atualizar_item_lista(self.energias, item_atualizado)
                    elif tipo == 'servico':
                        self._atualizar_item_lista(self.servicos, item_atualizado)
                else:
                    # ✅ FOI EXCLUÍDO - Remove das listas locais (sem consultar banco)
                    self._remover_item_das_listas(id_alterado)
            
            # ✅ RECARREGA CLIENTES DO BANCO SEMPRE!
            self.clientes = self.db.listar_clientes()
            self.monitor.atualizar_configuracoes(self._todos_equipamentos(), self.config.get_configuracoes(), self.clientes)
            tunnel_manager.ultima_alteracao = None
        
        estado = self.monitor.estado_dispositivos
        online = sum(1 for e in estado.values() if e.get("online"))
        offline = len(estado) - online
        total = len(self._todos_equipamentos()) + len(self.clientes)
        self.lbl_resumo.configure(text=f"Resumo: {total} dispositivos | {online} online | {offline} offline")
        
        if self.monitor.get_ultima_verificacao():
            self.lbl_ultima.configure(text=f"Ultima verificacao: {self.monitor.get_ultima_verificacao().strftime('%H:%M:%S')}")
        
        self.atualizar_dados()
        self.janela.after(2000, self.atualizar_interface)