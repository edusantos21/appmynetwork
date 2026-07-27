import threading
import time
import paramiko
import re
from datetime import datetime

class SSHManager:
    def __init__(self, config):
        self.config = config
        self.monitorando = False
        self.thread = None
        self.erros_consecutivos = {}
        self.ultimo_erro = {}
        self.ip_invalidos = set()
    
    def iniciar(self):
        if self.thread and self.thread.is_alive():
            print("⚠️ SSH Manager já está rodando")
            return
        
        self.monitorando = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("🔌 SSH Manager iniciado - Coleta automática ativa")
    
    def parar(self):
        self.monitorando = False
        print("🔌 SSH Manager parado")
    
    def _validar_ip(self, ip):
        if not ip:
            return False
        if ip in self.ip_invalidos:
            return False
        partes = ip.split('.')
        if len(partes) != 4:
            self.ip_invalidos.add(ip)
            return False
        for parte in partes:
            try:
                num = int(parte)
                if num < 0 or num > 255:
                    self.ip_invalidos.add(ip)
                    return False
            except ValueError:
                self.ip_invalidos.add(ip)
                return False
        return True
    
    def _executar_comando(self, ip, usuario, senha, porta, comando):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=porta, username=usuario, password=senha, timeout=5)
            stdin, stdout, stderr = ssh.exec_command(comando)
            saida = stdout.read().decode('utf-8').strip()
            ssh.close()
            return saida
        except Exception as e:
            return None
    
    def coletar(self, equipamento):
        nome = equipamento.get("nome", "desconhecido")
        ip = equipamento.get("ip", "")
        
        if not self._validar_ip(ip):
            if ip not in self.ip_invalidos:
                print(f"❌ SSH {nome}: IP inválido '{ip}' - ignorado")
                self.ip_invalidos.add(ip)
            return {}
        
        usuario = equipamento.get("ssh_usuario", "ubnt")
        senha = equipamento.get("ssh_senha", "")
        porta = equipamento.get("ssh_porta", 22)
        
        if not equipamento.get("ssh_enabled", True):
            return {}
        
        if not senha:
            chave = f"{nome}_{ip}"
            if chave not in self.erros_consecutivos:
                print(f"⚠️ SSH {nome}: Senha não configurada")
                self.erros_consecutivos[chave] = 1
            return {}
        
        dados = {}
        chave = f"{nome}_{ip}"
        
        # Coletar modelo
        saida = self._executar_comando(ip, usuario, senha, porta, "cat /etc/board.info 2>/dev/null | grep board.name")
        if saida:
            match = re.search(r'board.name=(.+)', saida)
            if match:
                dados["modelo"] = match.group(1).strip()
        
        # Coletar firmware
        saida = self._executar_comando(ip, usuario, senha, porta, "cat /etc/version 2>/dev/null")
        if saida:
            dados["firmware"] = saida.strip()
        
        # Coletar SSID
        saida = self._executar_comando(ip, usuario, senha, porta, "cat /tmp/system.cfg 2>/dev/null | grep wireless.1.ssid | head -1")
        if saida:
            match = re.search(r'wireless.1.ssid=(.+)', saida)
            if match:
                dados["ssid"] = match.group(1).strip()
                print(f"📡 SSH {nome}: SSID coletado = {dados['ssid']}")
        
        # Coletar MAC
        saida = self._executar_comando(ip, usuario, senha, porta, "cat /sys/class/net/eth0/address 2>/dev/null || ifconfig eth0 2>/dev/null | grep HWaddr | awk '{print $5}' || ifconfig ath0 2>/dev/null | grep HWaddr | awk '{print $5}'")
        if saida:
            match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', saida.upper())
            if match:
                dados["mac"] = match.group(0)
                print(f"📡 SSH {nome}: MAC coletado = {dados['mac']}")
        
        # Coletar número de clientes
        saida = self._executar_comando(ip, usuario, senha, porta, "wlanconfig ath0 list sta 2>/dev/null | tail -n +2 | wc -l")
        if saida and saida.isdigit():
            dados["clientes"] = int(saida)
            print(f"📡 SSH {nome}: Clientes coletados = {dados['clientes']}")
        else:
            dados["clientes"] = 0
        
        # Coletar lista de clientes
        saida = self._executar_comando(ip, usuario, senha, porta, "wlanconfig ath0 list sta 2>/dev/null | tail -n +2")
        if saida:
            clientes_lista = []
            linhas = saida.split('\n')
            for linha in linhas:
                partes = linha.split()
                if len(partes) >= 7:
                    clientes_lista.append({
                        "mac": partes[0],
                        "txrate": partes[3],
                        "rxrate": partes[4],
                        "rssi": partes[5]
                    })
            dados["clientes_lista"] = clientes_lista
        
        # Coletar uptime
        saida = self._executar_comando(ip, usuario, senha, porta, "uptime")
        if saida:
            match = re.search(r'up\s+(.+?)(?:,|$)', saida)
            if match:
                dados["uptime"] = match.group(1).strip()
        
        dados["ultima_coleta"] = datetime.now().isoformat()
        
        # 🔥 SÓ SALVAR SE TIVER DADOS VÁLIDOS (clientes > 0 OU SSID presente)
        if dados and (dados.get('clientes', 0) > 0 or dados.get('ssid')):
            equipamento["dados_snmp"] = dados
            
            try:
                from database import Database
                db = Database()
                db.salvar_equipamento(equipamento)
                print(f"✅ SSH {nome}: Dados salvos no banco (clientes={dados.get('clientes', 0)})")
            except Exception as e:
                print(f"❌ SSH {nome}: Erro ao salvar no banco: {e}")
            
            if chave in self.erros_consecutivos:
                del self.erros_consecutivos[chave]
        else:
            if dados:
                print(f"⚠️ SSH {nome}: Dados inválidos (clientes={dados.get('clientes', 0)}), NÃO salvou")
        
        return dados
    
    def testar(self, ip, usuario="ubnt", senha="ubnt", porta=22):
        resultados = []
        
        if not self._validar_ip(ip):
            resultados.append(f"❌ SSH: IP inválido '{ip}'")
            return resultados
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=porta, username=usuario, password=senha, timeout=5)
            resultados.append(f"✅ SSH: Conectado com sucesso!")
            
            stdin, stdout, stderr = ssh.exec_command("cat /etc/version")
            firmware = stdout.read().decode().strip()
            if firmware:
                resultados.append(f"✅ Firmware: {firmware}")
            
            stdin, stdout, stderr = ssh.exec_command("cat /etc/board.info | grep board.name")
            modelo = stdout.read().decode().strip()
            if modelo:
                match = re.search(r'board.name=(.+)', modelo)
                if match:
                    resultados.append(f"✅ Modelo: {match.group(1)}")
            
            stdin, stdout, stderr = ssh.exec_command("cat /sys/class/net/eth0/address 2>/dev/null || ifconfig eth0 | grep HWaddr | awk '{print $5}'")
            mac = stdout.read().decode().strip()
            if mac:
                resultados.append(f"✅ MAC: {mac}")
            
            stdin, stdout, stderr = ssh.exec_command("cat /tmp/system.cfg | grep wireless.1.ssid | head -1")
            ssid = stdout.read().decode().strip()
            if ssid:
                match = re.search(r'wireless.1.ssid=(.+)', ssid)
                if match:
                    resultados.append(f"✅ SSID: {match.group(1)}")
            
            stdin, stdout, stderr = ssh.exec_command("wlanconfig ath0 list sta 2>/dev/null | tail -n +2 | wc -l")
            clientes = stdout.read().decode().strip()
            if clientes and clientes.isdigit():
                resultados.append(f"✅ Clientes conectados: {clientes}")
            
            ssh.close()
            
        except paramiko.AuthenticationException:
            resultados.append("❌ SSH: Falha na autenticação (usuário/senha incorretos)")
        except Exception as e:
            resultados.append(f"❌ SSH: {e}")
        
        return resultados
    
    def _deve_logar_erro(self, chave, erro_tipo):
        agora = datetime.now().timestamp()
        
        if chave not in self.erros_consecutivos:
            self.erros_consecutivos[chave] = 1
            self.ultimo_erro[chave] = agora
            return True
        
        contador = self.erros_consecutivos[chave]
        ultimo = self.ultimo_erro.get(chave, 0)
        
        if contador >= 5 or (agora - ultimo) > 300:
            self.erros_consecutivos[chave] = 1
            self.ultimo_erro[chave] = agora
            return True
        
        self.erros_consecutivos[chave] = contador + 1
        return False
    
    def _loop(self):
        intervalo = self.config.get_configuracoes().get("snmp_intervalo", 30)
        
        while self.monitorando:
            try:
                for eq in self.config.get_equipamentos():
                    if not self.monitorando:
                        break
                    
                    if eq.get("ssh_enabled", True):
                        nome = eq.get("nome", "desconhecido")
                        ip = eq.get("ip", "")
                        
                        if ip in self.ip_invalidos:
                            continue
                        
                        try:
                            dados = self.coletar(eq)
                            if dados:
                                eq["dados_snmp"] = dados
                        except Exception as e:
                            chave = f"{nome}_{ip}"
                            if self._deve_logar_erro(chave, str(e)):
                                print(f"❌ SSH erro {ip}: {e}")
                        
                        time.sleep(0.5)
                
                time.sleep(intervalo)
                
            except Exception as e:
                print(f"❌ Erro no loop SSH: {e}")
                time.sleep(5)