# config.py - COMPLETO (COM intervalo_tunel + proxima_renovacao)
import json
import os

class Config:
    def __init__(self):
        # Pasta do AppData
        self.config_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'My Network')
        self.config_path = os.path.join(self.config_dir, 'config.json')
        
        # Criar pasta se não existir
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            print(f"📁 Pasta de configuração criada: {self.config_dir}")
        
        # Configurações padrão
        self.telegram_config = {}
        self.email_config = {}
        self.backup_config = {
            "agendado": False,
            "intervalo": "24h",
            "hora": "00:00",
            "historico": []
        }
        self.snmp_config = {
            "enabled": False,
            "usuario": "ubnt",
            "senha": "",
            "porta": 22,
            "intervalo": 30
        }
        self.configuracoes = {
            "timeout_ms": 500,
            "intervalo_segundos": 5,
            "quantidade_pings": 3,
            "limite_instavel": 50,
            "limite_offline": 100,
            "snmp_intervalo": 30,
            "salvar_intervalo": 10,
            "heartbeat_intervalo": 60,
            "porta_flask": 8080,
            "intervalo_tunel": "1h",
            "proxima_renovacao": None  # 🔥 NOVO
        }
        
        # NOVAS configurações (Firebase/Conta)
        self.firebase_credenciais = {
            "email": "",
            "senha": "",
            "lembrar": False
        }
        self.reconexao = {
            "ativa": False,
            "intervalo_minutos": 1,
            "max_tentativas": 0,
            "tentativas_atual": 0
        }
        
        self.carregar()
    
    def carregar(self):
        """Carrega as configurações do arquivo"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                    # Configurações existentes
                    self.telegram_config = dados.get("telegram", {})
                    self.email_config = dados.get("email_config", {})
                    
                    # Backup config
                    backup = dados.get("backup_config", {})
                    self.backup_config = {
                        "agendado": backup.get("agendado", False),
                        "intervalo": backup.get("intervalo", "24h"),
                        "hora": backup.get("hora", "00:00"),
                        "historico": backup.get("historico", [])
                    }
                    
                    # SNMP/SSH config
                    snmp = dados.get("snmp_config", {})
                    self.snmp_config = {
                        "enabled": snmp.get("enabled", False),
                        "usuario": snmp.get("usuario", "ubnt"),
                        "senha": snmp.get("senha", ""),
                        "porta": int(snmp.get("porta", 22)) if snmp.get("porta") else 22,
                        "intervalo": int(snmp.get("intervalo", 30)) if snmp.get("intervalo") else 30
                    }
                    
                    # Configurações do monitor
                    configs = dados.get("configuracoes", {})
                    
                    def to_int(value, default):
                        if value is None or value == "":
                            return default
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            return default
                    
                    self.configuracoes = {
                        "timeout_ms": to_int(configs.get("timeout_ms"), 500),
                        "intervalo_segundos": to_int(configs.get("intervalo_segundos"), 5),
                        "quantidade_pings": to_int(configs.get("quantidade_pings"), 3),
                        "limite_instavel": to_int(configs.get("limite_instavel"), 50),
                        "limite_offline": to_int(configs.get("limite_offline"), 100),
                        "snmp_intervalo": to_int(configs.get("snmp_intervalo"), 30),
                        "salvar_intervalo": to_int(configs.get("salvar_intervalo"), 10),
                        "heartbeat_intervalo": to_int(configs.get("heartbeat_intervalo"), 60),
                        "porta_flask": to_int(configs.get("porta_flask"), 8080),
                        "intervalo_tunel": configs.get("intervalo_tunel", "1h"),
                        "proxima_renovacao": configs.get("proxima_renovacao", None)  # 🔥 NOVO
                    }
                    
                    # NOVAS configurações
                    self.firebase_credenciais = dados.get("firebase_credenciais", {
                        "email": "",
                        "senha": "",
                        "lembrar": False
                    })
                    
                    self.reconexao = dados.get("reconexao", {
                        "ativa": False,
                        "intervalo_minutos": 1,
                        "max_tentativas": 0,
                        "tentativas_atual": 0
                    })
                    
                print(f"✅ Configuração carregada de: {self.config_path}")
            except Exception as e:
                print(f"❌ Erro ao carregar config.json: {e}")
        else:
            print(f"📝 Nenhuma configuração encontrada. Será criada em: {self.config_path}")
            self.salvar()
    
    def salvar(self):
        """Salva as configurações no arquivo"""
        dados = {
            "telegram": self.telegram_config,
            "email_config": self.email_config,
            "backup_config": self.backup_config,
            "snmp_config": self.snmp_config,
            "configuracoes": self.configuracoes,
            "firebase_credenciais": self.firebase_credenciais,
            "reconexao": self.reconexao
        }
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            print(f"💾 Configuração salva em: {self.config_path}")
        except Exception as e:
            print(f"❌ Erro ao salvar config.json: {e}")
    
    def recarregar(self):
        """Recarrega as configurações do arquivo (útil após restaurar backup)"""
        print("🔄 Recarregando configurações...")
        self.carregar()
        return True
    
    # ========== GETTERS E SETTERS ==========
    def get_telegram_config(self):
        return self.telegram_config
    
    def set_telegram_config(self, config):
        self.telegram_config = config
        self.salvar()
    
    def get_email_config(self):
        return self.email_config
    
    def set_email_config(self, config):
        self.email_config = config
        self.salvar()
    
    def get_backup_config(self):
        return self.backup_config
    
    def set_backup_config(self, config):
        self.backup_config.update(config)
        self.salvar()
    
    def get_snmp_config(self):
        return self.snmp_config
    
    def set_snmp_config(self, config):
        self.snmp_config.update(config)
        self.salvar()
    
    def get_configuracoes(self):
        return self.configuracoes
    
    def set_configuracoes(self, config):
        self.configuracoes.update(config)
        self.salvar()
    
    def get_firebase_credenciais(self):
        return self.firebase_credenciais
    
    def set_firebase_credenciais(self, credenciais):
        self.firebase_credenciais = credenciais
        self.salvar()
    
    def get_reconexao(self):
        return self.reconexao
    
    def set_reconexao(self, reconexao):
        self.reconexao = reconexao
        self.salvar()
    
    # ========== MÉTODOS PARA COMPATIBILIDADE ==========
    def get_equipamentos(self):
        """Compatibilidade - agora usa database.py"""
        from database import Database
        db = Database()
        return db.listar_equipamentos()
    
    def set_equipamentos(self, equipamentos):
        """Compatibilidade - agora usa database.py"""
        from database import Database
        db = Database()
        for eq in equipamentos:
            db.salvar_equipamento(eq)
    
    def get_localidades(self):
        from database import Database
        db = Database()
        return db.listar_localidades()
    
    def set_localidades(self, localidades):
        from database import Database
        db = Database()
        for local in localidades:
            db.salvar_localidade(local)
    
    def get_clientes(self):
        from database import Database
        db = Database()
        return db.listar_clientes()
    
    def set_clientes(self, clientes):
        from database import Database
        db = Database()
        for cliente in clientes:
            db.salvar_cliente(cliente)