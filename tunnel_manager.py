# tunnel_manager.py - VERSÃO FINAL (GETs DO MONITOR, CRUD NORMAL)
import subprocess
import threading
import time
import re
import requests
import os
import queue
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ========== LOCK DO TÚNEL ==========
tunel_lock = threading.Lock()

# ========== BLOQUEAR ACESSO LOCAL ==========
@app.before_request
def bloquear_local():
    if request.method == 'OPTIONS':
        return '', 200
    host = request.host
    if request.path == '/':
        return None
    if 'localhost' in host or host.startswith('127.') or host.startswith('192.168.'):
        return jsonify({'erro': 'Acesso apenas via túnel'}), 403

# ========== ESTADOS DO TÚNEL ==========
PARADO = 'parado'
CONECTANDO = 'conectando'
ATIVO = 'ativo'

estado_tunel = PARADO
processo_tunel = None
url_publica = None
flask_pronto = False
PORTA = None
ultima_alteracao = None

thread_reconexao = None
reconexao_ativa = True

COOLDOWN_FALHA = 40
ultima_tentativa_falha = None

TIMEOUT_CONEXAO = 30

INTERVALO_VERIFICACAO = 10

ESPERA_POS_ATIVACAO = 60
ultima_ativacao = None

monitor_ref = None
firebase_auth_ref = None

CLOUDFLARED_PATH = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'My Network', 'cloudflared.exe')

# ========== FILA DE URL PENDENTE ==========
url_pendente_firebase = None
lock_url_pendente = threading.Lock()
thread_salvando_url = None

# ========== VERIFICAR SAÚDE DO TÚNEL ==========
def verificar_tunel_saudavel():
    if not url_publica:
        return False
    try:
        response = requests.get(f"{url_publica}/", timeout=5)
        return response.status_code == 200
    except:
        return False

# ========== SALVAR URL NO FIREBASE (COM FILA DE TENTATIVAS) ==========
def salvar_url_firebase(url):
    global url_pendente_firebase, thread_salvando_url
    if not url:
        return
    if not firebase_auth_ref:
        return
    
    with lock_url_pendente:
        url_pendente_firebase = url
    
    # Se já tem thread tentando, não cria outra
    if thread_salvando_url and thread_salvando_url.is_alive():
        return
    
    thread_salvando_url = threading.Thread(target=_tentar_salvar_url, daemon=True)
    thread_salvando_url.start()

def _tentar_salvar_url():
    global url_pendente_firebase, thread_salvando_url
    while True:
        with lock_url_pendente:
            url = url_pendente_firebase
        if not url:
            thread_salvando_url = None
            break
        
        try:
            if not firebase_auth_ref.autenticado:
                print("🔐 Autenticando no Firebase...")
                firebase_auth_ref.autenticar()
            
            firebase_auth_ref.salvar_url(url)
            print(f"✅ URL salva no Firebase: {url}")
            with lock_url_pendente:
                url_pendente_firebase = None
            thread_salvando_url = None
            break
        except Exception as e:
            print(f"❌ Falha ao salvar URL: {e}. Tentando novamente em 10s...")
            time.sleep(10)

