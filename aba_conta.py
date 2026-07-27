# aba_conta.py - CORRIGIDO (TÚNEL AUTOMÁTICO, SEM SELETOR DE INTERVALO)
import customtkinter as ctk
import threading
import time
import os
import sys
import datetime

class AbaConta:
    def __init__(self, parent, config, firebase_auth, tunnel_manager):
        self.parent = parent
        self.config = config
        self.firebase_auth = firebase_auth
        self.tunnel_manager = tunnel_manager
        
        self.reconexao_ativa = False
        self.thread_reconexao = None
        
        self.criar_aba()
        self.carregar_configuracoes()
        self.atualizar_status()
        self.atualizar_status_tunel()
    
    def criar_aba(self):
        self.container = ctk.CTkScrollableFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(self.container, text="CONTA MY NETWORK", font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 15))
        
        # ========== CREDENCIAIS ==========
        frame_credenciais = ctk.CTkFrame(self.container)
        frame_credenciais.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_credenciais, text="Credenciais Firebase", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(frame_credenciais, text="Email:").pack(anchor="w", padx=10, pady=(5, 0))
        self.entry_email = ctk.CTkEntry(frame_credenciais, width=400, placeholder_text="seuemail@gmail.com")
        self.entry_email.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_credenciais, text="Senha:").pack(anchor="w", padx=10, pady=(5, 0))
        self.entry_senha = ctk.CTkEntry(frame_credenciais, width=400, placeholder_text="senha", show="*")
        self.entry_senha.pack(anchor="w", padx=10, pady=5)
        
        self.lembrar_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame_credenciais, text="Lembrar minhas credenciais", variable=self.lembrar_var).pack(anchor="w", padx=10, pady=5)
        
        # ========== PORTA DO SERVIDOR ==========
        frame_porta = ctk.CTkFrame(self.container)
        frame_porta.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_porta, text="Porta do Servidor", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(frame_porta, text="Porta que o Flask vai usar. Reinicie o app apos mudar.", 
                     font=("Arial", 10), text_color="gray").pack(anchor="w", padx=10, pady=(0, 5))
        
        frame_porta_config = ctk.CTkFrame(frame_porta)
        frame_porta_config.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_porta_config, text="Porta:").pack(side="left", padx=(0, 5))
        self.entry_porta = ctk.CTkEntry(frame_porta_config, width=80)
        self.entry_porta.pack(side="left", padx=5)
        self.entry_porta.insert(0, "8080")
        
        ctk.CTkButton(frame_porta_config, text="Salvar", command=self.salvar_porta, width=80).pack(side="left", padx=10)
        
        # ========== RECONEXÃO AUTOMÁTICA ==========
        frame_reconexao = ctk.CTkFrame(self.container)
        frame_reconexao.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_reconexao, text="Reconexao Automatica Firebase", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.reconexao_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame_reconexao, text="Ativar reconexao automatica", variable=self.reconexao_var, command=self.on_reconexao_toggle).pack(anchor="w", padx=10, pady=5)
        
        frame_config = ctk.CTkFrame(frame_reconexao)
        frame_config.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_config, text="Intervalo (min):").pack(side="left", padx=(0, 5))
        self.combo_intervalo = ctk.CTkComboBox(frame_config, values=["1", "2", "5", "10"], width=70)
        self.combo_intervalo.pack(side="left", padx=5)
        self.combo_intervalo.set("1")
        
        ctk.CTkLabel(frame_config, text="Max tentativas:").pack(side="left", padx=(15, 5))
        self.combo_max_tentativas = ctk.CTkComboBox(frame_config, values=["3", "5", "10", "infinito"], width=80)
        self.combo_max_tentativas.pack(side="left", padx=5)
        self.combo_max_tentativas.set("infinito")
        
        # ========== CONTROLE DO TÚNEL ==========
        frame_tunel_controle = ctk.CTkFrame(self.container)
        frame_tunel_controle.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_tunel_controle, text="Controle do Túnel Cloudflare", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        btn_frame_tunel = ctk.CTkFrame(frame_tunel_controle)
        btn_frame_tunel.pack(anchor="w", padx=10, pady=10)
        
        self.btn_reiniciar_tunel = ctk.CTkButton(
            btn_frame_tunel, text="🔄 Reiniciar Túnel Agora", 
            command=self.reiniciar_tunel_manual,
            width=180, fg_color="#00aa55"
        )
        self.btn_reiniciar_tunel.pack(side="left", padx=5)
        
        self.lbl_status_tunel = ctk.CTkLabel(frame_tunel_controle, text="⏳ Aguardando túnel...", font=("Arial", 12, "bold"))
        self.lbl_status_tunel.pack(anchor="w", padx=10, pady=(10, 5))
        
        # ========== BOTÕES AÇÕES ==========
        btn_frame = ctk.CTkFrame(self.container)
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="🔐 AUTENTICAR", command=self.autenticar, 
                     width=180, height=35, font=("Arial", 12, "bold"), fg_color="green").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔍 Testar Conexao", command=self.testar_conexao, 
                     width=130).pack(side="left", padx=5)
        
        # ========== STATUS ==========
        frame_status = ctk.CTkFrame(self.container)
        frame_status.pack(fill="x", pady=10)
        
        self.lbl_status = ctk.CTkLabel(frame_status, text="Status: Nao autenticado", font=("Arial", 11, "bold"))
        self.lbl_status.pack(anchor="w", padx=10, pady=3)
        
        self.lbl_ultima_tentativa = ctk.CTkLabel(frame_status, text="Ultima tentativa Firebase: --", font=("Arial", 10))
        self.lbl_ultima_tentativa.pack(anchor="w", padx=10, pady=1)
        
        self.lbl_proxima_tentativa = ctk.CTkLabel(frame_status, text="Proxima tentativa Firebase: --", font=("Arial", 10))
        self.lbl_proxima_tentativa.pack(anchor="w", padx=10, pady=1)
        
        self.lbl_tentativas_falhas = ctk.CTkLabel(frame_status, text="Tentativas falhas: 0", font=("Arial", 10))
        self.lbl_tentativas_falhas.pack(anchor="w", padx=10, pady=1)
        
        # ========== TÚNEL (URL) ==========
        frame_tunel = ctk.CTkFrame(self.container)
        frame_tunel.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_tunel, text="Tunel Cloudflare", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.lbl_url = ctk.CTkLabel(frame_tunel, text="URL: Aguardando...", font=("Arial", 10), text_color="cyan")
        self.lbl_url.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_status_site = ctk.CTkLabel(frame_tunel, text="Status: Aguardando", font=("Arial", 10))
        self.lbl_status_site.pack(anchor="w", padx=10, pady=2)
        
        ctk.CTkButton(frame_tunel, text="📋 Copiar URL", command=self.copiar_url, width=120).pack(anchor="w", padx=10, pady=5)
        
        self.lbl_notificacao = ctk.CTkLabel(self.container, text="", font=("Arial", 11, "bold"))
        self.lbl_notificacao.pack(pady=5)
    
    def _notificar(self, msg, cor="green", duracao=3000):
        self.lbl_notificacao.configure(text=msg, text_color=cor)
        if duracao > 0:
            self.container.after(duracao, lambda: self.lbl_notificacao.configure(text=""))
    
    def _get_url_atual(self):
        return self.tunnel_manager.get_url()
    
    def _atualizar_label_tunel(self):
        try:
            url = self._get_url_atual()
            if url:
                self.lbl_status_tunel.configure(text="🟢 Túnel Online")
            else:
                self.lbl_status_tunel.configure(text="🔴 Aguardando túnel...")
        except:
            pass
    
    def reiniciar_tunel_manual(self):
        self.btn_reiniciar_tunel.configure(state="disabled", text="⏳ Reiniciando...")
        self._notificar("🔄 Reiniciando túnel...", "orange", 0)
        
        def _reiniciar():
            try:
                import tunnel_manager as tm
                nova_url = tm.reiniciar_tunel(forcar=True)
                self.container.after(0, lambda: self._fim_reinicio(nova_url))
            except Exception as e:
                print(f"❌ Erro: {e}")
                self.container.after(0, lambda: self._erro_reinicio(str(e)))
        
        threading.Thread(target=_reiniciar, daemon=True).start()
    
    def _fim_reinicio(self, nova_url):
        self.btn_reiniciar_tunel.configure(state="normal", text="🔄 Reiniciar Túnel Agora")
        if nova_url:
            self.lbl_url.configure(text=f"URL: {nova_url}/equipamentos", text_color="green")
            self.lbl_status_site.configure(text="Status: Online", text_color="green")
            self._notificar("✅ Túnel renovado!")
            self._atualizar_label_tunel()
        else:
            self._notificar("❌ Falha ao renovar túnel", "red")
    
    def _erro_reinicio(self, erro):
        self.btn_reiniciar_tunel.configure(state="normal", text="🔄 Reiniciar Túnel Agora")
        self._notificar(f"❌ Erro: {erro[:50]}", "red")
    
    def salvar_porta(self):
        try:
            porta = int(self.entry_porta.get())
            if porta < 1 or porta > 65535:
                self._notificar("Porta inválida (1-65535)", "red")
                return
            configs = self.config.get_configuracoes()
            configs["porta_flask"] = porta
            self.config.set_configuracoes(configs)
            self._notificar(f"✅ Porta {porta} salva!")
        except:
            self._notificar("Digite um número válido", "red")
    
    def carregar_configuracoes(self):
        credenciais = self.config.get_firebase_credenciais()
        if credenciais:
            self.entry_email.delete(0, "end")
            self.entry_email.insert(0, credenciais.get("email", ""))
            self.entry_senha.delete(0, "end")
            self.entry_senha.insert(0, credenciais.get("senha", ""))
            self.lembrar_var.set(credenciais.get("lembrar", False))
            if credenciais.get("lembrar") and credenciais.get("email") and credenciais.get("senha"):
                self.firebase_auth.configurar(credenciais["email"], credenciais["senha"])
        
        reconexao = self.config.get_reconexao()
        self.reconexao_var.set(reconexao.get("ativa", False))
        self.combo_intervalo.set(str(reconexao.get("intervalo_minutos", 1)))
        max_t = reconexao.get("max_tentativas", 0)
        self.combo_max_tentativas.set("infinito" if max_t == 0 else str(max_t))
        if self.reconexao_var.get():
            self.iniciar_reconexao()
        
        porta = self.config.get_configuracoes().get("porta_flask", 8080)
        self.entry_porta.delete(0, "end")
        self.entry_porta.insert(0, str(porta))
    
    def salvar_configuracoes(self):
        if self.lembrar_var.get():
            credenciais = {"email": self.entry_email.get().strip(), "senha": self.entry_senha.get(), "lembrar": True}
        else:
            credenciais = {"email": "", "senha": "", "lembrar": False}
        self.config.set_firebase_credenciais(credenciais)
        
        max_t = self.combo_max_tentativas.get()
        max_t = 0 if max_t == "infinito" else int(max_t)
        reconexao = {
            "ativa": self.reconexao_var.get(),
            "intervalo_minutos": int(self.combo_intervalo.get()),
            "max_tentativas": max_t,
            "tentativas_atual": self.firebase_auth.tentativas_falhas if hasattr(self.firebase_auth, 'tentativas_falhas') else 0
        }
        self.config.set_reconexao(reconexao)
    
    def on_reconexao_toggle(self):
        if self.reconexao_var.get():
            self.iniciar_reconexao()
        else:
            self.parar_reconexao()
        self.salvar_configuracoes()
    
    def iniciar_reconexao(self):
        if self.thread_reconexao and self.thread_reconexao.is_alive():
            return
        self.reconexao_ativa = True
        self.thread_reconexao = threading.Thread(target=self._loop_reconexao, daemon=True)
        self.thread_reconexao.start()
    
    def parar_reconexao(self):
        self.reconexao_ativa = False
    
    def _loop_reconexao(self):
        while self.reconexao_ativa:
            try:
                if self.firebase_auth.autenticado:
                    time.sleep(int(self.combo_intervalo.get()) * 60)
                    continue
                reconexao_config = self.config.get_reconexao()
                max_t = reconexao_config.get("max_tentativas", 0)
                if max_t > 0 and self.firebase_auth.tentativas_falhas >= max_t:
                    self.reconexao_ativa = False
                    self.reconexao_var.set(False)
                    self.atualizar_status()
                    break
                self.atualizar_status()
                if self.firebase_auth.autenticar():
                    url = self.tunnel_manager.get_url()
                    if url:
                        self.firebase_auth.salvar_url(url)
                    self.atualizar_status()
                else:
                    self.atualizar_status()
                time.sleep(int(self.combo_intervalo.get()) * 60)
            except:
                time.sleep(60)
    
    def autenticar(self):
        email = self.entry_email.get().strip()
        senha = self.entry_senha.get()
        if not email or not senha:
            self._notificar("⚠️ Preencha email e senha!", "orange")
            return
        self.firebase_auth.configurar(email, senha)
        self.lbl_status.configure(text="Status: Autenticando...", text_color="orange")
        self._notificar("🔄 Autenticando...", "orange", 0)
        def _auth():
            if self.firebase_auth.autenticar():
                url = self.tunnel_manager.get_url()
                if url:
                    self.firebase_auth.salvar_url(url)
                self.atualizar_status()
                self.salvar_configuracoes()
                if not self.reconexao_var.get():
                    self.reconexao_var.set(True)
                    self.iniciar_reconexao()
                    self.salvar_configuracoes()
                self._notificar("✅ Autenticado!")
            else:
                self.atualizar_status()
                self._notificar("❌ Falha na autenticação!", "red")
        threading.Thread(target=_auth, daemon=True).start()
    
    def testar_conexao(self):
        email = self.entry_email.get().strip()
        senha = self.entry_senha.get()
        if not email or not senha:
            self._notificar("⚠️ Preencha email e senha!", "orange")
            return
        self.lbl_status.configure(text="Status: Testando...", text_color="orange")
        self._notificar("🔄 Testando...", "orange", 0)
        def _test():
            from firebase_auth import FirebaseAuth
            auth = FirebaseAuth()
            auth.configurar(email, senha)
            if auth.autenticar():
                self.lbl_status.after(0, lambda: self.lbl_status.configure(text="Status: Conexao OK!", text_color="green"))
                self._notificar("✅ Conectado ao Firebase!")
            else:
                self.lbl_status.after(0, lambda: self.lbl_status.configure(text="Status: Falha", text_color="red"))
                self._notificar("❌ Falha na conexão!", "red")
        threading.Thread(target=_test, daemon=True).start()
    
    def atualizar_status(self):
        if self.firebase_auth.autenticado:
            self.lbl_status.configure(text=f"Status: ✅ Autenticado - {self.firebase_auth.email}", text_color="green")
        else:
            self.lbl_status.configure(text="Status: ⚠️ Não autenticado", text_color="orange")
        if self.firebase_auth.ultima_tentativa:
            t = self.firebase_auth.ultima_tentativa.strftime('%d/%m/%Y %H:%M:%S')
            self.lbl_ultima_tentativa.configure(text=f"Última tentativa Firebase: {t}")
        if self.reconexao_ativa and not self.firebase_auth.autenticado:
            self.lbl_proxima_tentativa.configure(text=f"Próxima Firebase: em {self.combo_intervalo.get()} min")
        else:
            self.lbl_proxima_tentativa.configure(text="Próxima Firebase: --")
        self.lbl_tentativas_falhas.configure(text=f"Tentativas falhas Firebase: {self.firebase_auth.tentativas_falhas}")
    
    def atualizar_status_tunel(self):
        url = self._get_url_atual()
        if url:
            self.lbl_url.configure(text=f"URL: {url}/equipamentos", text_color="green")
            self.lbl_status_site.configure(text="Status: Online", text_color="green")
        else:
            self.lbl_url.configure(text="URL: Aguardando...", text_color="orange")
            self.lbl_status_site.configure(text="Status: Aguardando túnel", text_color="red")
        self._atualizar_label_tunel()
        self.container.after(5000, self.atualizar_status_tunel)
    
    def copiar_url(self):
        url = self._get_url_atual()
        if url:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(f"{url}/equipamentos")
            self._notificar("✅ URL copiada!")
        else:
            self._notificar("⚠️ Túnel não está ativo!", "orange")