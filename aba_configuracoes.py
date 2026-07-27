# aba_configuracoes.py - COMPACTO COM SELECTS
import customtkinter as ctk
from tkinter import messagebox

class AbaConfiguracoes:
    def __init__(self, parent, config, monitor, atualizar_callback, firebase_manager=None):
        self.parent = parent
        self.config = config
        self.monitor = monitor
        self.atualizar_callback = atualizar_callback
        self.firebase_manager = firebase_manager
        self.configuracoes = config.get_configuracoes()
        
        self.criar_aba()
    
    def criar_aba(self):
        self.container = ctk.CTkScrollableFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        frame = ctk.CTkFrame(self.container)
        frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="⚙️ Configurações do Monitoramento", font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=10)
        
        # 1. Intervalo
        ctk.CTkLabel(frame, text="1. Intervalo entre verificações:").pack(anchor="w", padx=10, pady=(5,0))
        self.combo_intervalo = ctk.CTkComboBox(frame, values=["1s", "2s", "3s", "5s", "10s", "15s", "30s"], width=120)
        self.combo_intervalo.pack(anchor="w", padx=10, pady=5)
        
        intervalo_atual = self.configuracoes.get("intervalo_segundos", 5)
        self.combo_intervalo.set(f"{intervalo_atual}s")
        
        # 2. Falhas
        ctk.CTkLabel(frame, text="2. Falhas consecutivas para OFFLINE:").pack(anchor="w", padx=10, pady=(15,0))
        self.combo_falhas = ctk.CTkComboBox(frame, values=["1","2","3","5","10"], width=120)
        self.combo_falhas.pack(anchor="w", padx=10, pady=5)
        
        falhas_atual = self.configuracoes.get("quantidade_pings", 3)
        self.combo_falhas.set(str(falhas_atual))
        
        # 3. Timeout
        ctk.CTkLabel(frame, text="3. Timeout do ping:").pack(anchor="w", padx=10, pady=(15,0))
        self.combo_timeout = ctk.CTkComboBox(frame, values=["200ms", "300ms", "500ms", "800ms", "1000ms"], width=120)
        self.combo_timeout.pack(anchor="w", padx=10, pady=5)
        
        timeout_atual = self.configuracoes.get("timeout_ms", 500)
        self.combo_timeout.set(f"{timeout_atual}ms")
        
        # 4. Salvamento
        ctk.CTkLabel(frame, text="4. Salvar status no banco a cada:").pack(anchor="w", padx=10, pady=(15,0))
        self.combo_salvar = ctk.CTkComboBox(frame, values=["1 minuto", "2 minutos", "5 minutos", "10 minutos", "30 minutos"], width=150)
        self.combo_salvar.pack(anchor="w", padx=10, pady=5)
        
        salvar_atual = self.configuracoes.get("salvar_intervalo", 60)
        if salvar_atual <= 60: self.combo_salvar.set("1 minuto")
        elif salvar_atual <= 120: self.combo_salvar.set("2 minutos")
        elif salvar_atual <= 300: self.combo_salvar.set("5 minutos")
        elif salvar_atual <= 600: self.combo_salvar.set("10 minutos")
        else: self.combo_salvar.set("30 minutos")
        
        self.lbl_status = ctk.CTkLabel(frame, text="", font=("Arial", 11))
        self.lbl_status.pack(anchor="w", padx=10, pady=10)
        
        ctk.CTkButton(frame, text="💾 Salvar", command=self.salvar, width=120).pack(anchor="w", padx=10, pady=10)
    
    def salvar(self):
        try:
            salvar_map = {
                "1 minuto": 60, "2 minutos": 120, "5 minutos": 300,
                "10 minutos": 600, "30 minutos": 1800
            }
            
            novas_configs = {
                "timeout_ms": int(self.combo_timeout.get().replace("ms","")),
                "intervalo_segundos": int(self.combo_intervalo.get().replace("s","")),
                "quantidade_pings": int(self.combo_falhas.get()),
                "limite_instavel": 50,
                "limite_offline": 100,
                "snmp_intervalo": 30,
                "salvar_intervalo": salvar_map.get(self.combo_salvar.get(), 60),
                "heartbeat_intervalo": 60
            }
            
            self.config.set_configuracoes(novas_configs)
            
            from database import Database
            db = Database()
            equipamentos = db.listar_equipamentos()
            clientes = db.listar_clientes()
            self.monitor.atualizar_configuracoes(equipamentos, novas_configs, clientes)
            
            if self.atualizar_callback:
                self.atualizar_callback()
            
            self.lbl_status.configure(text="✅ Salvo!", text_color="green")
            self.container.after(3000, lambda: self.lbl_status.configure(text=""))
            messagebox.showinfo("Sucesso", "Configurações salvas!")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")