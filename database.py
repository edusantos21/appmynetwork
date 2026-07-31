# database.py - COMPLETO (WAL Mode + coluna tipo + firmware + N/A)
import sqlite3
import os
from datetime import datetime


class Database:
    def __init__(self):
        self.appdata_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'My Network')
        self.db_path = os.path.join(self.appdata_dir, 'mynetwork.db')
        
        if not os.path.exists(self.appdata_dir):
            os.makedirs(self.appdata_dir)
            print(f"Pasta criada: {self.appdata_dir}")
        
        self.conectar()
        self.criar_tabelas()
    
    def conectar(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn
    
    def criar_tabelas(self):
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ip TEXT NOT NULL,
                porta TEXT DEFAULT '80',
                localidade TEXT DEFAULT '',
                modo_operacao TEXT DEFAULT 'cliente',
                tipo TEXT DEFAULT 'equipamento',
                firmware TEXT DEFAULT 'ubiquiti',
                status TEXT DEFAULT 'N/A',
                latencia REAL DEFAULT 0,
                ssh_enabled INTEGER DEFAULT 1,
                ssh_usuario TEXT DEFAULT 'ubnt',
                ssh_senha TEXT DEFAULT '',
                ssh_porta INTEGER DEFAULT 22,
                dados_snmp TEXT DEFAULT '{}',
                ultima_atualizacao TEXT,
                p2p_tipo TEXT DEFAULT '',
                p2p_par TEXT DEFAULT ''
            )
        ''')
        
        # Adiciona colunas que podem não existir em versões antigas
        for coluna, tipo in [
            ('tipo', 'TEXT DEFAULT "equipamento"'),
            ('firmware', 'TEXT DEFAULT "ubiquiti"'),
        ]:
            try:
                cursor.execute(f'ALTER TABLE equipamentos ADD COLUMN {coluna} {tipo}')
            except:
                pass
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS localidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ip TEXT NOT NULL,
                tipo TEXT DEFAULT 'radio',
                painel TEXT DEFAULT '',
                localidade TEXT DEFAULT '',
                pon_id TEXT DEFAULT '',
                endereco TEXT DEFAULT '',
                status TEXT DEFAULT 'N/A',
                latencia REAL DEFAULT 0
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipamentos_ip ON equipamentos(ip)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_equipamentos_tipo ON equipamentos(tipo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_ip ON clientes(ip)')
        
        conn.commit()
        conn.close()
        print("Banco de dados inicializado (WAL Mode)")
    
    # ========== EQUIPAMENTOS ==========
    def listar_equipamentos(self, tipo=None):
        conn = self.conectar()
        cursor = conn.cursor()
        
        if tipo:
            cursor.execute('SELECT * FROM equipamentos WHERE tipo = ? ORDER BY id', (tipo,))
        else:
            cursor.execute('SELECT * FROM equipamentos ORDER BY id')
        
        rows = cursor.fetchall()
        conn.close()
        
        equipamentos = []
        for row in rows:
            import json
            
            eq = {
                'id': row['id'],
                'nome': row['nome'],
                'ip': row['ip'],
                'porta': row['porta'],
                'localidade': row['localidade'],
                'modo_operacao': row['modo_operacao'],
                'tipo': row['tipo'] if 'tipo' in row.keys() else 'equipamento',
                'firmware': row['firmware'] if 'firmware' in row.keys() else 'ubiquiti',
                'status': row['status'],
                'latencia': row['latencia'],
                'ssh_enabled': bool(row['ssh_enabled']),
                'ssh_usuario': row['ssh_usuario'],
                'ssh_senha': row['ssh_senha'],
                'ssh_porta': row['ssh_porta'],
                'p2p_tipo': row['p2p_tipo'] or '',
                'p2p_par': row['p2p_par'] or '',
            }
            
            try:
                eq['dados_snmp'] = json.loads(row['dados_snmp']) if row['dados_snmp'] else {}
            except:
                eq['dados_snmp'] = {}
            
            eq['ultima_atualizacao'] = row['ultima_atualizacao']
            equipamentos.append(eq)
        return equipamentos
    
    def listar_por_tipo(self, tipo):
        return self.listar_equipamentos(tipo=tipo)
    
    def salvar_equipamento(self, equipamento):
        import json
        conn = self.conectar()
        cursor = conn.cursor()
        
        dados_snmp = equipamento.get('dados_snmp', {})
        if not isinstance(dados_snmp, dict):
            dados_snmp = {}
        dados_snmp_json = json.dumps(dados_snmp)
        agora = datetime.now().isoformat()
        
        status = equipamento.get('status', 'N/A')
        if isinstance(status, int) or status == '1':
            status = 'N/A'
        
        if equipamento.get('id'):
            cursor.execute('''
                UPDATE equipamentos SET
                    nome=?, ip=?, porta=?, localidade=?,
                    modo_operacao=?, tipo=?, firmware=?, status=?, latencia=?,
                    ssh_enabled=?, ssh_usuario=?, ssh_senha=?, ssh_porta=?,
                    dados_snmp=?, ultima_atualizacao=?,
                    p2p_tipo=?, p2p_par=?
                WHERE id=?
            ''', (
                equipamento.get('nome', ''),
                equipamento.get('ip', ''),
                equipamento.get('porta', '80'),
                equipamento.get('localidade', ''),
                equipamento.get('modo_operacao', 'cliente'),
                equipamento.get('tipo', 'equipamento'),
                equipamento.get('firmware', 'ubiquiti'),
                status,
                equipamento.get('latencia', 0),
                1 if equipamento.get('ssh_enabled', True) else 0,
                equipamento.get('ssh_usuario', 'ubnt'),
                equipamento.get('ssh_senha', ''),
                equipamento.get('ssh_porta', 22),
                dados_snmp_json,
                agora,
                equipamento.get('p2p_tipo', ''),
                equipamento.get('p2p_par', ''),
                equipamento['id']
            ))
        else:
            cursor.execute('''
                INSERT INTO equipamentos (
                    nome, ip, porta, localidade, modo_operacao, tipo, firmware,
                    status, latencia, ssh_enabled, ssh_usuario, ssh_senha, ssh_porta,
                    dados_snmp, ultima_atualizacao, p2p_tipo, p2p_par
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                equipamento.get('nome', ''),
                equipamento.get('ip', ''),
                equipamento.get('porta', '80'),
                equipamento.get('localidade', ''),
                equipamento.get('modo_operacao', 'cliente'),
                equipamento.get('tipo', 'equipamento'),
                equipamento.get('firmware', 'ubiquiti'),
                status,
                equipamento.get('latencia', 0),
                1 if equipamento.get('ssh_enabled', True) else 0,
                equipamento.get('ssh_usuario', 'ubnt'),
                equipamento.get('ssh_senha', ''),
                equipamento.get('ssh_porta', 22),
                dados_snmp_json,
                agora,
                equipamento.get('p2p_tipo', ''),
                equipamento.get('p2p_par', '')
            ))
        
        novo_id = equipamento.get('id') or cursor.lastrowid
        conn.commit()
        conn.close()
        return True, novo_id
    
    def salvar_status_em_lote(self, estado_equipamentos, estado_clientes):
        conn = self.conectar()
        cursor = conn.cursor()
        agora = datetime.now().isoformat()
        
        for eq in self.listar_equipamentos():
            ip = eq.get('ip', '')
            if ip in estado_equipamentos:
                estado = estado_equipamentos[ip]
                status = "ONLINE" if estado.get("online") else "OFFLINE"
                latencia = estado.get("latencia", 0)
                
                cursor.execute('''
                    UPDATE equipamentos SET status=?, latencia=?, ultima_atualizacao=?
                    WHERE ip=?
                ''', (status, latencia, agora, ip))
        
        for cli in self.listar_clientes():
            ip = cli.get('ip', '')
            if ip in estado_clientes:
                estado = estado_clientes[ip]
                status = "ONLINE" if estado.get("online") else "OFFLINE"
                latencia = estado.get("latencia", 0)
                
                cursor.execute('''
                    UPDATE clientes SET status=?, latencia=?
                    WHERE ip=?
                ''', (status, latencia, ip))
        
        conn.commit()
        conn.close()
        print(f"Status salvo em lote: {len(estado_equipamentos)} equipamentos, {len(estado_clientes)} clientes")
    
    def excluir_equipamento(self, equipamento_id):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM equipamentos WHERE id = ?', (equipamento_id,))
        conn.commit()
        conn.close()
        return True
    
    # ========== LOCALIDADES ==========
    def listar_localidades(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT nome FROM localidades ORDER BY nome')
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    
    def salvar_localidade(self, nome):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO localidades (nome) VALUES (?)', (nome,))
        conn.commit()
        conn.close()
        return True
    
    def excluir_localidade(self, nome):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM localidades WHERE nome = ?', (nome,))
        conn.commit()
        conn.close()
        return True
    
    # ========== CLIENTES ==========
    def listar_clientes(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY id')
        rows = cursor.fetchall()
        conn.close()
        
        clientes = []
        for row in rows:
            clientes.append({
                'id': row['id'],
                'nome': row['nome'],
                'ip': row['ip'],
                'tipo': row['tipo'],
                'painel': row['painel'],
                'localidade': row['localidade'],
                'pon_id': row['pon_id'],
                'endereco': row['endereco'],
                'status': row['status'],
                'latencia': row['latencia']
            })
        return clientes
    
    def salvar_cliente(self, cliente):
        conn = self.conectar()
        cursor = conn.cursor()
        
        if cliente.get('id'):
            cursor.execute('''
                UPDATE clientes SET
                    nome=?, ip=?, tipo=?, painel=?,
                    localidade=?, pon_id=?, endereco=?,
                    status=?, latencia=?
                WHERE id=?
            ''', (
                cliente.get('nome', ''),
                cliente.get('ip', ''),
                cliente.get('tipo', 'radio'),
                cliente.get('painel', ''),
                cliente.get('localidade', ''),
                cliente.get('pon_id', ''),
                cliente.get('endereco', ''),
                cliente.get('status', 'N/A'),
                cliente.get('latencia', 0),
                cliente['id']
            ))
        else:
            cursor.execute('''
                INSERT INTO clientes (
                    nome, ip, tipo, painel, localidade,
                    pon_id, endereco, status, latencia
                ) VALUES (?,?,?,?,?,?,?,?,?)
            ''', (
                cliente.get('nome', ''),
                cliente.get('ip', ''),
                cliente.get('tipo', 'radio'),
                cliente.get('painel', ''),
                cliente.get('localidade', ''),
                cliente.get('pon_id', ''),
                cliente.get('endereco', ''),
                cliente.get('status', 'N/A'),
                cliente.get('latencia', 0)
            ))
        
        novo_id = cliente.get('id') or cursor.lastrowid
        conn.commit()
        conn.close()
        return True, novo_id
    
    def excluir_cliente(self, cliente_id):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
        conn.commit()
        conn.close()
        return True