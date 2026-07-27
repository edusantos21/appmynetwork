import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

class EmailManager:
    def __init__(self):
        self.config = {
            "provedor": "",
            "email_envio": "",
            "senha": "",
            "email_destino": "",
            "smtp_server": "",
            "smtp_porta": 587
        }
    
    def configurar(self, provedor, email_envio, senha, email_destino, smtp_server=None, smtp_porta=None):
        """Configura o email com base no provedor escolhido"""
        self.config["provedor"] = provedor
        self.config["email_envio"] = email_envio
        self.config["senha"] = senha
        self.config["email_destino"] = email_destino
        
        # Configurar SMTP automaticamente baseado no provedor
        provedores = {
            "gmail": {"server": "smtp.gmail.com", "porta": 587},
            "outlook": {"server": "smtp-mail.outlook.com", "porta": 587},
            "yahoo": {"server": "smtp.mail.yahoo.com", "porta": 587},
            "hotmail": {"server": "smtp.live.com", "porta": 587},
            "terra": {"server": "smtp.terra.com.br", "porta": 587},
            "uol": {"server": "smtp.uol.com.br", "porta": 587}
        }
        
        if provedor.lower() in provedores:
            self.config["smtp_server"] = provedores[provedor.lower()]["server"]
            self.config["smtp_porta"] = provedores[provedor.lower()]["porta"]
        else:
            # Provedor personalizado (outro)
            self.config["smtp_server"] = smtp_server or ""
            self.config["smtp_porta"] = smtp_porta or 587
    
    def esta_configurado(self):
        """Verifica se o email está configurado"""
        return bool(self.config["email_envio"] and 
                   self.config["senha"] and 
                   self.config["email_destino"] and 
                   self.config["smtp_server"])
    
    def testar(self):
        """Envia um email de teste"""
        if not self.esta_configurado():
            return False, "Email não configurado"
        
        return self.enviar(
            assunto="🔔 My Network - Teste de Email",
            corpo="Este é um email de teste do sistema My Network.\n\nSe você recebeu este email, a configuração está correta!\n\nAtt,\nMy Network"
        )
    
    def enviar(self, assunto, corpo, anexo_path=None):
        """Envia um email com ou sem anexo"""
        if not self.esta_configurado():
            return False, "Email não configurado"
        
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg["From"] = self.config["email_envio"]
            msg["To"] = self.config["email_destino"]
            msg["Subject"] = assunto
            
            # Corpo do email
            msg.attach(MIMEText(corpo, "plain", "utf-8"))
            
            # Adicionar anexo se existir
            if anexo_path and os.path.exists(anexo_path):
                with open(anexo_path, "rb") as anexo:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(anexo.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(anexo_path)}",
                    )
                    msg.attach(part)
            
            # Conectar e enviar
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_porta"]) as server:
                server.starttls(context=context)
                server.login(self.config["email_envio"], self.config["senha"])
                server.send_message(msg)
            
            return True, "Email enviado com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao enviar email: {str(e)}"
    
    def get_config(self):
        """Retorna a configuração atual"""
        return self.config.copy()
    
    def set_config(self, config):
        """Define a configuração a partir de um dicionário"""
        self.config.update(config)
    
    def get_provedores(self):
        """Retorna lista de provedores disponíveis"""
        return ["gmail", "outlook", "yahoo", "hotmail", "terra", "uol", "outro"]