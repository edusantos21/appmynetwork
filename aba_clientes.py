# aba_clientes.py - PADRAO CORRIGIDO
import customtkinter as ctk
from tkinter import messagebox, ttk
import threading

class AbaClientes:
    def __init__(self, parent, config, db, monitor, atualizar_callback):
        self.parent = parent
        self.config = config
        self.db = db
        self.monitor = monitor
        self.atualizar_callback = atualizar_callback
        self.clientes = db.listar_clientes()
        self.equipamentos = db.listar_equipamentos()
        self.localidades = db.listar_localidades()
        self.item_selecionado = None
        
        self.criar_aba()
        self.atualizar_lista()
    
    def criar_aba(self):
        self.container = ctk.CTkFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        tree_frame = ctk.CTkFrame(self.container)
        tree_frame.pack(fill="both", expand=True, pady=(10, 0))
        tree_frame.pack_propagate(False)

        btn_frame = ctk.CTkFrame(tree_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(btn_frame, text="+ Adicionar Cliente", command=self.adicionar, width=140).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Editar", command=self.editar, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Excluir", command=self.excluir, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Testar Ping", command=self.testar_ping, width=120).pack(side="left", padx=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=("nome", "ip", "tipo", "referencia", "endereco", "status", "latencia"), show="headings")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("ip", text="IP")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("referencia", text="Referencia")
        self.tree.heading("endereco", text="Endereco/Localidade")
        self.tree.heading("status", text="Status")
        self.tree.heading("latencia", text="Latencia (ms)")
        
        self.tree.column("nome", width=180)
        self.tree.column("ip", width=120)
        self.tree.column("tipo", width=80)
        self.tree.column("referencia", width=150)
        self.tree.column("endereco", width=200)
        self.tree.column("status", width=100)
        self.tree.column("latencia", width=100)
        
        scrollbar = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
    
    def on_select(self, event):
        selecionado = self.tree.selection()
        self.item_selecionado = selecionado[0] if selecionado else None
    
    def atualizar_lista(self):
        nome_selecionado = None
        if self.item_selecionado:
            try:
                valores = self.tree.item(self.item_selecionado, 'values')
                if valores:
                    nome_selecionado = valores[0]
            except:
                pass
    
        for item in self.tree.get_children():
            self.tree.delete(item)
    
        for cliente in self.clientes:
            self._inserir_linha(cliente, nome_selecionado)
    
    def _inserir_linha(self, cliente, nome_selecionado=None):
        status = cliente.get("status", "N/A")
        latencia_raw = cliente.get("latencia", 0)
        try:
            latencia = int(latencia_raw) if latencia_raw else 0
        except (ValueError, TypeError):
            latencia = 0
        latencia_str = f"{latencia}" if latencia > 0 else "-"
    
        tipo = cliente.get("tipo", "radio")
        if tipo == "radio":
            referencia = cliente.get("painel", "-")
            endereco = cliente.get("localidade", "-")
        else:
            referencia = cliente.get("pon_id", "-")
            endereco = cliente.get("endereco", "-")
    
        item_id = self.tree.insert("", "end", values=(
            cliente.get("nome", ""),
            cliente.get("ip", ""),
            "Radio" if tipo == "radio" else "Fibra",
            referencia,
            endereco,
            status,
            latencia_str
        ))
    
        if nome_selecionado and nome_selecionado == cliente.get("nome", ""):
            self.tree.selection_set(item_id)
            self.item_selecionado = item_id
    
    def _atualizar_linha(self, idx):
        cliente = self.clientes[idx]
        nome = cliente.get("nome", "")
        
        for item_id in self.tree.get_children():
            valores = self.tree.item(item_id, "values")
            if valores and valores[0] == nome:
                status = cliente.get("status", "N/A")
                latencia_str = f"{int(cliente.get('latencia', 0))}" if cliente.get('latencia', 0) > 0 else "-"
                tipo = cliente.get("tipo", "radio")
                
                self.tree.item(item_id, values=(
                    nome, cliente.get("ip", ""),
                    "Radio" if tipo == "radio" else "Fibra",
                    cliente.get("painel", "-") if tipo == "radio" else cliente.get("pon_id", "-"),
                    cliente.get("localidade", "-") if tipo == "radio" else cliente.get("endereco", "-"),
                    status, latencia_str
                ))
                break
    
    def adicionar(self):
        self.localidades = self.db.listar_localidades()
        self.equipamentos = self.db.listar_equipamentos()
        
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Adicionar Cliente")
        dialog.geometry("550x550")
        dialog.minsize(550, 500)
        dialog.transient(self.parent)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (300)
        dialog.geometry(f"550x600+{x}+{y}")
        
        main_frame = ctk.CTkScrollableFrame(dialog, width=520, height=530)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(main_frame, text="Dados do Cliente", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        
        ctk.CTkLabel(main_frame, text="Nome:").pack(anchor="w", pady=(10, 0))
        entry_nome = ctk.CTkEntry(main_frame, width=450)
        entry_nome.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(main_frame, text="IP:").pack(anchor="w", pady=(10, 0))
        entry_ip = ctk.CTkEntry(main_frame, width=450)
        entry_ip.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(main_frame, text="Tipo de Conexao:", font=("Arial", 13, "bold")).pack(anchor="w", pady=(15, 5))
        
        tipo_var = ctk.StringVar(value="radio")
        ctk.CTkRadioButton(main_frame, text="Radio", variable=tipo_var, value="radio").pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(main_frame, text="Fibra", variable=tipo_var, value="fibra").pack(anchor="w", padx=20, pady=5)
        
        frame_radio = ctk.CTkFrame(main_frame)
        ctk.CTkLabel(frame_radio, text="Configuracoes de Radio", font=("Arial", 13, "bold")).pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(frame_radio, text="Painel (Equipamento):").pack(anchor="w", pady=(10, 0))
        
        nomes_equipamentos = [e.get("nome", "") for e in self.equipamentos if e.get("nome")]
        if not nomes_equipamentos:
            nomes_equipamentos = ["Nenhum equipamento cadastrado"]
        
        combo_painel = ctk.CTkComboBox(frame_radio, values=nomes_equipamentos, width=450)
        combo_painel.pack(anchor="w", pady=5)
        if nomes_equipamentos:
            combo_painel.set(nomes_equipamentos[0] if nomes_equipamentos[0] != "Nenhum equipamento cadastrado" else "")
        
        ctk.CTkLabel(frame_radio, text="Localidade:").pack(anchor="w", pady=(10, 0))
        
        localidades_lista = self.localidades.copy() if self.localidades else []
        if not localidades_lista:
            localidades_lista = ["Nenhuma localidade cadastrada"]
        
        combo_local = ctk.CTkComboBox(frame_radio, values=localidades_lista, width=450)
        combo_local.pack(anchor="w", pady=5)
        if localidades_lista and localidades_lista[0] != "Nenhuma localidade cadastrada":
            combo_local.set(localidades_lista[0])
        
        frame_fibra = ctk.CTkFrame(main_frame)
        ctk.CTkLabel(frame_fibra, text="Configuracoes de Fibra", font=("Arial", 13, "bold")).pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(frame_fibra, text="PON/ID:").pack(anchor="w", pady=(10, 0))
        entry_pon = ctk.CTkEntry(frame_fibra, width=450)
        entry_pon.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(frame_fibra, text="Endereco:").pack(anchor="w", pady=(10, 0))
        entry_endereco = ctk.CTkEntry(frame_fibra, width=450)
        entry_endereco.pack(anchor="w", pady=5)
        
        def on_tipo_change(*args):
            if tipo_var.get() == "radio":
                frame_radio.pack(fill="x", pady=10)
                frame_fibra.pack_forget()
            else:
                frame_radio.pack_forget()
                frame_fibra.pack(fill="x", pady=10)
        
        tipo_var.trace("w", on_tipo_change)
        on_tipo_change()
        
        lbl_status = ctk.CTkLabel(main_frame, text="", font=("Arial", 11))
        lbl_status.pack(anchor="w", pady=5)
        
        def salvar():
            nome = entry_nome.get().strip()
            ip = entry_ip.get().strip()
            
            if not nome or not ip:
                messagebox.showwarning("Aviso", "Preencha Nome e IP!")
                return
            
            tipo = tipo_var.get()
            
            if tipo == "radio":
                painel = combo_painel.get()
                localidade = combo_local.get()
                
                if painel == "Nenhum equipamento cadastrado":
                    painel = ""
                if localidade == "Nenhuma localidade cadastrada":
                    localidade = ""
                
                cliente = {
                    "nome": nome, "ip": ip, "tipo": tipo,
                    "painel": painel, "localidade": localidade,
                    "pon_id": "", "endereco": "",
                    "status": "N/A", "latencia": 0
                }
            else:
                pon_id = entry_pon.get().strip()
                endereco = entry_endereco.get().strip()
                cliente = {
                    "nome": nome, "ip": ip, "tipo": tipo,
                    "painel": "", "localidade": "",
                    "pon_id": pon_id, "endereco": endereco,
                    "status": "N/A", "latencia": 0
                }
            
            lbl_status.configure(text="Salvando...", text_color="orange")
            
            def salvar_db():
                try:
                    sucesso, cliente_id = self.db.salvar_cliente(cliente)
                    if sucesso and cliente_id:
                        cliente["id"] = cliente_id
                    
                    self.clientes.append(cliente)
                    self.monitor.atualizar_configuracoes(
                        self.db.listar_equipamentos(),
                        self.config.get_configuracoes(),
                        self.clientes
                    )
                    
                    lbl_status.after(0, lambda: lbl_status.configure(text="Salvo!", text_color="green"))
                    self.atualizar_lista()
                    dialog.after(0, dialog.destroy)
                except Exception as e:
                    erro_msg = str(e)
                    lbl_status.after(0, lambda msg=erro_msg: lbl_status.configure(text=f"Erro: {msg}", text_color="red"))
            
            threading.Thread(target=salvar_db, daemon=True).start()
        
        ctk.CTkButton(main_frame, text="Salvar", command=salvar, width=200).pack(pady=20)
    
    def editar(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um cliente")
            return
        
        self.localidades = self.db.listar_localidades()
        self.equipamentos = self.db.listar_equipamentos()
        
        try:
            valores = self.tree.item(self.item_selecionado, 'values')
            if not valores:
                return
        except:
            self.item_selecionado = None
            return
        
        nome_cliente = valores[0]
        idx = next((i for i, cli in enumerate(self.clientes) if cli.get("nome") == nome_cliente), None)
        
        if idx is None:
            return
        
        cliente = self.clientes[idx]
        
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Editar Cliente")
        dialog.geometry("550x550")
        dialog.minsize(550, 500)
        dialog.transient(self.parent)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (300)
        dialog.geometry(f"550x600+{x}+{y}")
        
        main_frame = ctk.CTkScrollableFrame(dialog, width=520, height=530)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(main_frame, text="Dados do Cliente", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        
        ctk.CTkLabel(main_frame, text="Nome:").pack(anchor="w", pady=(10, 0))
        entry_nome = ctk.CTkEntry(main_frame, width=450)
        entry_nome.insert(0, cliente.get("nome", ""))
        entry_nome.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(main_frame, text="IP:").pack(anchor="w", pady=(10, 0))
        entry_ip = ctk.CTkEntry(main_frame, width=450)
        entry_ip.insert(0, cliente.get("ip", ""))
        entry_ip.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(main_frame, text="Tipo de Conexao:", font=("Arial", 13, "bold")).pack(anchor="w", pady=(15, 5))
        
        tipo_var = ctk.StringVar(value=cliente.get("tipo", "radio"))
        ctk.CTkRadioButton(main_frame, text="Radio", variable=tipo_var, value="radio").pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(main_frame, text="Fibra", variable=tipo_var, value="fibra").pack(anchor="w", padx=20, pady=5)
        
        frame_radio = ctk.CTkFrame(main_frame)
        ctk.CTkLabel(frame_radio, text="Configuracoes de Radio", font=("Arial", 13, "bold")).pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(frame_radio, text="Painel (Equipamento):").pack(anchor="w", pady=(10, 0))
        
        nomes_equipamentos = [e.get("nome", "") for e in self.equipamentos if e.get("nome")]
        if not nomes_equipamentos:
            nomes_equipamentos = ["Nenhum equipamento cadastrado"]
        
        combo_painel = ctk.CTkComboBox(frame_radio, values=nomes_equipamentos, width=450)
        combo_painel.set(cliente.get("painel", ""))
        combo_painel.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(frame_radio, text="Localidade:").pack(anchor="w", pady=(10, 0))
        
        localidades_lista = self.localidades.copy() if self.localidades else []
        if not localidades_lista:
            localidades_lista = ["Nenhuma localidade cadastrada"]
        
        combo_local = ctk.CTkComboBox(frame_radio, values=localidades_lista, width=450)
        combo_local.set(cliente.get("localidade", ""))
        combo_local.pack(anchor="w", pady=5)
        
        frame_fibra = ctk.CTkFrame(main_frame)
        ctk.CTkLabel(frame_fibra, text="Configuracoes de Fibra", font=("Arial", 13, "bold")).pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(frame_fibra, text="PON/ID:").pack(anchor="w", pady=(10, 0))
        entry_pon = ctk.CTkEntry(frame_fibra, width=450)
        entry_pon.insert(0, cliente.get("pon_id", ""))
        entry_pon.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(frame_fibra, text="Endereco:").pack(anchor="w", pady=(10, 0))
        entry_endereco = ctk.CTkEntry(frame_fibra, width=450)
        entry_endereco.insert(0, cliente.get("endereco", ""))
        entry_endereco.pack(anchor="w", pady=5)
        
        def on_tipo_change(*args):
            if tipo_var.get() == "radio":
                frame_radio.pack(fill="x", pady=10)
                frame_fibra.pack_forget()
            else:
                frame_radio.pack_forget()
                frame_fibra.pack(fill="x", pady=10)
        
        tipo_var.trace("w", on_tipo_change)
        on_tipo_change()
        
        lbl_status = ctk.CTkLabel(main_frame, text="", font=("Arial", 11))
        lbl_status.pack(anchor="w", pady=5)
        
        def salvar():
            cliente["nome"] = entry_nome.get().strip()
            cliente["ip"] = entry_ip.get().strip()
            cliente["tipo"] = tipo_var.get()
            
            if cliente["tipo"] == "radio":
                painel = combo_painel.get()
                localidade = combo_local.get()
                cliente["painel"] = "" if painel == "Nenhum equipamento cadastrado" else painel
                cliente["localidade"] = "" if localidade == "Nenhuma localidade cadastrada" else localidade
                cliente["pon_id"] = ""
                cliente["endereco"] = ""
            else:
                cliente["painel"] = ""
                cliente["localidade"] = ""
                cliente["pon_id"] = entry_pon.get().strip()
                cliente["endereco"] = entry_endereco.get().strip()
            
            lbl_status.configure(text="Salvando...", text_color="orange")
            
            def salvar_db():
                try:
                    self.db.salvar_cliente(cliente)
                    self.monitor.atualizar_configuracoes(
                        self.db.listar_equipamentos(),
                        self.config.get_configuracoes(),
                        self.clientes
                    )
                    lbl_status.after(0, lambda: lbl_status.configure(text="Salvo!", text_color="green"))
                    self._atualizar_linha(idx)
                    dialog.after(0, dialog.destroy)
                except Exception as e:
                    erro_msg = str(e)
                    lbl_status.after(0, lambda msg=erro_msg: lbl_status.configure(text=f"Erro: {msg}", text_color="red"))
            
            threading.Thread(target=salvar_db, daemon=True).start()
        
        ctk.CTkButton(main_frame, text="Salvar", command=salvar, width=200).pack(pady=20)
    
    def excluir(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um cliente")
            return
        
        try:
            valores = self.tree.item(self.item_selecionado, 'values')
            if not valores:
                return
        except:
            self.item_selecionado = None
            return
        
        nome_cliente = valores[0]
        
        if messagebox.askyesno("Confirmar", f"Excluir cliente '{nome_cliente}'?"):
            idx = next((i for i, cli in enumerate(self.clientes) if cli.get("nome") == nome_cliente), None)
            
            if idx is not None:
                cliente_id = self.clientes[idx].get("id")
                
                def excluir_db():
                    try:
                        if cliente_id:
                            self.db.excluir_cliente(cliente_id)
                        del self.clientes[idx]
                        self.monitor.atualizar_configuracoes(
                            self.db.listar_equipamentos(),
                            self.config.get_configuracoes(),
                            self.clientes
                        )
                        self.atualizar_lista()
                    except Exception as e:
                        erro_msg = str(e)
                        messagebox.showerror("Erro", f"Erro ao excluir: {erro_msg}")
                
                threading.Thread(target=excluir_db, daemon=True).start()
    
    def testar_ping(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um cliente")
            return
        
        try:
            valores = self.tree.item(self.item_selecionado, 'values')
            if not valores:
                return
        except:
            self.item_selecionado = None
            return
        
        ip_cliente = valores[1]
        
        if not ip_cliente or ip_cliente == "-":
            messagebox.showwarning("Aviso", "Cliente sem IP configurado!")
            return
        
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Teste de Ping")
        dialog.geometry("400x200")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (200)
        y = (dialog.winfo_screenheight() // 2) - (100)
        dialog.geometry(f"400x200+{x}+{y}")
        
        lbl_resultado = ctk.CTkLabel(dialog, text=f"Testando {ip_cliente}...", font=("Arial", 18, "bold"))
        lbl_resultado.pack(pady=40)
        
        def executar_ping():
            latencia, status = self.monitor.testar_ping_unico(ip_cliente)
            if "ONLINE" in status:
                lbl_resultado.after(0, lambda: lbl_resultado.configure(
                    text=f"ONLINE - {latencia}ms", text_color="green"))
            else:
                lbl_resultado.after(0, lambda: lbl_resultado.configure(
                    text=f"OFFLINE", text_color="red"))
        
        threading.Thread(target=executar_ping, daemon=True).start()
        ctk.CTkButton(dialog, text="Fechar", command=dialog.destroy, width=100).pack(pady=20)