# log_manager.py - VERSÃO FINAL COM LIMITES
import sys
import os
from datetime import datetime

class LogManager:
    def __init__(self):
        self.logs = []
        self.callback = None
        self.stdout_original = sys.stdout
        self.log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_logs.txt')
        self.contador = 0
        self.max_memoria = 1000  # Máximo de logs na memória
        self.max_arquivo_mb = 5  # Máximo do arquivo em MB
    
    def iniciar(self):
        sys.stdout = self
    
    def write(self, texto):
        if texto and texto.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            linha = f"[{timestamp}] {texto.rstrip()}\n"
            self.logs.append(linha)
            
            # Mantém só os últimos logs na memória
            if len(self.logs) > self.max_memoria:
                self.logs = self.logs[-500:]
            
            # Salva no arquivo
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(linha)
            except:
                pass
            
            self.stdout_original.write(texto)
            
            self.contador += 1
            
            # Verifica tamanho do arquivo a cada 100 logs
            if self.contador % 100 == 0:
                self._verificar_tamanho_arquivo()
            
            # Atualiza interface a cada 5 logs
            if self.callback and self.contador % 5 == 0:
                self.callback(None)
    
    def _verificar_tamanho_arquivo(self):
        """Rotaciona arquivo se maior que 5MB"""
        try:
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_arquivo_mb * 1024 * 1024:
                # Renomeia o arquivo antigo
                backup = self.log_file.replace('.txt', f'_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
                os.rename(self.log_file, backup)
                # Cria novo arquivo
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