# ========== MATAR CLOUDFLARED ==========
def matar_todos_cloudflared():
    try:
        subprocess.run(
            ['taskkill', '/F', '/IM', 'cloudflared.exe'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        time.sleep(2)
    except:
        pass

# ========== LEITURA DE STDOUT ==========
def _ler_stdout_em_thread(processo, fila):
    try:
        for linha in processo.stdout:
            fila.put(linha)
    except Exception:
        pass
    finally:
        fila.put(None)

# ========== INICIAR TÚNEL ==========
def _iniciar_tunel_interno():
    global processo_tunel, url_publica, estado_tunel, ultima_tentativa_falha, ultima_ativacao

    if not flask_pronto:
        return None

    cloudflared = CLOUDFLARED_PATH if os.path.exists(CLOUDFLARED_PATH) else 'cloudflared'
    estado_tunel = CONECTANDO

    try:
        processo_tunel = subprocess.Popen(
            [cloudflared, 'tunnel', '--url', f'http://localhost:{PORTA}', '--protocol', 'http2'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
    except FileNotFoundError:
        print(f"❌ cloudflared não encontrado: {cloudflared}")
        estado_tunel = PARADO
        ultima_tentativa_falha = datetime.now()
        return None
    except Exception as e:
        print(f"❌ Erro ao iniciar cloudflared: {e}")
        estado_tunel = PARADO
        ultima_tentativa_falha = datetime.now()
        return None

    fila = queue.Queue()
    leitor = threading.Thread(target=_ler_stdout_em_thread, args=(processo_tunel, fila), daemon=True)
    leitor.start()

    inicio = time.time()
    while time.time() - inicio < TIMEOUT_CONEXAO:
        if processo_tunel.poll() is not None:
            print(f"❌ cloudflared encerrou sozinho (código {processo_tunel.returncode})")
            break

        try:
            linha = fila.get(timeout=1)
        except queue.Empty:
            continue

        if linha is None:
            break

        linha = linha.rstrip()
        if linha:
            print(f"[cloudflared] {linha}")

        if 'trycloudflare.com' in linha:
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', linha)
            if match:
                url_publica = match.group(0)
                estado_tunel = ATIVO
                ultima_ativacao = datetime.now()
                salvar_url_firebase(url_publica)
                print(f"✅ Túnel ativo: {url_publica}")
                return url_publica

    print("⏰ Timeout ou falha ao obter URL do túnel.")
    try:
        processo_tunel.kill()
    except:
        pass
    estado_tunel = PARADO
    ultima_tentativa_falha = datetime.now()
    return None

# ========== REINICIAR TÚNEL ==========
def reiniciar_tunel(forcar=False):
    global processo_tunel, estado_tunel, url_publica

    if not tunel_lock.acquire(blocking=False):
        print("⏳ Já tem outro reinício em andamento, ignorando...")
        return url_publica

    try:
        if not forcar and ultima_tentativa_falha:
            segundos = (datetime.now() - ultima_tentativa_falha).total_seconds()
            if segundos < COOLDOWN_FALHA:
                return url_publica

        print("🔄 Reiniciando túnel...")
        matar_todos_cloudflared()

        if processo_tunel:
            try:
                processo_tunel.kill()
            except:
                pass
            processo_tunel = None

        estado_tunel = PARADO
        url_publica = None

        print("🚀 Iniciando novo túnel...")
        resultado = _iniciar_tunel_interno()

        if resultado is None:
            print("😞 Falha ao iniciar!")
        else:
            print(f"🎊 Túnel pronto! URL: {resultado}")
            salvar_url_firebase(resultado)

        return resultado
    finally:
        tunel_lock.release()

# ========== LOOP DE RECONEXÃO ==========
def loop_reconexao_programada():
    while reconexao_ativa:
        try:
            if estado_tunel == ATIVO:
                if ultima_ativacao is None or \
                   (datetime.now() - ultima_ativacao).total_seconds() >= ESPERA_POS_ATIVACAO:
                    if not verificar_tunel_saudavel():
                        print("🔴 Túnel não está respondendo! Gerando novo...")
                        nova_url = reiniciar_tunel()
                        if nova_url:
                            salvar_url_firebase(nova_url)
                    
            elif estado_tunel == PARADO:
                print("🔴 Túnel offline! Tentando ligar...")
                nova_url = reiniciar_tunel()
                if nova_url:
                    salvar_url_firebase(nova_url)
            
            time.sleep(INTERVALO_VERIFICACAO)
            
        except Exception as e:
            print(f"💥 Erro: {e}")
            time.sleep(INTERVALO_VERIFICACAO)

def iniciar_tunel_com_reconexao():
    global thread_reconexao, reconexao_ativa

    reconexao_ativa = True

    # ✅ Garante autenticação ANTES de iniciar o túnel
    if firebase_auth_ref and not firebase_auth_ref.autenticado:
        print("🔐 Autenticando Firebase antes do túnel...")
        try:
            firebase_auth_ref.autenticar()
            print("✅ Firebase autenticado!")
        except Exception as e:
            print(f"⚠️ Falha na autenticação inicial: {e}")

    if thread_reconexao is None or not thread_reconexao.is_alive():
        thread_reconexao = threading.Thread(target=loop_reconexao_programada, daemon=True)
        thread_reconexao.start()

    reiniciar_tunel(forcar=True)

def parar_tunel():
    global reconexao_ativa, processo_tunel, estado_tunel, url_publica, url_pendente_firebase
    reconexao_ativa = False
    matar_todos_cloudflared()
    if processo_tunel:
        try:
            processo_tunel.kill()
        except:
            pass
    processo_tunel = None
    estado_tunel = PARADO
    url_publica = None
    with lock_url_pendente:
        url_pendente_firebase = None
    print("🛑 Túnel parado")

def get_url():
    return url_publica

def tunel_esta_ativo():
    return estado_tunel == ATIVO and url_publica is not None

def flask_esta_pronto():
    return flask_pronto

# ========== FLASK ==========
def iniciar_flask(db, monitor, firebase_auth=None, porta=None):
    global flask_pronto, monitor_ref, firebase_auth_ref, PORTA, ultima_alteracao

    monitor_ref = monitor
    firebase_auth_ref = firebase_auth

    if porta is None:
        from config import Config
        config = Config()
        porta = config.get_configuracoes().get("porta_flask", 8080)

    PORTA = porta

    def atualizar_monitor(id_alterado=None):
        global ultima_alteracao
        if monitor_ref:
            try:
                equipamentos = db.listar_equipamentos()
                clientes = db.listar_clientes()
                monitor_ref.atualizar_configuracoes(equipamentos, monitor_ref.configuracoes, clientes)
                ultima_alteracao = id_alterado
            except:
                pass

    # ========== TÚNEL ==========
    @app.route('/tunel/status', methods=['GET'])
    def api_status_tunel():
        return jsonify({'estado': estado_tunel, 'url': url_publica})

    @app.route('/tunel/reiniciar', methods=['POST'])
    def api_reiniciar_tunel():
        nova_url = reiniciar_tunel(forcar=True)
        if nova_url:
            salvar_url_firebase(nova_url)
        return jsonify({'sucesso': True, 'url': nova_url})

    # ========== GETs DO MONITOR ==========
    @app.route('/equipamentos', methods=['GET'])
    def api_equipamentos():
        if monitor_ref:
            todos = monitor_ref.get_estado()
            return jsonify([e for e in todos if e.get('tipo') == 'equipamento'])
        return jsonify([])

    @app.route('/p2p', methods=['GET'])
    def api_p2p():
        if monitor_ref:
            todos = monitor_ref.get_estado()
            return jsonify([e for e in todos if e.get('modo_operacao') == 'p2p'])
        return jsonify([])

    @app.route('/servidores', methods=['GET'])
    def api_servidores():
        if monitor_ref:
            return jsonify(monitor_ref.get_servidores_estado())
        return jsonify([])

    @app.route('/energias', methods=['GET'])
    def api_energias():
        if monitor_ref:
            return jsonify(monitor_ref.get_energias_estado())
        return jsonify([])

    @app.route('/servicos', methods=['GET'])
    def api_servicos():
        if monitor_ref:
            return jsonify(monitor_ref.get_servicos_estado())
        return jsonify([])

    @app.route('/clientes', methods=['GET'])
    def api_clientes():
        if monitor_ref:
            return jsonify(monitor_ref.get_clientes_estado())
        return jsonify([])

    @app.route('/localidades', methods=['GET'])
    def api_localidades():
        return jsonify(db.listar_localidades())

    # ========== CRUD EQUIPAMENTOS ==========
    @app.route('/equipamento', methods=['POST'])
    def api_adicionar_equipamento():
        dados = request.json
        sucesso, id = db.salvar_equipamento(dados)
        atualizar_monitor(id)
        return jsonify({'sucesso': sucesso, 'id': id})

    @app.route('/equipamento/<int:id>', methods=['PUT'])
    def api_editar_equipamento(id):
        dados = request.json
        dados['id'] = id
        sucesso, _ = db.salvar_equipamento(dados)
        atualizar_monitor(id)
        return jsonify({'sucesso': sucesso})

    @app.route('/equipamento/<int:id>', methods=['DELETE'])
    def api_excluir_equipamento(id):
        db.excluir_equipamento(id)
        atualizar_monitor(id)
        return jsonify({'sucesso': True})

    # ========== CRUD CLIENTES ==========
    @app.route('/cliente', methods=['POST'])
    def api_adicionar_cliente():
        dados = request.json
        sucesso, id = db.salvar_cliente(dados)
        atualizar_monitor(id)
        return jsonify({'sucesso': sucesso, 'id': id})

    @app.route('/cliente/<int:id>', methods=['PUT'])
    def api_editar_cliente(id):
        dados = request.json
        dados['id'] = id
        sucesso, _ = db.salvar_cliente(dados)
        atualizar_monitor(id)
        return jsonify({'sucesso': sucesso})

    @app.route('/cliente/<int:id>', methods=['DELETE'])
    def api_excluir_cliente(id):
        db.excluir_cliente(id)
        atualizar_monitor(id)
        return jsonify({'sucesso': True})

    # ========== CRUD LOCALIDADES ==========
    @app.route('/localidade', methods=['POST'])
    def api_adicionar_localidade():
        dados = request.json
        nome = dados.get('nome', '').strip()
        if nome:
            db.salvar_localidade(nome)
            atualizar_monitor(-1)
            return jsonify({'sucesso': True})
        return jsonify({'erro': 'Nome obrigatório'}), 400

    @app.route('/localidade/<nome>', methods=['PUT'])
    def api_editar_localidade(nome):
        dados = request.json
        novo_nome = dados.get('nome', '').strip()
        if novo_nome and novo_nome != nome:
            equipamentos = db.listar_equipamentos()
            for eq in equipamentos:
                if eq.get('localidade') == nome:
                    eq['localidade'] = novo_nome
                    db.salvar_equipamento(eq)
            db.excluir_localidade(nome)
            db.salvar_localidade(novo_nome)
            atualizar_monitor(-1)
            return jsonify({'sucesso': True})
        return jsonify({'erro': 'Nome obrigatório'}), 400

    @app.route('/localidade/<nome>', methods=['DELETE'])
    def api_excluir_localidade(nome):
        equipamentos = db.listar_equipamentos()
        for eq in equipamentos:
            if eq.get('localidade') == nome:
                eq['localidade'] = ''
                db.salvar_equipamento(eq)
        db.excluir_localidade(nome)
        atualizar_monitor(-1)
        return jsonify({'sucesso': True})

    @app.route('/')
    def home():
        return jsonify({'status': 'online', 'projeto': 'My Network'})

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    print(f"Iniciando Flask na porta {PORTA}...")
    try:
        app.run(host='0.0.0.0', port=PORTA, debug=False, use_reloader=False)
        flask_pronto = True
    except Exception as e:
        print(f"Erro ao iniciar Flask: {e}")
        flask_pronto = False

def esperar_flask_pronto(max_tentativas=10):
    global flask_pronto
    for _ in range(max_tentativas):
        try:
            response = requests.get(f"http://localhost:{PORTA}/", timeout=2)
            if response.status_code == 200:
                flask_pronto = True
                return True
        except:
            pass
        time.sleep(1)
    return False