# ssh_manager.py - COMPLETO FINAL (COM MIMOSA)
import asyncio
import asyncssh
import threading
import time
import re
from datetime import datetime
from asyncssh.kex import get_kex_algs
from asyncssh.encryption import get_encryption_algs
from asyncssh.public_key import get_public_key_algs

_KEX_ALGS_COMPATIVEIS = [a.decode() if isinstance(a, bytes) else a for a in get_kex_algs()]
_ENCRYPTION_ALGS_COMPATIVEIS = [a.decode() if isinstance(a, bytes) else a for a in get_encryption_algs()]
_HOST_KEY_ALGS_COMPATIVEIS = [a.decode() if isinstance(a, bytes) else a for a in get_public_key_algs()]

class SSHManager:
    def __init__(self, config):
        self.config = config
        self.monitorando = False
        self.thread = None
        self.erros_consecutivos = {}
        self.ultimo_erro = {}
        self.ip_invalidos = set()
        
        self.dados_ssh_cache = {}
        self.fila_salvamento = {}
        self.ultimo_salvamento = 0
        self.lock_cache = threading.Lock()
        self.loop_asyncio = None
        self.semaforo = None
        self.max_conexoes_simultaneas = 10
        
        self.callback_atualizar = None
    
    def set_callback_atualizar(self, callback):
        self.callback_atualizar = callback
    
    def iniciar(self):
        if self.thread and self.thread.is_alive():
            print("⚠️ SSH Manager já está rodando")
            return
        self.monitorando = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("🔌 SSH Manager iniciado - Coleta assíncrona ativa")
    
    def parar(self):
        self.monitorando = False
        self._salvar_em_lote()
        print("🔌 SSH Manager parado")
    
    def _validar_ip(self, ip):
        if not ip: return False
        if ip in self.ip_invalidos: return False
        partes = ip.split('.')
        if len(partes) != 4: self.ip_invalidos.add(ip); return False
        for parte in partes:
            try:
                num = int(parte)
                if num < 0 or num > 255: self.ip_invalidos.add(ip); return False
            except ValueError: self.ip_invalidos.add(ip); return False
        return True
    
    def _extrair_valor_mikrotik(self, texto, chave):
        match = re.search(rf'{chave}=("[^"]*"|\S+)', texto, re.IGNORECASE)
        return match.group(1).strip('"') if match else None
    
    async def _coletar_ubiquiti(self, conn, nome):
        dados = {}
        try:
            cmd_ssid = conn.run("cat /tmp/system.cfg 2>/dev/null | grep wireless.1.ssid | head -1", check=False)
            cmd_mac = conn.run("cat /sys/class/net/eth0/address 2>/dev/null || ifconfig eth0 2>/dev/null | grep HWaddr | awk '{print $5}' || ifconfig ath0 2>/dev/null | grep HWaddr | awk '{print $5}'", check=False)
            cmd_clientes = conn.run("wlanconfig ath0 list sta 2>/dev/null | tail -n +2 | wc -l", check=False)
            resultados = await asyncio.gather(cmd_ssid, cmd_mac, cmd_clientes, return_exceptions=True)
            
            if resultados[0] and not isinstance(resultados[0], Exception):
                saida = resultados[0].stdout.strip()
                match = re.search(r'wireless\.1\.ssid=(.+)', saida)
                if match: dados["ssid"] = match.group(1).strip(); print(f"📡 SSH {nome}: SSID = {dados['ssid']}")
            
            if resultados[1] and not isinstance(resultados[1], Exception):
                saida = resultados[1].stdout.strip().upper()
                match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', saida)
                if match: dados["mac"] = match.group(0); print(f"📡 SSH {nome}: MAC = {dados['mac']}")
            
            if resultados[2] and not isinstance(resultados[2], Exception):
                saida = resultados[2].stdout.strip()
                dados["clientes"] = int(saida) if saida and saida.isdigit() else 0
                print(f"📡 SSH {nome}: Clientes = {dados['clientes']}")
        except Exception: pass
        return dados
    
    def _coletar_bullet_sync(self, equipamento):
        """Coleta dados do Bullet M5/XS5 usando PARAMIKO (síncrono)."""
        import paramiko as pm
        nome = equipamento.get("nome", "desconhecido")
        ip = equipamento.get("ip", "")
        usuario = equipamento.get("ssh_usuario", "ubnt")
        senha = equipamento.get("ssh_senha", "")
        porta = equipamento.get("ssh_porta", 22)
        dados = {}
        
        try:
            ssh = pm.SSHClient()
            ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
            ssh.connect(ip, port=porta, username=usuario, password=senha, timeout=5,
                       allow_agent=False, look_for_keys=False)
            
            stdin, stdout, stderr = ssh.exec_command("iwconfig 2>/dev/null | grep ESSID")
            saida = stdout.read().decode().strip()
            match = re.search(r'ESSID:"([^"]+)"', saida)
            if match: dados["ssid"] = match.group(1).strip(); print(f"📡 SSH {nome}: SSID = {dados['ssid']}")
            
            stdin, stdout, stderr = ssh.exec_command("ifconfig ath0 2>/dev/null")
            saida = stdout.read().decode().strip()
            match = re.search(r'HWaddr\s+([0-9A-Fa-f:]+)', saida)
            if match: dados["mac"] = match.group(1).upper(); print(f"📡 SSH {nome}: MAC = {dados['mac']}")
            
            stdin, stdout, stderr = ssh.exec_command("wlanconfig ath0 list sta 2>/dev/null")
            saida = stdout.read().decode().strip()
            clientes = len(re.findall(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', saida))
            dados["clientes"] = clientes
            print(f"📡 SSH {nome}: Clientes = {dados['clientes']}")
            
            ssh.close()
        except Exception as e:
            print(f"❌ SSH {nome} ({ip}): falha Paramiko - {e}")
        
        return dados
    
    async def _coletar_mikrotik(self, conn, nome):
        dados = {}
        try:
            cmd_wireless = conn.run("/interface wireless print detail", check=False)
            cmd_registration = conn.run("/interface wireless registration-table print", check=False)
            resultados = await asyncio.gather(cmd_wireless, cmd_registration, return_exceptions=True)
            
            if resultados[0] and not isinstance(resultados[0], Exception):
                saida = resultados[0].stdout.strip()
                bloco = saida.split('\n\n')[0] if '\n\n' in saida else saida
                dados["ssid"] = self._extrair_valor_mikrotik(bloco, 'ssid') or 'N/A'
                dados["mac"] = (self._extrair_valor_mikrotik(bloco, 'mac-address') or '').upper()
                print(f"📡 SSH {nome}: SSID = {dados['ssid']}, MAC = {dados['mac']}")
            
            if resultados[1] and not isinstance(resultados[1], Exception):
                saida = resultados[1].stdout.strip()
                clientes = len(re.findall(r'^\s*\d+\s+\w+', saida, re.MULTILINE))
                dados["clientes"] = clientes
                print(f"📡 SSH {nome}: Clientes = {dados['clientes']}")
            else: dados["clientes"] = 0
        except Exception: pass
        return dados
    
    async def _conectar_e_coletar(self, equipamento, ip, usuario, senha, porta, firmware, nome):
        dados = {}
        
        # Mimosa não tem SSH - apenas retorna vazio
        if firmware == "mimosa":
            return dados
        
        # Bullet usa Paramiko (via executor)
        if firmware == "bullet":
            loop = asyncio.get_event_loop()
            dados = await loop.run_in_executor(None, self._coletar_bullet_sync, equipamento)
        else:
            async with asyncssh.connect(
                ip, port=porta, username=usuario, password=senha,
                known_hosts=None, connect_timeout=3,
                kex_algs=_KEX_ALGS_COMPATIVEIS,
                encryption_algs=_ENCRYPTION_ALGS_COMPATIVEIS,
                server_host_key_algs=_HOST_KEY_ALGS_COMPATIVEIS,
            ) as conn:
                if firmware == "mikrotik":
                    dados = await self._coletar_mikrotik(conn, nome)
                else:
                    dados = await self._coletar_ubiquiti(conn, nome)
        
        dados["ultima_coleta"] = datetime.now().isoformat()
        
        if dados and (dados.get('mac') or dados.get('ssid') or dados.get('clientes', 0) > 0):
            with self.lock_cache:
                cache_antigo = self.dados_ssh_cache.get(ip, {})
                if (dados.get('mac') != cache_antigo.get('mac') or
                    dados.get('ssid') != cache_antigo.get('ssid') or
                    dados.get('clientes') != cache_antigo.get('clientes')):
                    self.dados_ssh_cache[ip] = dados
                    equipamento["dados_snmp"] = dados
                    self.fila_salvamento[equipamento.get('id', ip)] = equipamento
        return dados
    
    async def _coletar_async(self, equipamento):
        nome = equipamento.get("nome", "desconhecido")
        ip = equipamento.get("ip", "")
        firmware = equipamento.get("firmware", "ubiquiti")
        
        if not self._validar_ip(ip): return None
        usuario = equipamento.get("ssh_usuario", "ubnt")
        senha = equipamento.get("ssh_senha", "")
        porta = equipamento.get("ssh_porta", 22)
        if not equipamento.get("ssh_enabled", True) or not senha: return None
        
        erros_transitorios = (asyncssh.ConnectionLost, asyncio.TimeoutError, TimeoutError, ConnectionResetError)
        async with self.semaforo:
            for tentativa in (1, 2):
                try:
                    return await self._conectar_e_coletar(equipamento, ip, usuario, senha, porta, firmware, nome)
                except erros_transitorios as e:
                    if tentativa == 1:
                        print(f"🔄 SSH {nome} ({ip}): {type(e).__name__}, tentando de novo...")
                        await asyncio.sleep(1); continue
                    print(f"❌ SSH {nome} ({ip}): {type(e).__name__}: {e}"); return None
                except Exception as e:
                    print(f"❌ SSH {nome} ({ip}): {type(e).__name__}: {e}"); return None
    
    async def _monitorar_todos_async(self, equipamentos):
        tasks = [self._coletar_async(eq) for eq in equipamentos]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _salvar_em_lote(self):
        with self.lock_cache:
            if not self.fila_salvamento: return
            try:
                from database import Database
                db = Database()
                total = len(self.fila_salvamento)
                for eq in self.fila_salvamento.values(): db.salvar_equipamento(eq)
                print(f"💾 SSH: {total} equipamentos salvos em lote")
                self.fila_salvamento.clear()
                self.ultimo_salvamento = time.time()
                if self.callback_atualizar:
                    try: self.callback_atualizar()
                    except Exception as e: print(f"⚠️ Erro ao chamar callback: {e}")
            except Exception as e: print(f"❌ SSH: Erro ao salvar em lote: {e}")
    
    def get_dados_cache(self, ip): return self.dados_ssh_cache.get(ip, {})
    def get_todos_dados_cache(self): return dict(self.dados_ssh_cache)
    
    def testar(self, ip, usuario="ubnt", senha="ubnt", porta=22):
        resultados = []
        if not self._validar_ip(ip): resultados.append(f"❌ SSH: IP inválido '{ip}'"); return resultados
        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=porta, username=usuario, password=senha, timeout=5)
            resultados.append("✅ SSH: Conectado com sucesso!"); ssh.close()
        except Exception as e: resultados.append(f"❌ SSH: {e}")
        return resultados
    
    def _loop(self):
        self.loop_asyncio = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop_asyncio)
        self.semaforo = asyncio.Semaphore(self.max_conexoes_simultaneas)
        intervalo = self.config.get_configuracoes().get("snmp_intervalo", 30)
        
        while self.monitorando:
            try:
                equipamentos_ssh = [
                    eq for eq in self.config.get_equipamentos()
                    if eq.get("ssh_enabled", True) and eq.get("ip") not in self.ip_invalidos and eq.get("ssh_senha")
                ]
                if equipamentos_ssh:
                    inicio = time.time()
                    self.loop_asyncio.run_until_complete(self._monitorar_todos_async(equipamentos_ssh))
                    print(f"📡 SSH: {len(equipamentos_ssh)} equipamentos em {time.time() - inicio:.2f}s")
                
                if time.time() - self.ultimo_salvamento >= 30: self._salvar_em_lote()
                time.sleep(intervalo)
            except Exception as e: print(f"❌ Erro no loop SSH: {e}"); time.sleep(5)