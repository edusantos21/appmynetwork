# monitor.py - TCP ASYNCIO COM FALLBACK DE PORTAS (CORRIGIDO)
import asyncio
import threading
import time
import socket
from datetime import datetime


class Monitor:
    def __init__(self, telegram_manager=None, firebase_manager=None):
        self.telegram_manager = telegram_manager
        self.firebase_manager = firebase_manager
        self.monitorando = False
        self.equipamentos = []
        self.clientes = []
        self.configuracoes = {}
        self.ultima_verificacao = None
        self.thread = None
        self.db = None
        
        self.estado_dispositivos = {}
        self.estados_anteriores = {}
        self.falhas = {}
        self.ultima_latencia = {}
        
        self.max_falhas = 3
        self.intervalo = 5
        self.timeout_ping = 0.15
        
        self.telegram_configurado = False
        self.ultima_verificacao_telegram = 0
        
        self.loop_asyncio = None
    
    def _get_db(self):
        if self.db is None:
            from database import Database
            self.db = Database()
        return self.db
    
    def atualizar_configuracoes(self, equipamentos, configuracoes, clientes=None):
        self.equipamentos = equipamentos or []
        self.configuracoes = configuracoes or {}
        if clientes is not None:
            self.clientes = clientes or []
        
        self.max_falhas = int(self.configuracoes.get("quantidade_pings", 3))
        self.intervalo = int(self.configuracoes.get("intervalo_segundos", 5))
        self.timeout_ping = int(self.configuracoes.get("timeout_ms", 150)) / 1000
        
        # Remove IPs que não estão mais na lista
        ips_atuais = set()
        for e in self.equipamentos:
            ip = e.get("ip", "")
            if ip:
                ips_atuais.add(ip)
        for c in self.clientes:
            ip = c.get("ip", "")
            if ip:
                ips_atuais.add(ip)
        
        for ip in list(self.estado_dispositivos.keys()):
            if ip not in ips_atuais:
                del self.estado_dispositivos[ip]
                self.falhas.pop(ip, None)
                self.ultima_latencia.pop(ip, None)
                self.estados_anteriores.pop(ip, None)
        
        print(f"Monitor atualizado: {len(self.equipamentos)} equipamentos, {len(self.clientes)} clientes | timeout: {self.timeout_ping}s")
    
    def iniciar(self):
        if self.thread and self.thread.is_alive():
            return
        self.monitorando = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("Monitoramento iniciado")
    
    def parar(self):
        self.monitorando = False
        if self.loop_asyncio:
            self.loop_asyncio.call_soon_threadsafe(self.loop_asyncio.stop)
        print("Monitoramento parado")
    
    async def _ping_tcp_async(self, ip, porta_configurada=80):
        portas_para_tentar = []
        if porta_configurada not in portas_para_tentar:
            portas_para_tentar.append(porta_configurada)
        if 443 not in portas_para_tentar:
            portas_para_tentar.append(443)
        if 80 not in portas_para_tentar:
            portas_para_tentar.append(80)
        portas_para_tentar = list(dict.fromkeys(portas_para_tentar))
        
        for porta in portas_para_tentar:
            try:
                inicio = time.perf_counter()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setblocking(False)
                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().sock_connect(sock, (ip, porta)),
                        timeout=self.timeout_ping
                    )
                    tempo = (time.perf_counter() - inicio) * 1000
                    sock.close()
                    latencia_real = round(tempo / 2, 1)
                    return ip, True, latencia_real, porta
                except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                    sock.close()
                    continue
            except Exception:
                continue
        return ip, False, 0, porta_configurada
    
    async def _monitorar_todos_async(self, ips):
        if not ips:
            return
        ips_unicos = list(dict.fromkeys(ips))
        tasks = []
        for ip in ips_unicos:
            porta = 80
            for eq in self.equipamentos:
                if eq.get("ip") == ip and eq.get("porta"):
                    try:
                        porta = int(eq.get("porta"))
                    except (ValueError, TypeError):
                        porta = 80
                    break
            tasks.append(self._ping_tcp_async(ip, porta))
        
        resultados = await asyncio.gather(*tasks)
        
        for ip, respondeu, latencia, porta_usada in resultados:
            if ip not in self.falhas:
                self.falhas[ip] = 0
            if respondeu:
                self.falhas[ip] = 0
                self.ultima_latencia[ip] = latencia
            else:
                self.falhas[ip] = min(self.falhas[ip] + 1, self.max_falhas)
            online = self.falhas[ip] < self.max_falhas
            latencia_mostrar = latencia if respondeu else self.ultima_latencia.get(ip, 0)
            self.estado_dispositivos[ip] = {
                "online": online,
                "latencia": latencia_mostrar,
                "falhas": self.falhas[ip],
                "porta_usada": porta_usada if respondeu else None
            }
            chave = f"{ip}"
            estado_anterior = self.estados_anteriores.get(chave)
            novo_estado = "ONLINE" if online else "OFFLINE"
            if estado_anterior and estado_anterior != novo_estado:
                self._enviar_alerta(ip, novo_estado)
            self.estados_anteriores[chave] = novo_estado
    
    def _enviar_alerta(self, ip, novo_status):
        if not self.telegram_manager:
            return
        agora = time.time()
        if agora - self.ultima_verificacao_telegram > 30:
            self.telegram_configurado = self.telegram_manager.esta_configurado()
            self.ultima_verificacao_telegram = agora
        if not self.telegram_configurado:
            return
        def enviar():
            try:
                hora_atual = datetime.now().strftime("%H:%M:%S")
                nome = ip
                localidade = "-"
                for e in self.equipamentos:
                    if e.get("ip") == ip:
                        nome = e.get("nome", ip)
                        localidade = e.get("localidade", "-")
                        break
                for c in self.clientes:
                    if c.get("ip") == ip:
                        nome = c.get("nome", ip)
                        break
                if novo_status == "OFFLINE":
                    msg = f"🔴 OFFLINE - {nome} | {localidade} | {ip}\n🕐 {hora_atual}"
                else:
                    latencia = self.estado_dispositivos.get(ip, {}).get("latencia", 0)
                    msg = f"🟢 ONLINE - {nome} | {localidade} | {ip}\n🕐 {hora_atual} | 📶 {latencia}ms"
                self.telegram_manager.enviar(msg)
            except Exception as e:
                print(f"Erro ao enviar alerta: {e}")
        threading.Thread(target=enviar, daemon=True).start()
    
    def _loop(self):
        print("Loop de monitoramento iniciado")
        self.loop_asyncio = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop_asyncio)
        while self.monitorando:
            try:
                inicio = time.time()
                todos_ips = set()
                for e in self.equipamentos:
                    ip = e.get("ip", "")
                    if ip:
                        todos_ips.add(ip)
                        if ip not in self.falhas:
                            self.falhas[ip] = self.max_falhas
                for c in self.clientes:
                    ip = c.get("ip", "")
                    if ip:
                        todos_ips.add(ip)
                        if ip not in self.falhas:
                            self.falhas[ip] = self.max_falhas
                if todos_ips:
                    self.loop_asyncio.run_until_complete(
                        self._monitorar_todos_async(list(todos_ips))
                    )
                self.ultima_verificacao = datetime.now()
                tempo_execucao = time.time() - inicio
                online = sum(1 for e in self.estado_dispositivos.values() if e.get("online"))
                offline = len(self.estado_dispositivos) - online
                print(f"[MONITOR] {len(todos_ips)} IPs em {tempo_execucao:.2f}s | 🟢 {online} | 🔴 {offline}")
                tempo_espera = max(0, self.intervalo - tempo_execucao)
                time.sleep(tempo_espera)
            except Exception as e:
                print(f"Erro no loop: {e}")
                time.sleep(5)
    
    def get_estado(self):
        resultado = []
        for eq in self.equipamentos:
            ip = eq.get("ip", "")
            estado = self.estado_dispositivos.get(ip, {})
            dados_snmp = eq.get('dados_snmp', {})
            if not isinstance(dados_snmp, dict):
                dados_snmp = {}
            resultado.append({
                "id": eq.get("id"),
                "nome": eq.get("nome", ""),
                "ip": ip,
                "tipo": eq.get("tipo", "equipamento"),
                "status": "ONLINE" if estado.get("online", False) else "OFFLINE",
                "latencia": estado.get("latencia", 0),
                "localidade": eq.get("localidade", ""),
                "modo_operacao": eq.get("modo_operacao", "cliente"),
                "p2p_tipo": eq.get("p2p_tipo", ""),
                "p2p_par": eq.get("p2p_par", ""),
                "clientes": dados_snmp.get("clientes", 0),
                "ssid": dados_snmp.get("ssid", ""),
                "mac": dados_snmp.get("mac", ""),
                "porta": eq.get("porta", "80"),
                "ssh_enabled": eq.get("ssh_enabled", False),
                "falhas": estado.get("falhas", 0)
            })
        return resultado
    
    def get_servidores_estado(self):
        resultado = []
        for eq in self.equipamentos:
            if eq.get('tipo') != 'servidor':
                continue
            ip = eq.get("ip", "")
            estado = self.estado_dispositivos.get(ip, {})
            resultado.append({
                "id": eq.get("id"),
                "nome": eq.get("nome", ""),
                "ip": ip,
                "status": "ONLINE" if estado.get("online", False) else "OFFLINE",
                "latencia": estado.get("latencia", 0),
                "localidade": eq.get("localidade", ""),
                "porta": eq.get("porta", "80"),
                "falhas": estado.get("falhas", 0)
            })
        return resultado
    
    def get_energias_estado(self):
        resultado = []
        for eq in self.equipamentos:
            if eq.get('tipo') != 'energia':
                continue
            ip = eq.get("ip", "")
            estado = self.estado_dispositivos.get(ip, {})
            resultado.append({
                "id": eq.get("id"),
                "nome": eq.get("nome", ""),
                "ip": ip,
                "status": "ONLINE" if estado.get("online", False) else "OFFLINE",
                "latencia": estado.get("latencia", 0),
                "localidade": eq.get("localidade", ""),
                "porta": eq.get("porta", "80"),
                "falhas": estado.get("falhas", 0)
            })
        return resultado
    
    def get_servicos_estado(self):
        resultado = []
        for eq in self.equipamentos:
            if eq.get('tipo') != 'servico':
                continue
            ip = eq.get("ip", "")
            estado = self.estado_dispositivos.get(ip, {})
            resultado.append({
                "id": eq.get("id"),
                "nome": eq.get("nome", ""),
                "ip": ip,
                "status": "ONLINE" if estado.get("online", False) else "OFFLINE",
                "latencia": estado.get("latencia", 0),
                "localidade": eq.get("localidade", ""),
                "porta": eq.get("porta", "80"),
                "falhas": estado.get("falhas", 0)
            })
        return resultado
    
    def get_clientes_estado(self):
        resultado = []
        for cli in self.clientes:
            ip = cli.get("ip", "")
            estado = self.estado_dispositivos.get(ip, {})
            resultado.append({
                "id": cli.get("id"),
                "nome": cli.get("nome", ""),
                "ip": ip,
                "status": "ONLINE" if estado.get("online", False) else "OFFLINE",
                "latencia": estado.get("latencia", 0),
                "falhas": estado.get("falhas", 0)
            })
        return resultado
    
    def get_resumo(self):
        online = sum(1 for e in self.estado_dispositivos.values() if e.get("online"))
        offline = len(self.estado_dispositivos) - online
        return {
            "total": len(self.equipamentos) + len(self.clientes),
            "online": online,
            "offline": offline,
            "ultima_verificacao": self.ultima_verificacao.isoformat() if self.ultima_verificacao else None
        }
    
    def get_ultima_verificacao(self):
        return self.ultima_verificacao
    
    def testar_ping_unico(self, ip):
        async def testar():
            return await self._ping_tcp_async(ip, 80)
        _, respondeu, latencia, _ = asyncio.run(testar())
        if respondeu:
            return latencia, "ONLINE"
        return 0, "OFFLINE"
    
    def forcar_verificacao(self):
        todos_ips = set()
        for e in self.equipamentos:
            ip = e.get("ip", "")
            if ip: todos_ips.add(ip)
        for c in self.clientes:
            ip = c.get("ip", "")
            if ip: todos_ips.add(ip)
        if todos_ips:
            self.loop_asyncio.run_until_complete(
                self._monitorar_todos_async(list(todos_ips))
            )
        self.ultima_verificacao = datetime.now()
        return self.get_resumo()