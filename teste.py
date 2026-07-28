# teste_tcp.py - TCP Ping dividido por 3 (CORRIGIDO)
import customtkinter as ctk
from tkinter import ttk
import threading
import time
import subprocess
import re
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
estado_global = {}

@app.route('/')
def home():
    return jsonify({"status": "online"})

@app.route('/equipamentos')
def api_equipamentos():
    resultado = []
    for ip, dados in estado_global.items():
        resultado.append({
            "ip": ip,
            "status": "🟢 ONLINE" if dados["online"] else "🔴 OFFLINE",
            "latencia": dados.get("latencia", 0),
            "falhas": dados.get("falhas", 0)
        })
    return jsonify(resultado)


class TesteCompleto:
    
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        self.janela = ctk.CTk()
        self.janela.title("Teste TCP Ping - 2 Blocos /24")
        self.janela.geometry("700x850")
        
        self.testando = False
        self.executor = None
        self.falhas = {}
        self.itens = {}
        self.ultima_latencia = {}
        self.url_publica = None
        self.cloudflared_path = r"C:\Users\Edu\Desktop\My\MyNetworkBack\cloudflared.exe"
        
        self.criar_interface()
        self.iniciar_servidor()
        self.janela.mainloop()
    
    def criar_interface(self):
        frame_config = ctk.CTkFrame(self.janela)
        frame_config.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(frame_config, text="Threads:").pack(side="left", padx=5)
        self.combo_threads = ctk.CTkComboBox(frame_config, values=["50","100","150","200"], width=60)
        self.combo_threads.pack(side="left", padx=5)
        self.combo_threads.set("100")
        
        ctk.CTkLabel(frame_config, text="Falhas:").pack(side="left", padx=5)
        self.combo_falhas = ctk.CTkComboBox(frame_config, values=["1","2","3","5"], width=50)
        self.combo_falhas.pack(side="left", padx=5)
        self.combo_falhas.set("3")
        
        frame_blocos = ctk.CTkFrame(self.janela)
        frame_blocos.pack(fill="x", padx=15, pady=5)
        
        self.chk_bloco1 = ctk.CTkCheckBox(frame_blocos, text="Bloco 1:", checkbox_width=18, checkbox_height=18)
        self.chk_bloco1.pack(side="left", padx=(10,5))
        self.chk_bloco1.select()
        self.entry_bloco1 = ctk.CTkEntry(frame_blocos, width=130, placeholder_text="192.168.189")
        self.entry_bloco1.pack(side="left", padx=5)
        self.entry_bloco1.insert(0, "192.168.189")
        ctk.CTkLabel(frame_blocos, text=".1 - .254").pack(side="left", padx=2)
        
        self.chk_bloco2 = ctk.CTkCheckBox(frame_blocos, text="Bloco 2:", checkbox_width=18, checkbox_height=18)
        self.chk_bloco2.pack(side="left", padx=(20,5))
        self.chk_bloco2.select()
        self.entry_bloco2 = ctk.CTkEntry(frame_blocos, width=130, placeholder_text="192.168.190")
        self.entry_bloco2.pack(side="left", padx=5)
        self.entry_bloco2.insert(0, "192.168.190")
        ctk.CTkLabel(frame_blocos, text=".1 - .254").pack(side="left", padx=2)
        
        frame_botoes = ctk.CTkFrame(self.janela)
        frame_botoes.pack(fill="x", padx=15, pady=5)
        
        self.btn_iniciar = ctk.CTkButton(frame_botoes, text="▶ INICIAR", command=self.iniciar, fg_color="green")
        self.btn_iniciar.pack(side="left", padx=5)
        self.btn_parar = ctk.CTkButton(frame_botoes, text="⏹ PARAR", command=self.parar, fg_color="red", state="disabled")
        self.btn_parar.pack(side="left", padx=5)
        self.lbl_total = ctk.CTkLabel(frame_botoes, text="Total: 0 IPs", font=("Arial", 12))
        self.lbl_total.pack(side="left", padx=20)
        self.lbl_tempo = ctk.CTkLabel(frame_botoes, text="0.0s", font=("Arial", 14, "bold"))
        self.lbl_tempo.pack(side="right", padx=10)
        
        self.lbl_url = ctk.CTkLabel(self.janela, text="🔗 Aguardando túnel...", font=("Arial", 11), text_color="cyan")
        self.lbl_url.pack(pady=5)
        
        self.tree = ttk.Treeview(self.janela, columns=("ip", "status", "ms", "falhas"), show="headings", height=20)
        self.tree.heading("ip", text="IP")
        self.tree.heading("status", text="Status")
        self.tree.heading("ms", text="Latência")
        self.tree.heading("falhas", text="Falhas")
        self.tree.column("ip", width=150, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("ms", width=80, anchor="center")
        self.tree.column("falhas", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.lbl_resumo = ctk.CTkLabel(self.janela, text="🟢 0 | 🔴 0", font=("Arial", 14, "bold"))
        self.lbl_resumo.pack(pady=5)
        btn_copiar = ctk.CTkButton(self.janela, text="📋 Copiar URL", command=self.copiar_url, width=120)
        btn_copiar.pack(pady=5)
    
    def iniciar_servidor(self):
        def rodar_flask():
            app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
        threading.Thread(target=rodar_flask, daemon=True).start()
        threading.Thread(target=self.iniciar_tunel, daemon=True).start()
    
    def iniciar_tunel(self):
        time.sleep(2)
        if not os.path.exists(self.cloudflared_path):
            self.lbl_url.configure(text="❌ cloudflared.exe não encontrado!"); return
        try:
            processo = subprocess.Popen(
                [self.cloudflared_path, 'tunnel', '--url', 'http://localhost:8080'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for linha in processo.stdout:
                if 'trycloudflare.com' in linha:
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', linha)
                    if match:
                        self.url_publica = match.group(0)
                        self.lbl_url.configure(text=f"🔗 {self.url_publica}/equipamentos")
        except: pass
    
    def testar_ping(self, ip):
        try:
            inicio = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex((ip, 80))
            tempo = (time.perf_counter() - inicio) * 1000
            sock.close()
            
            if result == 0:
                latencia = round(tempo / 3, 1)
                return ip, True, latencia
            return ip, False, 0
        except:
            return ip, False, 0
    
    def iniciar(self):
        self.threads = int(self.combo_threads.get())
        self.max_falhas = int(self.combo_falhas.get())
        self.tree.delete(*self.tree.get_children())
        self.itens = {}
        self.falhas = {}
        self.ultima_latencia = {}
        global estado_global; estado_global = {}
        
        if self.chk_bloco1.get():
            bloco1 = self.entry_bloco1.get().strip()
            for i in range(1, 255):
                ip = f"{bloco1}.{i}"
                item_id = self.tree.insert("", "end", values=(ip, "🔴 OFFLINE", "-", str(self.max_falhas)))
                self.itens[ip] = item_id
                self.falhas[ip] = self.max_falhas
        
        if self.chk_bloco2.get():
            bloco2 = self.entry_bloco2.get().strip()
            for i in range(1, 255):
                ip = f"{bloco2}.{i}"
                item_id = self.tree.insert("", "end", values=(ip, "🔴 OFFLINE", "-", str(self.max_falhas)))
                self.itens[ip] = item_id
                self.falhas[ip] = self.max_falhas
        
        self.lbl_total.configure(text=f"Total: {len(self.itens)} IPs")
        self.testando = True
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.executor = ThreadPoolExecutor(max_workers=self.threads)
        threading.Thread(target=self.loop, daemon=True).start()
    
    def loop(self):
        ips = list(self.itens.keys())
        global estado_global
        ciclo = 0
        
        while self.testando:
            ciclo += 1
            inicio = time.time()
            resultados = {}
            futures = {self.executor.submit(self.testar_ping, ip): ip for ip in ips}
            
            for future in as_completed(futures):
                if not self.testando: return
                ip, respondeu, latencia = future.result()
                
                if respondeu:
                    self.falhas[ip] = 0
                    self.ultima_latencia[ip] = latencia
                else:
                    self.falhas[ip] = min(self.falhas[ip] + 1, self.max_falhas)
                
                online = self.falhas[ip] < self.max_falhas
                latencia_mostrar = latencia if respondeu else self.ultima_latencia.get(ip, 0)
                
                resultados[ip] = (respondeu, latencia_mostrar, self.falhas[ip])
                estado_global[ip] = {
                    "online": online,
                    "latencia": latencia_mostrar,
                    "falhas": self.falhas[ip]
                }
            
            self.janela.after(0, self.atualizar_tabela, resultados)
            tempo = time.time() - inicio
            online = sum(1 for f in self.falhas.values() if f < self.max_falhas)
            offline = sum(1 for f in self.falhas.values() if f >= self.max_falhas)
            self.lbl_tempo.configure(text=f"{tempo:.2f}s")
            self.lbl_resumo.configure(text=f"🟢 {online} | 🔴 {offline} | ⏱️ {tempo:.2f}s | Ciclo #{ciclo}")
    
    def atualizar_tabela(self, resultados):
        for ip, (respondeu, latencia, falhas) in resultados.items():
            if ip not in self.itens: continue
            
            if falhas >= self.max_falhas:
                self.tree.item(self.itens[ip], values=(ip, "🔴 OFFLINE", "-", str(falhas)))
            else:
                if latencia > 0:
                    self.tree.item(self.itens[ip], values=(ip, "🟢 ONLINE", f"{latencia}ms", str(falhas)))
                else:
                    self.tree.item(self.itens[ip], values=(ip, "🟢 ONLINE", "-", str(falhas)))
    
    def copiar_url(self):
        if self.url_publica:
            self.janela.clipboard_clear()
            self.janela.clipboard_append(f"{self.url_publica}/equipamentos")
            self.lbl_url.configure(text="✅ URL COPIADA!")
    
    def parar(self):
        self.testando = False
        if self.executor: self.executor.shutdown(wait=False)
        self.btn_parar.configure(state="disabled")
        self.btn_iniciar.configure(state="normal")


if __name__ == "__main__":
    TesteCompleto()