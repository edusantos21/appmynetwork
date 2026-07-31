# log_manager.py - VERSÃO FINAL COM LIMITES (COMPATÍVEL COM EXE)
import sys
import os
from datetime import datetime

class LogManager:
    def __init__(self):
        self.logs = []
        self.callback = None
        self.stdout_original = None
        self.log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_logs.txt')
        self.contador = 0
        self.max_memoria = 1000
        self.max_arquivo_mb = 5
    
    def iniciar(self):
        # Guarda o stdout original (compatível com .exe)
        self.stdout_original = sys.stdout or sys.__stdout__
        sys.stdout = self
    
    def write(self, texto):
        if texto and texto.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            linha = f"[{timestamp}] {texto.rstrip()}\n"
            self.logs.append(linha)
            
            if len(self.logs) > self.max_memoria:
                self.logs = self.logs[-500:]
            
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(linha)
            except:
                pass
            
            # Escreve no terminal original (se existir)
            if self.stdout_original:
                try:
                    self.stdout_original.write(texto)
                except:
                    pass
            
            self.contador += 1
            
            if self.contador % 100 == 0:
                self._verificar_tamanho_arquivo()
            
            if self.callback and self.contador % 5 == 0:
                self.callback(None)
    
    def _verificar_tamanho_arquivo(self):
        try:
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_arquivo_mb * 1024 * 1024:
                backup = self.log_file.replace('.txt', f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
                os.rename(self.log_file, backup)
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Arquivo rotacionado (5MB atingido). Backup: {os.path.basename(backup)}\n")
        except:
            pass
    
    def flush(self):
        pass
    
    def get_logs(self):
        return self.logs
    
    def get_ultimas(self, n=100):
        return self.logs[-n:] if len(self.logs) > n else self.logs
    
    def limpar(self):
        self.logs.clear()
        self.contador = 0
    
    def set_callback(self, callback):
        self.callback = callback