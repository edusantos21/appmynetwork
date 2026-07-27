import customtkinter as ctk
from tkinter import messagebox
import threading


class AbaTelegram:
    def __init__(self, parent, config, telegram_manager, firebase_manager=None):
        self.parent = parent
        self.config = config
        self.telegram_manager = telegram_manager
        self.firebase_manager = firebase_manager
        
        # Templates padrão
        self.templates_padrao = {
            "online": "🟢 ONLINE - EQUIPAMENTO: 📡 {nome} | 📍 {localidade} | 🌐 {ip} | ⏱️ {uptime} | {status} | ⏱️ Latência: {latencia}ms",
            "instavel": "🟡 INSTÁVEL - EQUIPAMENTO: 📡 {nome} | 📍 {localidade} | 🌐 {ip} | ⏱️ {uptime} | {status} | ⏱️ Latência: {latencia}ms",
            "offline": "🔴 OFFLINE - EQUIPAMENTO: 📡 {nome} | 📍 {localidade} | 🌐 {ip} | ⏱️ {uptime} | {status}",
            "cliente_online": "🟢 ONLINE - CLIENTE: 👤 {nome} | 🌐 {ip} | {status} | ⏱️ Latência: {latencia}ms",
            "cliente_instavel": "🟡 INSTÁVEL - CLIENTE: 👤 {nome} | 🌐 {ip} | {status} | ⏱️ Latência: {latencia}ms",
            "cliente_offline": "🔴 OFFLINE - CLIENTE: 👤 {nome} | 🌐 {ip} | {status}"
        }
        
        self.criar_aba()
        self.carregar_configuracoes()
    
    def criar_aba(self):
        self.container = ctk.CTkScrollableFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        lbl_titulo = ctk.CTkLabel(self.container, text="🤖 Configurações do Telegram", font=("Arial", 18, "bold"))
        lbl_titulo.pack(anchor="w", pady=(0, 15))
        
        # ========== CONFIGURAÇÕES BÁSICAS ==========
        frame_basico = ctk.CTkFrame(self.container)
        frame_basico.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_basico, text="🔧 Configurações Básicas", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(frame_basico, text="Token do Bot:").pack(anchor="w", padx=10, pady=(5, 0))
        self.txt_token = ctk.CTkEntry(frame_basico, placeholder_text="Token do Bot", width=500)
        self.txt_token.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(frame_basico, text="Chat ID:").pack(anchor="w", padx=10, pady=(5, 0))
        self.txt_chat_id = ctk.CTkEntry(frame_basico, placeholder_text="Chat ID (ex: -4500301441)", width=500)
        self.txt_chat_id.pack(anchor="w", padx=10, pady=5)
        
        btn_frame_basico = ctk.CTkFrame(frame_basico)
        btn_frame_basico.pack(anchor="w", padx=10, pady=10)
        
        btn_testar = ctk.CTkButton(btn_frame_basico, text="🔗 Testar Conexão", command=self.testar_conexao, width=180)
        btn_testar.pack(side="left", padx=5)
        
        btn_salvar_basico = ctk.CTkButton(btn_frame_basico, text="💾 Salvar Configurações", command=self.salvar_configuracoes, width=180)
        btn_salvar_basico.pack(side="left", padx=5)
        
        self.lbl_status = ctk.CTkLabel(frame_basico, text="", font=("Arial", 11))
        self.lbl_status.pack(anchor="w", padx=10, pady=5)
        
        # Separador
        separator = ctk.CTkFrame(self.container, height=2, fg_color="gray")
        separator.pack(fill="x", pady=15)
        
        # ========== TEMPLATES DE MENSAGENS ==========
        frame_templates = ctk.CTkFrame(self.container)
        frame_templates.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_templates, text="📝 Templates de Mensagens", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        lbl_info_templates = ctk.CTkLabel(frame_templates, 
            text="Personalize o formato das mensagens enviadas. Use as variáveis entre {chaves}.\n"
                 "Variáveis disponíveis: {nome}, {ip}, {localidade}, {status}, {latencia}, {uptime}, {clientes}, {ssid}, {mac}, {modelo}, {hora}, {data}",
            font=("Arial", 10), text_color="gray", justify="left")
        lbl_info_templates.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Template ONLINE
        ctk.CTkLabel(frame_templates, text="🟢 Mensagem ONLINE (Equipamento):").pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_template_online = ctk.CTkTextbox(frame_templates, height=50, width=600)
        self.txt_template_online.pack(anchor="w", padx=10, pady=5)
        
        # Template INSTÁVEL
        ctk.CTkLabel(frame_templates, text="🟡 Mensagem INSTÁVEL (Equipamento):").pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_template_instavel = ctk.CTkTextbox(frame_templates, height=50, width=600)
        self.txt_template_instavel.pack(anchor="w", padx=10, pady=5)
        
        # Template OFFLINE
        ctk.CTkLabel(frame_templates, text="🔴 Mensagem OFFLINE (Equipamento):").pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_template_offline = ctk.CTkTextbox(frame_templates, height=50, width=600)
        self.txt_template_offline.pack(anchor="w", padx=10, pady=5)
        
        # Template Cliente ONLINE
        ctk.CTkLabel(frame_templates, text="🟢 Mensagem ONLINE (Cliente):").pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_template_cliente_online = ctk.CTkTextbox(frame_templates, height=40, width=600)
        self.txt_template_cliente_online.pack(anchor="w", padx=10, pady=5)
        
        # Template Cliente OFFLINE
        ctk.CTkLabel(frame_templates, text="🔴 Mensagem OFFLINE (Cliente):").pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_template_cliente_offline = ctk.CTkTextbox(frame_templates, height=40, width=600)
        self.txt_template_cliente_offline.pack(anchor="w", padx=10, pady=5)
        
        btn_frame_templates = ctk.CTkFrame(frame_templates)
        btn_frame_templates.pack(anchor="w", padx=10, pady=15)
        
        btn_salvar_templates = ctk.CTkButton(btn_frame_templates, text="💾 Salvar Templates", command=self.salvar_templates, width=180)
        btn_salvar_templates.pack(side="left", padx=5)
        
        btn_restaurar = ctk.CTkButton(btn_frame_templates, text="🔄 Restaurar Padrão", command=self.restaurar_templates_padrao, width=180, fg_color="orange")
        btn_restaurar.pack(side="left", padx=5)
        
        self.lbl_template_status = ctk.CTkLabel(frame_templates, text="", font=("Arial", 11))
        self.lbl_template_status.pack(anchor="w", padx=10, pady=5)
        
        # Separador
        separator2 = ctk.CTkFrame(self.container, height=2, fg_color="gray")
        separator2.pack(fill="x", pady=15)
        
        # ========== PREVIEW ==========
        frame_preview = ctk.CTkFrame(self.container)
        frame_preview.pack(fill="x", pady=10)
        
        ctk.CTkLabel(frame_preview, text="👁️ Preview da Mensagem", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(frame_preview, text="Selecione um tipo para visualizar:").pack(anchor="w", padx=10, pady=(5, 0))
        
        self.preview_tipo = ctk.CTkComboBox(frame_preview, values=["ONLINE", "INSTÁVEL", "OFFLINE", "CLIENTE ONLINE", "CLIENTE OFFLINE"], width=200)
        self.preview_tipo.pack(anchor="w", padx=10, pady=5)
        self.preview_tipo.set("ONLINE")
        
        btn_preview = ctk.CTkButton(frame_preview, text="🔄 Atualizar Preview", command=self.atualizar_preview, width=150)
        btn_preview.pack(anchor="w", padx=10, pady=5)
        
        self.lbl_preview = ctk.CTkLabel(frame_preview, text="", font=("Arial", 11), wraplength=600, justify="left")
        self.lbl_preview.pack(anchor="w", padx=10, pady=10)
    
    def carregar_configuracoes(self):
        """Carrega as configurações salvas"""
        telegram_config = self.config.get_telegram_config()
        
        # Carregar token e chat_id
        self.txt_token.delete(0, "end")
        self.txt_token.insert(0, telegram_config.get("token", ""))
        
        self.txt_chat_id.delete(0, "end")
        self.txt_chat_id.insert(0, telegram_config.get("chat_id", ""))
        
        # Carregar templates ou usar padrão
        templates = telegram_config.get("templates", {})
        
        self.txt_template_online.delete("1.0", "end")
        self.txt_template_online.insert("1.0", templates.get("online", self.templates_padrao["online"]))
        
        self.txt_template_instavel.delete("1.0", "end")
        self.txt_template_instavel.insert("1.0", templates.get("instavel", self.templates_padrao["instavel"]))
        
        self.txt_template_offline.delete("1.0", "end")
        self.txt_template_offline.insert("1.0", templates.get("offline", self.templates_padrao["offline"]))
        
        self.txt_template_cliente_online.delete("1.0", "end")
        self.txt_template_cliente_online.insert("1.0", templates.get("cliente_online", self.templates_padrao["cliente_online"]))
        
        self.txt_template_cliente_offline.delete("1.0", "end")
        self.txt_template_cliente_offline.insert("1.0", templates.get("cliente_offline", self.templates_padrao["cliente_offline"]))
        
        # Atualizar status
        if self.telegram_manager.esta_configurado():
            self.lbl_status.configure(text="✅ Telegram configurado e funcionando!", text_color="green")
        elif telegram_config.get("token") and telegram_config.get("chat_id"):
            self.lbl_status.configure(text="⚠️ Configurações salvas, mas não testadas", text_color="orange")
        else:
            self.lbl_status.configure(text="⚪ Telegram não configurado", text_color="gray")
    
    def salvar_configuracoes(self):
        """Salva token e chat_id localmente e no Firebase"""
        token = self.txt_token.get().strip()
        chat_id = self.txt_chat_id.get().strip()
        
        if not token or not chat_id:
            messagebox.showwarning("Aviso", "Preencha o Token e o Chat ID!")
            return
        
        telegram_config = self.config.get_telegram_config()
        telegram_config["token"] = token
        telegram_config["chat_id"] = chat_id
        
        # Salvar localmente
        self.config.set_telegram_config(telegram_config)
        self.telegram_manager.configurar(token, chat_id)
        
        self.lbl_status.configure(text="💾 Salvando...", text_color="orange")
        
        # Salvar no Firebase em segundo plano
        def salvar_firebase():
            try:
                if self.firebase_manager and self.firebase_manager.esta_configurado():
                    configuracoes = {
                        "monitor": self.config.get_configuracoes(),
                        "telegram": telegram_config,
                        "snmp": self.config.get_snmp_config()
                    }
                    self.firebase_manager.salvar_configuracoes(configuracoes)
                    print("✅ Configurações do Telegram salvas no Firebase")
                
                self.lbl_status.after(0, lambda: self.lbl_status.configure(text="✅ Configurações salvas com sucesso!", text_color="green"))
                self.container.after(3000, lambda: self.lbl_status.configure(
                    text="✅ Telegram configurado e funcionando!" if self.telegram_manager.esta_configurado() else "⚠️ Configurações salvas, mas não testadas",
                    text_color="green" if self.telegram_manager.esta_configurado() else "orange"
                ))
            except Exception as e:
                print(f"❌ Erro ao salvar no Firebase: {e}")
                self.lbl_status.after(0, lambda: self.lbl_status.configure(text="✅ Salvo localmente (Firebase indisponível)", text_color="orange"))
        
        threading.Thread(target=salvar_firebase, daemon=True).start()
        messagebox.showinfo("Sucesso", "Configurações do Telegram salvas!")
    
    def salvar_templates(self):
        """Salva os templates personalizados localmente e no Firebase"""
        telegram_config = self.config.get_telegram_config()
        
        if "templates" not in telegram_config:
            telegram_config["templates"] = {}
        
        telegram_config["templates"]["online"] = self.txt_template_online.get("1.0", "end-1c").strip()
        telegram_config["templates"]["instavel"] = self.txt_template_instavel.get("1.0", "end-1c").strip()
        telegram_config["templates"]["offline"] = self.txt_template_offline.get("1.0", "end-1c").strip()
        telegram_config["templates"]["cliente_online"] = self.txt_template_cliente_online.get("1.0", "end-1c").strip()
        telegram_config["templates"]["cliente_offline"] = self.txt_template_cliente_offline.get("1.0", "end-1c").strip()
        
        # Salvar localmente
        self.config.set_telegram_config(telegram_config)
        
        self.lbl_template_status.configure(text="💾 Salvando templates...", text_color="orange")
        
        # Salvar no Firebase em segundo plano
        def salvar_firebase():
            try:
                if self.firebase_manager and self.firebase_manager.esta_configurado():
                    configuracoes = {
                        "monitor": self.config.get_configuracoes(),
                        "telegram": telegram_config,
                        "snmp": self.config.get_snmp_config()
                    }
                    self.firebase_manager.salvar_configuracoes(configuracoes)
                    print("✅ Templates do Telegram salvos no Firebase")
                
                self.lbl_template_status.after(0, lambda: self.lbl_template_status.configure(text="✅ Templates salvos com sucesso!", text_color="green"))
                self.container.after(3000, lambda: self.lbl_template_status.configure(text=""))
            except Exception as e:
                print(f"❌ Erro ao salvar templates no Firebase: {e}")
                self.lbl_template_status.after(0, lambda: self.lbl_template_status.configure(text="✅ Templates salvos localmente", text_color="green"))
        
        threading.Thread(target=salvar_firebase, daemon=True).start()
        messagebox.showinfo("Sucesso", "Templates de mensagem salvos!")
    
    def restaurar_templates_padrao(self):
        """Restaura os templates para o padrão"""
        if messagebox.askyesno("Confirmar", "Restaurar todos os templates para o padrão?"):
            self.txt_template_online.delete("1.0", "end")
            self.txt_template_online.insert("1.0", self.templates_padrao["online"])
            
            self.txt_template_instavel.delete("1.0", "end")
            self.txt_template_instavel.insert("1.0", self.templates_padrao["instavel"])
            
            self.txt_template_offline.delete("1.0", "end")
            self.txt_template_offline.insert("1.0", self.templates_padrao["offline"])
            
            self.txt_template_cliente_online.delete("1.0", "end")
            self.txt_template_cliente_online.insert("1.0", self.templates_padrao["cliente_online"])
            
            self.txt_template_cliente_offline.delete("1.0", "end")
            self.txt_template_cliente_offline.insert("1.0", self.templates_padrao["cliente_offline"])
            
            self.lbl_template_status.configure(text="✅ Templates restaurados para o padrão!", text_color="green")
            self.container.after(3000, lambda: self.lbl_template_status.configure(text=""))
    
    def testar_conexao(self):
        """Testa a conexão com o Telegram"""
        token = self.txt_token.get().strip()
        chat_id = self.txt_chat_id.get().strip()
        
        if not token or not chat_id:
            messagebox.showwarning("Aviso", "Configure o Token e Chat ID primeiro!")
            return
        
        # Configurar temporariamente para teste
        self.telegram_manager.configurar(token, chat_id)
        
        self.lbl_status.configure(text="🔗 Testando conexão...", text_color="orange")
        
        def testar():
            if self.telegram_manager.testar():
                self.lbl_status.after(0, lambda: self.lbl_status.configure(text="✅ Telegram conectado com sucesso!", text_color="green"))
                messagebox.showinfo("Sucesso", "✅ Mensagem de teste enviada!\nVerifique seu Telegram.")
            else:
                self.lbl_status.after(0, lambda: self.lbl_status.configure(text="❌ Falha na conexão com Telegram", text_color="red"))
                messagebox.showerror("Erro", "❌ Falha ao enviar mensagem.\nVerifique o Token e Chat ID.")
        
        threading.Thread(target=testar, daemon=True).start()
    
    def atualizar_preview(self):
        """Atualiza o preview da mensagem"""
        tipo = self.preview_tipo.get()
        
        # Dados de exemplo
        exemplo = {
            "nome": "FIBRANET-12",
            "ip": "192.168.189.24",
            "localidade": "SALGADO",
            "status": "🟢 ONLINE" if "ONLINE" in tipo else ("🟡 INSTÁVEL" if "INSTÁVEL" in tipo else "🔴 OFFLINE"),
            "latencia": "8.5",
            "uptime": "2 days, 1:30",
            "clientes": "6",
            "ssid": "FIBRANET-12",
            "mac": "24:A4:3C:89:EE:79",
            "modelo": "NanoStation loco M5",
            "hora": "14:30:00",
            "data": "18/04/2026 14:30:00"
        }
        
        if "CLIENTE" in tipo:
            if "ONLINE" in tipo:
                template = self.txt_template_cliente_online.get("1.0", "end-1c").strip()
            else:
                template = self.txt_template_cliente_offline.get("1.0", "end-1c").strip()
            exemplo["nome"] = "Cliente Exemplo"
            exemplo["ip"] = "192.168.1.100"
        else:
            if "ONLINE" in tipo:
                template = self.txt_template_online.get("1.0", "end-1c").strip()
            elif "INSTÁVEL" in tipo:
                template = self.txt_template_instavel.get("1.0", "end-1c").strip()
            else:
                template = self.txt_template_offline.get("1.0", "end-1c").strip()
        
        # Substituir variáveis
        preview = template
        for chave, valor in exemplo.items():
            preview = preview.replace("{" + chave + "}", str(valor))
        
        self.lbl_preview.configure(text=f"📱 Preview:\n{preview}")
    
    def get_templates(self):
        """Retorna os templates atuais para uso no monitor"""
        telegram_config = self.config.get_telegram_config()
        templates = telegram_config.get("templates", {})
        
        return {
            "online": templates.get("online", self.templates_padrao["online"]),
            "instavel": templates.get("instavel", self.templates_padrao["instavel"]),
            "offline": templates.get("offline", self.templates_padrao["offline"]),
            "cliente_online": templates.get("cliente_online", self.templates_padrao["cliente_online"]),
            "cliente_instavel": templates.get("cliente_instavel", self.templates_padrao["cliente_instavel"]),
            "cliente_offline": templates.get("cliente_offline", self.templates_padrao["cliente_offline"])
        }