import customtkinter as ctk
from tkinter import messagebox, ttk
import threading
from datetime import datetime

class AbaBackup:
    def __init__(self, parent, config, firebase_manager, backup_manager, email_manager):
        self.parent = parent
        self.config = config
        self.firebase_manager = firebase_manager
        self.backup_manager = backup_manager
        self.email_manager = email_manager
        
        self.criar_aba()
        self.carregar_configuracoes()
        self.atualizar_historico()
    
    def criar_aba(self):
        self.container = ctk.CTkScrollableFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        lbl_titulo = ctk.CTkLabel(self.container, text="💾 Backup e Email", font=("Arial", 18, "bold"))
        lbl_titulo.pack(anchor="w", pady=(0, 15))
        
        # ========== SEÇÃO DE EMAIL ==========
        frame_email = ctk.CTkFrame(self.container)
        frame_email.pack(fill="x", pady=10)
        
        lbl_email = ctk.CTkLabel(frame_email, text="📧 Configuração de Email", font=("Arial", 14, "bold"))
        lbl_email.pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(frame_email, text="Provedor:").pack(anchor="w", padx=10, pady=(5, 0))
        self.combo_provedor = ctk.CTkComboBox(frame_email, values=self.email_manager.get_provedores(), width=300)
        self.combo_provedor.pack(anchor="w", padx=10, pady=5)
        self.combo_provedor.set("gmail")
        
        ctk.CTkLabel(frame_email, text="Email de envio:").pack(anchor="w", padx=10, pady=(5, 0))
        self.entry_email_envio = ctk.CTkEntry(frame_email, width=350, placeholder_text="seuemail@gmail.com")
        self.entry_email_envio.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_email, text="Senha do app:").pack(anchor="w", padx=10, pady=(5, 0))
        self.entry_senha = ctk.CTkEntry(frame_email, width=350, placeholder_text="senha do app", show="*")
        self.entry_senha.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_email, text="Email de destino:").pack(anchor="w", padx=10, pady=(5, 0))
        self.entry_email_destino = ctk.CTkEntry(frame_email, width=350, placeholder_text="destino@gmail.com")
        self.entry_email_destino.pack(anchor="w", padx=10, pady=5)
        
        # Informação sobre senha de app
        lbl_info_senha = ctk.CTkLabel(frame_email, 
            text="📌 Use uma 'Senha de App' do Gmail (não a senha da conta).\n"
                 "   Gmail: Conta > Segurança > Verificação em duas etapas > Senhas de app",
            font=("Arial", 10), text_color="gray", justify="left")
        lbl_info_senha.pack(anchor="w", padx=10, pady=(0, 5))
        
        btn_frame_email = ctk.CTkFrame(frame_email)
        btn_frame_email.pack(anchor="w", padx=10, pady=10)
        
        btn_testar_email = ctk.CTkButton(btn_frame_email, text="🔗 Testar Email", command=self.testar_email, width=150)
        btn_testar_email.pack(side="left", padx=5)
        
        btn_salvar_email = ctk.CTkButton(btn_frame_email, text="💾 Salvar Email", command=self.salvar_email, width=150)
        btn_salvar_email.pack(side="left", padx=5)
        
        self.lbl_email_status = ctk.CTkLabel(frame_email, text="", font=("Arial", 11))
        self.lbl_email_status.pack(anchor="w", padx=10, pady=5)
        
        # Separador
        separator = ctk.CTkFrame(self.container, height=2, fg_color="gray")
        separator.pack(fill="x", pady=10)
        
        # ========== SEÇÃO DE BACKUP ==========
        frame_backup = ctk.CTkFrame(self.container)
        frame_backup.pack(fill="x", pady=10)
        
        lbl_backup = ctk.CTkLabel(frame_backup, text="💾 Configuração de Backup", font=("Arial", 14, "bold"))
        lbl_backup.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Frame para botões de ação
        btn_frame_backup = ctk.CTkFrame(frame_backup)
        btn_frame_backup.pack(anchor="w", padx=10, pady=10)
        
        btn_backup_agora = ctk.CTkButton(btn_frame_backup, text="📁 FAZER BACKUP AGORA", command=self.fazer_backup, width=200, height=40, font=("Arial", 13, "bold"), fg_color="green")
        btn_backup_agora.pack(side="left", padx=5)
        
        btn_backup_sem_email = ctk.CTkButton(btn_frame_backup, text="📁 Backup (sem email)", command=lambda: self.fazer_backup(enviar_email=False), width=180, height=40, font=("Arial", 13))
        btn_backup_sem_email.pack(side="left", padx=5)
        
        # Configurações de agendamento
        lbl_agendamento = ctk.CTkLabel(frame_backup, text="⏰ Agendamento", font=("Arial", 13, "bold"))
        lbl_agendamento.pack(anchor="w", padx=10, pady=(15, 5))
        
        self.auto_backup_var = ctk.BooleanVar(value=False)
        chk_auto = ctk.CTkCheckBox(frame_backup, text="Ativar backup automático", variable=self.auto_backup_var, font=("Arial", 13), command=self.on_toggle_agendamento)
        chk_auto.pack(anchor="w", padx=10, pady=5)
        
        frame_intervalo = ctk.CTkFrame(frame_backup)
        frame_intervalo.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_intervalo, text="Intervalo:").pack(side="left", padx=(0, 10))
        self.combo_intervalo = ctk.CTkComboBox(frame_intervalo, values=["1h", "5h", "8h", "12h", "24h", "diario", "semanal", "mensal"], width=120)
        self.combo_intervalo.pack(side="left", padx=5)
        self.combo_intervalo.set("24h")
        
        ctk.CTkLabel(frame_intervalo, text="Hora (HH:MM):").pack(side="left", padx=(20, 10))
        self.entry_hora = ctk.CTkEntry(frame_intervalo, width=70, placeholder_text="00:00")
        self.entry_hora.pack(side="left", padx=5)
        self.entry_hora.insert(0, "00:00")
        
        # Informação sobre agendamento
        lbl_info_agendamento = ctk.CTkLabel(frame_backup, 
            text="📌 Intervalos fixos (1h, 5h, etc) executam a cada X horas a partir do horário configurado.\n"
                 "   Diário: uma vez por dia no horário. Semanal: uma vez por semana. Mensal: uma vez por mês.",
            font=("Arial", 10), text_color="gray", justify="left")
        lbl_info_agendamento.pack(anchor="w", padx=10, pady=(5, 5))
        
        btn_salvar_backup = ctk.CTkButton(frame_backup, text="💾 Salvar Configurações de Backup", command=self.salvar_backup, width=250)
        btn_salvar_backup.pack(anchor="w", padx=10, pady=10)
        
        self.lbl_backup_status = ctk.CTkLabel(frame_backup, text="", font=("Arial", 11))
        self.lbl_backup_status.pack(anchor="w", padx=10, pady=5)
        
        # Status do agendamento
        self.lbl_agendamento_status = ctk.CTkLabel(frame_backup, text="", font=("Arial", 11))
        self.lbl_agendamento_status.pack(anchor="w", padx=10, pady=5)
        
        # Separador
        separator2 = ctk.CTkFrame(self.container, height=2, fg_color="gray")
        separator2.pack(fill="x", pady=10)
        
        # ========== HISTÓRICO ==========
        frame_historico = ctk.CTkFrame(self.container)
        frame_historico.pack(fill="both", expand=True, pady=10)
        
        lbl_historico = ctk.CTkLabel(frame_historico, text="📋 Histórico de Backups", font=("Arial", 14, "bold"))
        lbl_historico.pack(anchor="w", padx=10, pady=(10, 5))
        
        tree_frame = ctk.CTkFrame(frame_historico)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Adicionar scrollbar
        tree_scroll = ctk.CTkScrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")
        
        self.tree_historico = ttk.Treeview(tree_frame, columns=("data", "arquivo", "equipamentos", "falhas", "status"), show="headings", height=8)
        self.tree_historico.heading("data", text="Data/Hora")
        self.tree_historico.heading("arquivo", text="Arquivo")
        self.tree_historico.heading("equipamentos", text="Sucessos")
        self.tree_historico.heading("falhas", text="Falhas")
        self.tree_historico.heading("status", text="Email")
        
        self.tree_historico.column("data", width=150)
        self.tree_historico.column("arquivo", width=200)
        self.tree_historico.column("equipamentos", width=80)
        self.tree_historico.column("falhas", width=60)
        self.tree_historico.column("status", width=100)
        
        self.tree_historico.pack(side="left", fill="both", expand=True)
        
        # Configurar scrollbar
        tree_scroll.configure(command=self.tree_historico.yview)
        self.tree_historico.configure(yscrollcommand=tree_scroll.set)
        
        btn_frame_hist = ctk.CTkFrame(frame_historico)
        btn_frame_hist.pack(anchor="w", padx=10, pady=10)
        
        btn_atualizar = ctk.CTkButton(btn_frame_hist, text="🔄 Atualizar Histórico", command=self.atualizar_historico, width=180)
        btn_atualizar.pack(side="left", padx=5)
        
        btn_limpar = ctk.CTkButton(btn_frame_hist, text="🗑️ Limpar Histórico", command=self.limpar_historico, width=150, fg_color="orange")
        btn_limpar.pack(side="left", padx=5)
    
    def carregar_configuracoes(self):
        """Carrega as configurações salvas"""
        email_config = self.config.get_email_config()
        if email_config:
            self.combo_provedor.set(email_config.get("provedor", "gmail"))
            
            self.entry_email_envio.delete(0, "end")
            self.entry_email_envio.insert(0, email_config.get("email_envio", ""))
            
            self.entry_senha.delete(0, "end")
            self.entry_senha.insert(0, email_config.get("senha", ""))
            
            self.entry_email_destino.delete(0, "end")
            self.entry_email_destino.insert(0, email_config.get("email_destino", ""))
            
            self.email_manager.configurar(**email_config)
        
        backup_config = self.config.get_backup_config()
        if backup_config:
            self.auto_backup_var.set(backup_config.get("agendado", False))
            self.combo_intervalo.set(backup_config.get("intervalo", "24h"))
            self.entry_hora.delete(0, "end")
            self.entry_hora.insert(0, backup_config.get("hora", "00:00"))
            self.backup_manager.backup_config = backup_config.copy()
            self.backup_manager.carregar_historico()
            
        self.atualizar_status_agendamento()
    
    def on_toggle_agendamento(self):
        """Callback quando o checkbox de agendamento é alterado"""
        self.atualizar_status_agendamento()
    
    def atualizar_status_agendamento(self):
        """Atualiza o label de status do agendamento"""
        if self.auto_backup_var.get():
            intervalo = self.combo_intervalo.get()
            hora = self.entry_hora.get()
            self.lbl_agendamento_status.configure(
                text=f"⏰ Agendamento ativo: {intervalo} às {hora}", 
                text_color="green"
            )
        else:
            self.lbl_agendamento_status.configure(
                text="⏰ Agendamento desativado", 
                text_color="gray"
            )
    
    def salvar_email(self):
        """Salva as configurações de email"""
        email_config = {
            "provedor": self.combo_provedor.get(),
            "email_envio": self.entry_email_envio.get().strip(),
            "email_destino": self.entry_email_destino.get().strip(),
            "senha": self.entry_senha.get()
        }
        
        if not email_config["email_envio"] or not email_config["senha"] or not email_config["email_destino"]:
            messagebox.showwarning("Aviso", "Preencha todos os campos de email!")
            return
        
        self.config.set_email_config(email_config)
        self.email_manager.configurar(**email_config)
        
        self.lbl_email_status.configure(text="💾 Salvando...", text_color="orange")
        
        def salvar_firebase():
            try:
                if self.firebase_manager and self.firebase_manager.esta_configurado():
                    self.firebase_manager.salvar_email_config(email_config)
                self.lbl_email_status.after(0, lambda: self.lbl_email_status.configure(text="✅ Email salvo com sucesso!", text_color="green"))
                self.lbl_email_status.after(3000, lambda: self.lbl_email_status.configure(text=""))
            except Exception as e:
                self.lbl_email_status.after(0, lambda: self.lbl_email_status.configure(text=f"❌ Erro ao salvar: {e}", text_color="red"))
        
        threading.Thread(target=salvar_firebase, daemon=True).start()
        messagebox.showinfo("Sucesso", "Configurações de email salvas!")
    
    def testar_email(self):
        """Testa o envio de email"""
        # Primeiro salva as configurações
        self.salvar_email()
        
        if not self.email_manager.esta_configurado():
            messagebox.showwarning("Aviso", "Configure o email primeiro!")
            return
        
        self.lbl_email_status.configure(text="📧 Enviando email de teste...", text_color="orange")
        
        def testar():
            sucesso, mensagem = self.email_manager.testar()
            if sucesso:
                self.lbl_email_status.after(0, lambda: self.lbl_email_status.configure(text="✅ Email de teste enviado!", text_color="green"))
                self.lbl_email_status.after(5000, lambda: self.lbl_email_status.configure(text=""))
                messagebox.showinfo("Sucesso", f"✅ Email de teste enviado para {self.email_manager.config['email_destino']}!")
            else:
                self.lbl_email_status.after(0, lambda: self.lbl_email_status.configure(text=f"❌ {mensagem}", text_color="red"))
                messagebox.showerror("Erro", f"❌ Falha ao enviar email:\n{mensagem}")
        
        threading.Thread(target=testar, daemon=True).start()
    
    def salvar_backup(self):
        """Salva as configurações de backup"""
        hora = self.entry_hora.get().strip()
        
        # Validar formato da hora
        import re
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', hora):
            messagebox.showwarning("Aviso", "Formato de hora inválido! Use HH:MM (ex: 14:30)")
            return
        
        backup_config = {
            "agendado": self.auto_backup_var.get(),
            "intervalo": self.combo_intervalo.get(),
            "hora": hora
        }
        
        self.config.set_backup_config(backup_config)
        self.backup_manager.backup_config = backup_config.copy()
        self.backup_manager.salvar_config()
        
        # Parar agendamento atual e reiniciar se necessário
        self.backup_manager.parar_agendamento()
        if backup_config["agendado"]:
            self.backup_manager.iniciar_agendamento()
        
        self.lbl_backup_status.configure(text="💾 Salvando...", text_color="orange")
        self.atualizar_status_agendamento()
        
        def salvar_firebase():
            try:
                if self.firebase_manager and self.firebase_manager.esta_configurado():
                    self.firebase_manager.salvar_backup_config(backup_config)
                self.lbl_backup_status.after(0, lambda: self.lbl_backup_status.configure(text="✅ Configurações salvas!", text_color="green"))
                self.lbl_backup_status.after(3000, lambda: self.lbl_backup_status.configure(text=""))
            except Exception as e:
                self.lbl_backup_status.after(0, lambda: self.lbl_backup_status.configure(text=f"❌ Erro: {e}", text_color="red"))
        
        threading.Thread(target=salvar_firebase, daemon=True).start()
        messagebox.showinfo("Sucesso", "Configurações de backup salvas!\nO agendamento foi atualizado.")
    
    def fazer_backup(self, enviar_email=True):
        """Executa o backup agora"""
        self.lbl_backup_status.configure(text="📁 Iniciando backup...", text_color="orange")
        
        def executar_backup():
            try:
                sucesso, mensagem, caminho = self.backup_manager.fazer_backup_agora(enviar_email=enviar_email)
                if sucesso:
                    self.lbl_backup_status.after(0, lambda: self.lbl_backup_status.configure(text=f"✅ {mensagem}", text_color="green"))
                    self.lbl_backup_status.after(5000, lambda: self.lbl_backup_status.configure(text=""))
                    self.atualizar_historico()
                    messagebox.showinfo("Sucesso", mensagem)
                else:
                    self.lbl_backup_status.after(0, lambda: self.lbl_backup_status.configure(text=f"❌ {mensagem}", text_color="red"))
                    messagebox.showerror("Erro", mensagem)
            except Exception as e:
                self.lbl_backup_status.after(0, lambda: self.lbl_backup_status.configure(text=f"❌ Erro: {e}", text_color="red"))
                messagebox.showerror("Erro", f"Erro ao fazer backup:\n{e}")
        
        threading.Thread(target=executar_backup, daemon=True).start()
    
    def atualizar_historico(self):
        """Atualiza a treeview com o histórico de backups"""
        for item in self.tree_historico.get_children():
            self.tree_historico.delete(item)
        
        historico = self.backup_manager.historico
        if not historico:
            return
        
        for backup in historico:
            try:
                data = backup.get("data")
                if isinstance(data, str):
                    data = datetime.fromisoformat(data)
                
                data_str = data.strftime("%Y-%m-%d %H:%M:%S") if data else "N/A"
                arquivo = backup.get("arquivo", "N/A")
                sucessos = backup.get("equipamentos", 0)
                falhas = backup.get("falhas", 0)
                enviado = "✅ Enviado" if backup.get("enviado", False) else "❌ Não enviado"
                
                self.tree_historico.insert("", "end", values=(
                    data_str,
                    arquivo,
                    sucessos,
                    falhas,
                    enviado
                ))
            except Exception as e:
                print(f"Erro ao exibir item do histórico: {e}")
    
    def limpar_historico(self):
        """Limpa o histórico de backups"""
        if messagebox.askyesno("Confirmar", "Limpar todo o histórico de backups?"):
            self.backup_manager.historico = []
            self.backup_manager.salvar_historico()
            self.atualizar_historico()
            messagebox.showinfo("Sucesso", "Histórico limpo!")