# aba_logs.py - VERSÃO LEVE
import customtkinter as ctk
from datetime import datetime

class AbaLogs:
    def __init__(self, tab, log_manager):
        self.tab = tab
        self.log_manager = log_manager
        
        self.frame = ctk.CTkFrame(tab)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        titulo_frame = ctk.CTkFrame(self.frame)
        titulo_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(titulo_frame, text="📋 Logs do Sistema", font=("Arial", 18, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(titulo_frame, text="🗑️ Limpar", command=self.limpar_logs, width=100).pack(side="right", padx=5)
        ctk.CTkButton(titulo_frame, text="💾 Salvar", command=self.salvar_logs, width=100).pack(side="right", padx=5)
        
        self.texto_logs = ctk.CTkTextbox(self.frame, font=("Consolas", 10))
        self.texto_logs.pack(fill="both", expand=True)
        self.texto_logs.configure(fg_color="#0a0a0a", text_color="#00ff00", wrap="word")
        
        self.log_manager.set_callback(self.atualizar_logs)
        self.atualizar_logs()
    
    def atualizar_logs(self, *args):
        self.texto_logs.delete("1.0", "end")
        for linha in self.log_manager.get_ultimas(100):
            self.texto_logs.insert("end", linha)
        self.texto_logs.see("end")
    
    def limpar_logs(self):
        self.log_manager.limpar()
        self.texto_logs.delete("1.0", "end")
        self.texto_logs.insert("end", "[SISTEMA] Logs limpos!\n")
    
    def salvar_logs(self):
        from tkinter import filedialog
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt")],
            initialfile=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if arquivo:
            with open(arquivo, 'w', encoding='utf-8') as f:
                for linha in self.log_manager.get_logs():
                    f.write(linha)