import requests

class TelegramManager:
    def __init__(self, token="", chat_id=""):
        self.token = token
        self.chat_id = chat_id
    
    def configurar(self, token, chat_id):
        """Configura o token e chat_id do Telegram"""
        self.token = token
        self.chat_id = chat_id
    
    def esta_configurado(self):
        """Verifica se o Telegram está configurado"""
        return bool(self.token and self.chat_id)
    
    def enviar(self, texto):
        """Envia uma mensagem para o Telegram"""
        if not self.esta_configurado():
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            dados = {"chat_id": self.chat_id, "text": texto}
            response = requests.post(url, data=dados, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem Telegram: {e}")
            return False
    
    def testar(self):
        """Envia uma mensagem de teste"""
        return self.enviar("🔔 Teste: My Network está funcionando!")