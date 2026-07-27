import threading
import time
import zipfile
import os
import shutil
from datetime import datetime
import paramiko

class BackupManager:
    def __init__(self, config, ssh_manager, email_manager):
        self.config = config
        self.ssh_manager = ssh_manager
        self.email_manager = email_manager
        self.agendamento_ativo = False
        self.thread_agendamento = None
        self.backup_config = {
            "agendado": False,
            "intervalo": "24h",
            "hora": "00:00",
            "historico": []
        }
        self.historico = []
        self.proxima_execucao = None
        
        self.carregar_config()
        self.carregar_historico()
    
    def carregar_config(self):
        backup_config = self.config.get_backup_config()
        if backup_config:
            self.backup_config.update(backup_config)
    
    def salvar_config(self):
        self.config.set_backup_config(self.backup_config)
    
    def coletar_configuracoes_ssh(self):
        resultados = []
        equipamentos = self.config.get_equipamentos()
        
        for eq in equipamentos:
            if not eq.get("ssh_enabled", True):
                continue
                
            ip = eq.get("ip", "")
            usuario = eq.get("ssh_usuario", "ubnt")
            senha = eq.get("ssh_senha", "")
            porta = eq.get("ssh_porta", 22)
            nome = eq.get("nome", "desconhecido")
            
            if not ip or not senha:
                resultados.append({
                    "nome": nome,
                    "ip": ip,
                    "configuracao": None,
                    "sucesso": False,
                    "erro": "IP ou senha não configurados"
                })
                continue
            
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, port=porta, username=usuario, password=senha, timeout=10)
                
                stdin, stdout, stderr = ssh.exec_command("cat /tmp/system.cfg 2>/dev/null")
                configuracao = stdout.read().decode('utf-8')
                
                if configuracao:
                    resultados.append({
                        "nome": nome,
                        "ip": ip,
                        "configuracao": configuracao,
                        "sucesso": True
                    })
                else:
                    stdin, stdout, stderr = ssh.exec_command("cat /etc/config/system 2>/dev/null")
                    configuracao = stdout.read().decode('utf-8')
                    if configuracao:
                        resultados.append({
                            "nome": nome,
                            "ip": ip,
                            "configuracao": configuracao,
                            "sucesso": True
                        })
                    else:
                        resultados.append({
                            "nome": nome,
                            "ip": ip,
                            "configuracao": None,
                            "sucesso": False,
                            "erro": "Configuração não encontrada"
                        })
                
                ssh.close()
                
            except paramiko.AuthenticationException:
                resultados.append({
                    "nome": nome,
                    "ip": ip,
                    "configuracao": None,
                    "sucesso": False,
                    "erro": "Falha na autenticação"
                })
            except Exception as e:
                resultados.append({
                    "nome": nome,
                    "ip": ip,
                    "configuracao": None,
                    "sucesso": False,
                    "erro": str(e)
                })
        
        return resultados
    
    def criar_arquivo_backup(self, resultados):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = f"backup_my_network_{timestamp}.zip"
        
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        caminho_zip = os.path.join(backup_dir, nome_arquivo)
        
        log_content = f"Backup realizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        log_content += "=" * 50 + "\n\n"
        
        sucessos = 0
        falhas = 0
        
        with zipfile.ZipFile(caminho_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Backup das configurações SSH dos equipamentos
            for resultado in resultados:
                if resultado["sucesso"]:
                    nome_arquivo_cfg = f"equipamentos/{resultado['nome']}_{resultado['ip']}.cfg"
                    zipf.writestr(nome_arquivo_cfg, resultado["configuracao"])
                    log_content += f"✅ {resultado['nome']} ({resultado['ip']}): OK\n"
                    sucessos += 1
                else:
                    log_content += f"❌ {resultado['nome']} ({resultado['ip']}): FALHA - {resultado.get('erro', 'Desconhecido')}\n"
                    falhas += 1
            
            # Backup do config.json
            config_path = self.config.config_path
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    zipf.writestr("config/config.json", f.read())
                log_content += f"\n✅ config.json: OK\n"
            else:
                log_content += f"\n❌ config.json: Arquivo não encontrado\n"
            
            # Backup do mynetwork.db
            db_path = os.path.join(self.config.config_dir, 'mynetwork.db')
            if os.path.exists(db_path):
                zipf.write(db_path, "database/mynetwork.db")
                log_content += f"✅ mynetwork.db: OK\n"
            else:
                log_content += f"❌ mynetwork.db: Arquivo não encontrado\n"
            
            zipf.writestr("log_backup.txt", log_content)
        
        return caminho_zip, sucessos, falhas, log_content
    
    def fazer_backup_agora(self, enviar_email=True):
        print("📁 Iniciando backup completo...")
        
        resultados = self.coletar_configuracoes_ssh()
        
        sucessos = sum(1 for r in resultados if r["sucesso"])
        falhas = len(resultados) - sucessos
        
        caminho_zip, sucessos, falhas, log_content = self.criar_arquivo_backup(resultados)
        
        self.historico.insert(0, {
            "data": datetime.now(),
            "arquivo": os.path.basename(caminho_zip),
            "equipamentos": sucessos,
            "falhas": falhas,
            "enviado": False
        })
        
        self.historico = self.historico[:10]
        self.salvar_historico()
        
        enviado = False
        if enviar_email and self.email_manager.esta_configurado():
            assunto = f"📁 Backup My Network - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            corpo = f"""Backup realizado com sucesso!

📊 Resumo:
- Equipamentos com sucesso: {sucessos}
- Equipamentos com falha: {falhas}
- Total: {len(resultados)}

📋 Detalhes:
{log_content}

📎 O arquivo de backup contém:
- Configurações dos equipamentos (SSH)
- config.json (configurações do app)
- mynetwork.db (banco de dados)

Att,
My Network
"""
            sucesso, mensagem = self.email_manager.enviar(assunto, corpo, caminho_zip)
            if sucesso:
                enviado = True
                self.historico[0]["enviado"] = True
                self.salvar_historico()
                print(f"✅ Backup enviado por email: {mensagem}")
            else:
                print(f"❌ Falha ao enviar email: {mensagem}")
        
        mensagem = f"Backup concluído! {sucessos} equipamentos salvos, {falhas} falhas."
        if enviado:
            mensagem += " Email enviado com sucesso!"
        
        return True, mensagem, caminho_zip
    
    def restaurar_backup(self, caminho_zip, reiniciar_callback=None):
        """Restaura um backup a partir de um arquivo ZIP"""
        import zipfile
        
        print(f"📂 Restaurando backup: {caminho_zip}")
        
        try:
            with zipfile.ZipFile(caminho_zip, 'r') as zipf:
                # Extrair config.json
                if "config/config.json" in zipf.namelist():
                    config_path = self.config.config_path
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    with open(config_path, 'wb') as f:
                        f.write(zipf.read("config/config.json"))
                    print("✅ config.json restaurado")
                
                # Extrair mynetwork.db
                if "database/mynetwork.db" in zipf.namelist():
                    db_path = os.path.join(self.config.config_dir, 'mynetwork.db')
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    with open(db_path, 'wb') as f:
                        f.write(zipf.read("database/mynetwork.db"))
                    print("✅ mynetwork.db restaurado")
                
                # Recarregar configurações
                self.config.recarregar()
                
                # Chamar callback para reiniciar sistemas
                if reiniciar_callback:
                    reiniciar_callback()
                
                return True, "Backup restaurado com sucesso!"
                
        except Exception as e:
            return False, f"Erro ao restaurar backup: {e}"
    
    def importar_arquivo(self, caminho_origem, tipo, reiniciar_callback=None):
        """Importa um arquivo individual (DB ou JSON)"""
        try:
            if tipo == "db":
                destino = os.path.join(self.config.config_dir, 'mynetwork.db')
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                shutil.copy2(caminho_origem, destino)
                print(f"✅ Banco de dados importado: {destino}")
                
            elif tipo == "json":
                destino = self.config.config_path
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                shutil.copy2(caminho_origem, destino)
                self.config.recarregar()
                print(f"✅ Configuração importada: {destino}")
            
            else:
                return False, "Tipo de arquivo inválido"
            
            # Chamar callback para reiniciar sistemas
            if reiniciar_callback:
                reiniciar_callback()
            
            return True, f"Arquivo {tipo} importado com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao importar arquivo: {e}"
    
    def salvar_historico(self):
        historico_str = []
        for item in self.historico:
            historico_str.append({
                "data": item["data"].isoformat(),
                "arquivo": item["arquivo"],
                "equipamentos": item["equipamentos"],
                "falhas": item["falhas"],
                "enviado": item["enviado"]
            })
        self.backup_config["historico"] = historico_str
        self.salvar_config()
    
    def carregar_historico(self):
        historico_str = self.backup_config.get("historico", [])
        self.historico = []
        for item in historico_str:
            self.historico.append({
                "data": datetime.fromisoformat(item["data"]),
                "arquivo": item["arquivo"],
                "equipamentos": item["equipamentos"],
                "falhas": item["falhas"],
                "enviado": item["enviado"]
            })
    
    def _calcular_proxima_execucao(self):
        """Calcula a próxima data/hora de execução baseado na configuração"""
        agora = datetime.now()
        intervalo = self.backup_config.get("intervalo", "24h")
        hora_str = self.backup_config.get("hora", "00:00")
        
        if intervalo in ["1h", "5h", "8h", "12h", "24h"]:
            intervalo_segundos = self._intervalo_para_segundos(intervalo)
            return agora.timestamp() + intervalo_segundos
        
        try:
            hora = int(hora_str.split(":")[0])
            minuto = int(hora_str.split(":")[1])
        except:
            hora = 0
            minuto = 0
        
        proxima = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        
        if proxima <= agora:
            if intervalo == "diario":
                proxima = proxima.replace(day=agora.day + 1)
            elif intervalo == "semanal":
                proxima = proxima.replace(day=agora.day + (7 - agora.weekday()))
            elif intervalo == "mensal":
                if agora.month == 12:
                    proxima = proxima.replace(year=agora.year + 1, month=1)
                else:
                    proxima = proxima.replace(month=agora.month + 1)
        
        return proxima.timestamp()
    
    def _intervalo_para_segundos(self, intervalo):
        intervalos = {
            "1h": 3600,
            "5h": 18000,
            "8h": 28800,
            "12h": 43200,
            "24h": 86400
        }
        return intervalos.get(intervalo, 86400)
    
    def iniciar_agendamento(self):
        if not self.backup_config.get("agendado", False):
            return
        
        self.agendamento_ativo = True
        self.thread_agendamento = threading.Thread(target=self._loop_agendamento, daemon=True)
        self.thread_agendamento.start()
        print("🕐 Agendamento de backup iniciado")
    
    def parar_agendamento(self):
        self.agendamento_ativo = False
        print("🕐 Agendamento de backup parado")
    
    def _loop_agendamento(self):
        intervalo = self.backup_config.get("intervalo", "24h")
        hora_str = self.backup_config.get("hora", "00:00")
        
        if intervalo in ["1h", "5h", "8h", "12h", "24h"]:
            intervalo_segundos = self._intervalo_para_segundos(intervalo)
            
            agora = datetime.now()
            hora_atual = agora.hour
            minuto_atual = agora.minute
            
            try:
                hora_agendada = int(hora_str.split(":")[0])
                minuto_agendado = int(hora_str.split(":")[1])
            except:
                hora_agendada = 0
                minuto_agendado = 0
            
            segundos_ate_proximo = 0
            
            if hora_atual < hora_agendada:
                segundos_ate_proximo = ((hora_agendada - hora_atual) * 3600) + (minuto_agendado - minuto_atual) * 60
            elif hora_atual == hora_agendada and minuto_atual < minuto_agendado:
                segundos_ate_proximo = (minuto_agendado - minuto_atual) * 60
            else:
                segundos_ate_proximo = ((24 - hora_atual) * 3600) + (hora_agendada * 3600) + (minuto_agendado - minuto_atual) * 60
            
            if segundos_ate_proximo > 0:
                print(f"🕐 Primeiro backup em {segundos_ate_proximo // 3600}h {(segundos_ate_proximo % 3600) // 60}min")
                time.sleep(segundos_ate_proximo)
            
            while self.agendamento_ativo:
                self.fazer_backup_agora(enviar_email=True)
                time.sleep(intervalo_segundos)
        
        else:
            proxima_timestamp = self._calcular_proxima_execucao()
            agora_timestamp = datetime.now().timestamp()
            
            segundos_espera = max(0, proxima_timestamp - agora_timestamp)
            
            if segundos_espera > 0:
                print(f"🕐 Primeiro backup em {segundos_espera // 3600}h {(segundos_espera % 3600) // 60}min")
                time.sleep(segundos_espera)
            
            while self.agendamento_ativo:
                self.fazer_backup_agora(enviar_email=True)
                
                proxima_timestamp = self._calcular_proxima_execucao()
                agora_timestamp = datetime.now().timestamp()
                segundos_espera = max(0, proxima_timestamp - agora_timestamp)
                time.sleep(segundos_espera)