import requests
import time
from datetime import datetime

class FirebaseAuth:
    def __init__(self):
        self.api_key = "AIzaSyCiOTnCBKCsJw32ExvzoOjlFNnkF-kMFHk"
        self.project_id = "meusitemynetwork"
        self.auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        self.firestore_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
        
        self.uid = None
        self.token = None
        self.email = None
        self.senha = None
        self.autenticado = False
        self.ultima_tentativa = None
        self.proxima_tentativa = None
        self.tentativas_falhas = 0
    
    def configurar(self, email, senha):
        self.email = email
        self.senha = senha
    
    def autenticar(self):
        if not self.email or not self.senha:
            return False
        self.ultima_tentativa = datetime.now()
        data = {"email": self.email, "password": self.senha, "returnSecureToken": True}
        try:
            response = requests.post(self.auth_url, json=data, timeout=10)
            if response.status_code == 200:
                dados = response.json()
                self.uid = dados.get('localId')
                self.token = dados.get('idToken')
                self.autenticado = True
                self.tentativas_falhas = 0
                print(f"✅ Firebase autenticado: {self.email}")
                return True
            else:
                self.autenticado = False
                self.tentativas_falhas += 1
                print(f"❌ Falha autenticação: {response.status_code}")
                return False
        except Exception as e:
            self.autenticado = False
            self.tentativas_falhas += 1
            print(f"❌ Erro autenticação: {e}")
            return False
    
    def salvar_url(self, url_tunel):
        """Salva a URL do túnel no Firestore - perfil, empresa e vínculos"""
        if not self.autenticado or not self.token:
            print("⚠️ Não autenticado, não pode salvar URL")
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # 1. Busca empresaId do usuário
            user_url = f"{self.firestore_url}/usuarios/{self.uid}"
            resp = requests.get(user_url, headers=headers, timeout=10)
            
            empresa_id = None
            if resp.status_code == 200:
                user_data = resp.json()
                if 'fields' in user_data and 'empresaId' in user_data['fields']:
                    empresa_id = user_data['fields']['empresaId'].get('stringValue', '')
            
            # 2. Atualiza URL no perfil do usuário (SEMPRE inclui empresaId)
            update_url = f"{user_url}?updateMask.fieldPaths=email&updateMask.fieldPaths=url_tunel&updateMask.fieldPaths=atualizado_em&updateMask.fieldPaths=empresaId"
            
            fields = {
                "email": {"stringValue": self.email},
                "url_tunel": {"stringValue": url_tunel},
                "atualizado_em": {"stringValue": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                "empresaId": {"stringValue": empresa_id or ""}
            }
            
            data = {"fields": fields}
            response = requests.patch(update_url, headers=headers, json=data, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ URL salva no perfil: {url_tunel}")
                
                if empresa_id:
                    self._atualizar_url_empresa(empresa_id, url_tunel, headers)
                    self._atualizar_url_vinculos(empresa_id, url_tunel, headers)
                else:
                    print("⚠️ empresaId não encontrado, pulando atualização de empresa e vínculos")
                
                return True
            else:
                print(f"❌ Erro ao salvar URL: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao salvar URL: {e}")
            return False
    
    def _atualizar_url_empresa(self, empresa_id, url_tunel, headers):
        try:
            empresa_url = f"{self.firestore_url}/empresas/{empresa_id}?updateMask.fieldPaths=url_tunel&updateMask.fieldPaths=atualizado_em"
            data = {
                "fields": {
                    "url_tunel": {"stringValue": url_tunel},
                    "atualizado_em": {"stringValue": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                }
            }
            resp = requests.patch(empresa_url, headers=headers, json=data, timeout=10)
            if resp.status_code in [200, 204]:
                print(f"✅ URL atualizada na empresa {empresa_id}")
            else:
                print(f"⚠️ Erro ao atualizar empresa {empresa_id}: {resp.status_code}")
        except Exception as e:
            print(f"⚠️ Erro ao atualizar empresa: {e}")
    
    def _atualizar_url_vinculos(self, empresa_id, url_tunel, headers):
        try:
            query_url = f"{self.firestore_url}/vinculos?pageSize=1000"
            resp = requests.get(query_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"⚠️ Erro ao buscar vínculos: {resp.status_code}")
                return
            documentos = resp.json()
            if 'documents' not in documentos:
                print("⚠️ Nenhum vínculo encontrado")
                return
            atualizados = 0
            for doc in documentos['documents']:
                fields = doc.get('fields', {})
                vinculo_empresa = fields.get('empresaId', {}).get('stringValue', '')
                status = fields.get('status', {}).get('stringValue', '')
                if vinculo_empresa == empresa_id and status == 'aprovado':
                    doc_name = doc['name'].split('/')[-1]
                    update_url = f"{self.firestore_url}/vinculos/{doc_name}?updateMask.fieldPaths=url_tunel"
                    data = {"fields": {"url_tunel": {"stringValue": url_tunel}}}
                    r = requests.patch(update_url, headers=headers, json=data, timeout=10)
                    if r.status_code in [200, 204]:
                        atualizados += 1
                        print(f"   ✅ URL atualizada no vínculo: {doc_name}")
            print(f"✅ URL atualizada em {atualizados} vínculos")
        except Exception as e:
            print(f"⚠️ Erro ao atualizar vínculos: {e}")
    
    def esta_configurado(self):
        return bool(self.email and self.senha)
    
    def resetar_tentativas(self):
        self.tentativas_falhas = 0