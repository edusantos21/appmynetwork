# aba_equipamentos.py - PADRAO CORRIGIDO
import customtkinter as ctk
from tkinter import messagebox, ttk
import threading


class AbaEquipamentos:
    def __init__(self, parent, config, db, monitor, ssh_manager, atualizar_callback):
        self.parent = parent
        self.config = config
        self.db = db
        self.monitor = monitor
        self.ssh_manager = ssh_manager
        self.atualizar_callback = atualizar_callback
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

        ctk.CTkButton(btn_frame, text="+ Adicionar", command=self.adicionar, width=120).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Editar", command=self.editar, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Excluir", command=self.excluir, width=100).pack(side="left", padx=5)

        self.tree = ttk.Treeview(tree_frame, columns=("nome", "ip", "porta", "localidade", "modo", "p2p_info", "status", "latencia", "mac", "ssh", "clientes", "ssid"), show="headings")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("ip", text="IP")
        self.tree.heading("porta", text="Porta")
        self.tree.heading("localidade", text="Localidade")
        self.tree.heading("modo", text="Modo")
        self.tree.heading("p2p_info", text="P2P")
        self.tree.heading("status", text="Status")
        self.tree.heading("latencia", text="Latencia (ms)")
        self.tree.heading("mac", text="MAC")
        self.tree.heading("ssh", text="SSH")
        self.tree.heading("clientes", text="Clientes")
        self.tree.heading("ssid", text="SSID")

        self.tree.column("nome", width=120)
        self.tree.column("ip", width=100)
        self.tree.column("porta", width=50)
        self.tree.column("localidade", width=100)
        self.tree.column("modo", width=80)
        self.tree.column("p2p_info", width=150)
        self.tree.column("status", width=80)
        self.tree.column("latencia", width=80)
        self.tree.column("mac", width=130)
        self.tree.column("ssh", width=50)
        self.tree.column("clientes", width=60)
        self.tree.column("ssid", width=120)

        scrollbar = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def on_select(self, event):
        selecionado = self.tree.selection()
        self.item_selecionado = selecionado[0] if selecionado else None

    def atualizar_lista(self):
        nome_selecionado = None
        if self.item_selecionado:
            try:
                valores = self.tree.item(self.item_selecionado, "values")
                if valores:
                    nome_selecionado = valores[0]
            except:
                pass

        for item in self.tree.get_children():
            self.tree.delete(item)

        for eq in self.equipamentos:
            self._inserir_linha(eq, nome_selecionado)

    def _inserir_linha(self, eq, nome_selecionado=None):
        status = eq.get("status", "N/A")
        latencia_raw = eq.get("latencia", 0)
        try:
            latencia = float(latencia_raw) if latencia_raw else 0
        except (ValueError, TypeError):
            latencia = 0
        latencia_str = f"{int(latencia)}" if latencia > 0 else "-"

        dados_snmp = eq.get("dados_snmp", {})
        if not isinstance(dados_snmp, dict):
            dados_snmp = {}
        
        mac = dados_snmp.get("mac", "") or eq.get("mac", "")
        ssh_status = "Sim" if eq.get("ssh_enabled", False) else "Nao"

        clientes_raw = dados_snmp.get("clientes", 0) if isinstance(dados_snmp, dict) else 0
        try:
            clientes = int(clientes_raw) if clientes_raw else 0
        except (ValueError, TypeError):
            clientes = 0

        ssid = dados_snmp.get("ssid", "") if isinstance(dados_snmp, dict) else ""
        modo = eq.get("modo_operacao", "cliente")
        modo_display = "P2P" if modo == "p2p" else "Cliente"
        
        p2p_info = "-"
        if modo == "p2p":
            p2p_tipo = eq.get("p2p_tipo", "")
            p2p_par = eq.get("p2p_par", "")
            if p2p_tipo == "ap":
                p2p_info = f"AP -> {p2p_par}" if p2p_par else "AP"
            elif p2p_tipo == "station":
                p2p_info = f"Station <- {p2p_par}" if p2p_par else "Station"
            else:
                p2p_info = "Configurar"

        valores = (
            eq.get("nome", ""), eq.get("ip", ""), eq.get("porta", ""),
            eq.get("localidade", ""), modo_display, p2p_info,
            status, latencia_str, mac.upper() if mac else "-",
            ssh_status, clientes, ssid[:20] if ssid else "-",
        )

        item_id = self.tree.insert("", "end", values=valores)

        if nome_selecionado and nome_selecionado == eq.get("nome", ""):
            self.tree.selection_set(item_id)
            self.item_selecionado = item_id

    def _atualizar_linha(self, idx):
        eq = self.equipamentos[idx]
        nome = eq.get("nome", "")
        
        for item_id in self.tree.get_children():
            valores = self.tree.item(item_id, "values")
            if valores and valores[0] == nome:
                status = eq.get("status", "N/A")
                latencia_str = f"{int(eq.get('latencia', 0))}" if eq.get('latencia', 0) > 0 else "-"
                modo_display = "P2P" if eq.get("modo_operacao") == "p2p" else "Cliente"
                mac = eq.get("dados_snmp", {}).get("mac", "") or eq.get("mac", "")
                ssh_status = "Sim" if eq.get("ssh_enabled", False) else "Nao"
                clientes = eq.get("dados_snmp", {}).get("clientes", 0)
                ssid = eq.get("dados_snmp", {}).get("ssid", "-")[:20]
                
                self.tree.item(item_id, values=(
                    nome, eq.get("ip", ""), eq.get("porta", ""),
                    eq.get("localidade", ""), modo_display, "-",
                    status, latencia_str, mac.upper() if mac else "-",
                    ssh_status, clientes, ssid if ssid else "-",
                ))
                break

    def _get_p2p_pares_disponiveis(self, p2p_tipo, equipamento_atual=None):
        todos = self.db.listar_equipamentos()
        tipo_oposto = "station" if p2p_tipo == "ap" else "ap" if p2p_tipo == "station" else None
        if not tipo_oposto:
            return []
        pares = []
        for eq in todos:
            if equipamento_atual and eq.get("nome") == equipamento_atual.get("nome"):
                continue
            if eq.get("modo_operacao") == "p2p" and eq.get("p2p_tipo") == tipo_oposto:
                pares.append(eq.get("nome", ""))
        return pares if pares else ["Nenhum equipamento compativel"]

    def _criar_frame_p2p(self, parent, equipamento=None):
        frame_p2p = ctk.CTkFrame(parent)
        ctk.CTkLabel(frame_p2p, text="Configuracoes P2P", font=("Arial", 14, "bold")).pack(anchor="w", pady=(5, 10))
        ctk.CTkLabel(frame_p2p, text="Tipo do Link:").pack(anchor="w", pady=(5, 0))
        
        p2p_tipo_var = ctk.StringVar(value=equipamento.get("p2p_tipo", "ap") if equipamento else "ap")
        frame_tipo = ctk.CTkFrame(frame_p2p)
        frame_tipo.pack(anchor="w", pady=5)
        ctk.CTkRadioButton(frame_tipo, text="AP", variable=p2p_tipo_var, value="ap").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(frame_tipo, text="Station", variable=p2p_tipo_var, value="station").pack(side="left")
        
        ctk.CTkLabel(frame_p2p, text="Conectado ao equipamento:").pack(anchor="w", pady=(15, 0))
        
        def atualizar_combo(*args):
            pares = self._get_p2p_pares_disponiveis(p2p_tipo_var.get(), equipamento)
            combo_p2p_par.configure(values=pares)
            if pares and pares[0] != "Nenhum equipamento compativel":
                combo_p2p_par.set(equipamento.get("p2p_par") if equipamento and equipamento.get("p2p_par") in pares else pares[0])
            else:
                combo_p2p_par.set("")
        
        p2p_tipo_var.trace("w", atualizar_combo)
        pares_iniciais = self._get_p2p_pares_disponiveis(p2p_tipo_var.get(), equipamento)
        combo_p2p_par = ctk.CTkComboBox(frame_p2p, values=pares_iniciais, width=400)
        combo_p2p_par.pack(anchor="w", pady=5)
        if equipamento and equipamento.get("p2p_par") in pares_iniciais:
            combo_p2p_par.set(equipamento.get("p2p_par"))
        
        return frame_p2p, p2p_tipo_var, combo_p2p_par

    def adicionar(self):
        self.localidades = self.db.listar_localidades()
        
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Adicionar Equipamento")
        dialog.geometry("550x650")
        dialog.minsize(550, 500)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (325)
        dialog.geometry(f"550x650+{x}+{y}")

        main_frame = ctk.CTkScrollableFrame(dialog, width=520, height=580)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main_frame, text="Dados do Equipamento", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        ctk.CTkLabel(main_frame, text="Nome:").pack(anchor="w", pady=(10, 0))
        entry_nome = ctk.CTkEntry(main_frame, width=450)
        entry_nome.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="IP:").pack(anchor="w", pady=(10, 0))
        entry_ip = ctk.CTkEntry(main_frame, width=450)
        entry_ip.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Porta HTTP:").pack(anchor="w", pady=(10, 0))
        entry_porta = ctk.CTkEntry(main_frame, width=200)
        entry_porta.insert(0, "80")
        entry_porta.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Localidade:").pack(anchor="w", pady=(10, 0))
        localidades_lista = self.localidades.copy() if self.localidades else ["Nenhuma localidade cadastrada"]
        combo_local = ctk.CTkComboBox(main_frame, values=localidades_lista, width=450)
        combo_local.pack(anchor="w", pady=5)
        if localidades_lista[0] != "Nenhuma localidade cadastrada":
            combo_local.set(localidades_lista[0])

        ctk.CTkLabel(main_frame, text="Modo de Operacao", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        modo_var = ctk.StringVar(value="cliente")
        ctk.CTkRadioButton(main_frame, text="Painel de Clientes", variable=modo_var, value="cliente").pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(main_frame, text="Ponto-a-Ponto", variable=modo_var, value="p2p").pack(anchor="w", padx=20, pady=5)
        
        frame_p2p_container = ctk.CTkFrame(main_frame)
        frame_p2p, p2p_tipo_var, combo_p2p_par = self._criar_frame_p2p(frame_p2p_container)
        frame_p2p.pack(fill="x", pady=10)
        
        def on_modo_change(*args):
            if modo_var.get() == "p2p":
                frame_p2p_container.pack(fill="x", pady=10)
            else:
                frame_p2p_container.pack_forget()
        modo_var.trace("w", on_modo_change)
        on_modo_change()

        ctk.CTkLabel(main_frame, text="Configuracoes SSH", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        ssh_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(main_frame, text="Habilitar coleta SSH", variable=ssh_var).pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Usuario SSH:").pack(anchor="w", pady=(10, 0))
        entry_ssh_user = ctk.CTkEntry(main_frame, width=450)
        entry_ssh_user.insert(0, "ubnt")
        entry_ssh_user.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Senha SSH:").pack(anchor="w", pady=(10, 0))
        entry_ssh_pass = ctk.CTkEntry(main_frame, width=450, show="*")
        entry_ssh_pass.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Porta SSH:").pack(anchor="w", pady=(10, 0))
        entry_ssh_port = ctk.CTkEntry(main_frame, width=200)
        entry_ssh_port.insert(0, "22")
        entry_ssh_port.pack(anchor="w", pady=5)

        lbl_status = ctk.CTkLabel(main_frame, text="", font=("Arial", 11))
        lbl_status.pack(anchor="w", pady=5)

        def salvar():
            nome = entry_nome.get().strip()
            ip = entry_ip.get().strip()
            if not nome or not ip:
                messagebox.showwarning("Aviso", "Preencha Nome e IP!")
                return
            
            localidade = combo_local.get()
            if localidade == "Nenhuma localidade cadastrada":
                localidade = ""
            
            equipamento = {
                "nome": nome, "ip": ip, "porta": entry_porta.get().strip() or "80",
                "localidade": localidade, "modo_operacao": modo_var.get(),
                "tipo": "equipamento", "status": "N/A", "latencia": 0,
                "ssh_enabled": ssh_var.get(), "ssh_usuario": entry_ssh_user.get().strip() or "ubnt",
                "ssh_senha": entry_ssh_pass.get(),
                "ssh_porta": int(entry_ssh_port.get()) if entry_ssh_port.get().isdigit() else 22,
                "dados_snmp": {},
            }
            if modo_var.get() == "p2p":
                equipamento["p2p_tipo"] = p2p_tipo_var.get()
                par = combo_p2p_par.get()
                equipamento["p2p_par"] = par if par and par != "Nenhum equipamento compativel" else ""
            else:
                equipamento["p2p_tipo"] = ""
                equipamento["p2p_par"] = ""

            lbl_status.configure(text="Salvando...", text_color="orange")

            def salvar_db():
                try:
                    sucesso, eq_id = self.db.salvar_equipamento(equipamento)
                    if sucesso:
                        equipamento["id"] = eq_id
                        self.equipamentos.append(equipamento)
                    
                    self.monitor.atualizar_configuracoes(self.equipamentos, self.config.get_configuracoes(), self.config.get_clientes())
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
            messagebox.showwarning("Aviso", "Selecione um equipamento")
            return

        try:
            valores = self.tree.item(self.item_selecionado, "values")
            if not valores:
                return
        except:
            self.item_selecionado = None
            return

        nome_equip = valores[0]
        idx = next((i for i, eq in enumerate(self.equipamentos) if eq.get("nome") == nome_equip), None)
        if idx is None:
            return

        eq = self.equipamentos[idx]
        self.localidades = self.db.listar_localidades()

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Editar Equipamento")
        dialog.geometry("550x650")
        dialog.minsize(550, 500)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (275)
        y = (dialog.winfo_screenheight() // 2) - (325)
        dialog.geometry(f"550x650+{x}+{y}")

        main_frame = ctk.CTkScrollableFrame(dialog, width=520, height=580)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main_frame, text="Dados do Equipamento", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        ctk.CTkLabel(main_frame, text="Nome:").pack(anchor="w", pady=(10, 0))
        entry_nome = ctk.CTkEntry(main_frame, width=450)
        entry_nome.insert(0, eq.get("nome", ""))
        entry_nome.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="IP:").pack(anchor="w", pady=(10, 0))
        entry_ip = ctk.CTkEntry(main_frame, width=450)
        entry_ip.insert(0, eq.get("ip", ""))
        entry_ip.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Porta HTTP:").pack(anchor="w", pady=(10, 0))
        entry_porta = ctk.CTkEntry(main_frame, width=200)
        entry_porta.insert(0, eq.get("porta", "80"))
        entry_porta.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Localidade:").pack(anchor="w", pady=(10, 0))
        localidades_lista = self.localidades.copy() if self.localidades else ["Nenhuma localidade cadastrada"]
        combo_local = ctk.CTkComboBox(main_frame, values=localidades_lista, width=450)
        combo_local.set(eq.get("localidade", ""))
        combo_local.pack(anchor="w", pady=5)

        ctk.CTkLabel(main_frame, text="Modo de Operacao", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        modo_var = ctk.StringVar(value=eq.get("modo_operacao", "cliente"))
        ctk.CTkRadioButton(main_frame, text="Painel de Clientes", variable=modo_var, value="cliente").pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(main_frame, text="Ponto-a-Ponto", variable=modo_var, value="p2p").pack(anchor="w", padx=20, pady=5)
        
        frame_p2p_container = ctk.CTkFrame(main_frame)
        frame_p2p, p2p_tipo_var, combo_p2p_par = self._criar_frame_p2p(frame_p2p_container, eq)
        frame_p2p.pack(fill="x", pady=10)
        
        def on_modo_change(*args):
            if modo_var.get() == "p2p":
                frame_p2p_container.pack(fill="x", pady=10)
            else:
                frame_p2p_container.pack_forget()
        modo_var.trace("w", on_modo_change)
        on_modo_change()

        ctk.CTkLabel(main_frame, text="Configuracoes SSH", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        ssh_var = ctk.BooleanVar(value=eq.get("ssh_enabled", True))
        ctk.CTkCheckBox(main_frame, text="Habilitar coleta SSH", variable=ssh_var).pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Usuario SSH:").pack(anchor="w", pady=(10, 0))
        entry_ssh_user = ctk.CTkEntry(main_frame, width=450)
        entry_ssh_user.insert(0, eq.get("ssh_usuario", "ubnt"))
        entry_ssh_user.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Senha SSH:").pack(anchor="w", pady=(10, 0))
        entry_ssh_pass = ctk.CTkEntry(main_frame, width=450, show="*")
        entry_ssh_pass.insert(0, eq.get("ssh_senha", ""))
        entry_ssh_pass.pack(anchor="w", pady=5)
        ctk.CTkLabel(main_frame, text="Porta SSH:").pack(anchor="w", pady=(10, 0))
        entry_ssh_port = ctk.CTkEntry(main_frame, width=200)
        entry_ssh_port.insert(0, str(eq.get("ssh_porta", 22)))
        entry_ssh_port.pack(anchor="w", pady=5)

        lbl_status = ctk.CTkLabel(main_frame, text="", font=("Arial", 11))
        lbl_status.pack(anchor="w", pady=5)

        def salvar():
            eq["nome"] = entry_nome.get().strip()
            eq["ip"] = entry_ip.get().strip()
            eq["porta"] = entry_porta.get().strip() or "80"
            localidade = combo_local.get()
            eq["localidade"] = "" if localidade == "Nenhuma localidade cadastrada" else localidade
            eq["modo_operacao"] = modo_var.get()
            eq["ssh_enabled"] = ssh_var.get()
            eq["ssh_usuario"] = entry_ssh_user.get().strip() or "ubnt"
            eq["ssh_senha"] = entry_ssh_pass.get()
            eq["ssh_porta"] = int(entry_ssh_port.get()) if entry_ssh_port.get().isdigit() else 22
            
            if modo_var.get() == "p2p":
                eq["p2p_tipo"] = p2p_tipo_var.get()
                par = combo_p2p_par.get()
                eq["p2p_par"] = par if par and par != "Nenhum equipamento compativel" else ""
            else:
                eq["p2p_tipo"] = ""
                eq["p2p_par"] = ""

            lbl_status.configure(text="Salvando...", text_color="orange")

            def salvar_db():
                try:
                    self.db.salvar_equipamento(eq)
                    self.monitor.atualizar_configuracoes(self.equipamentos, self.config.get_configuracoes(), self.config.get_clientes())
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
            messagebox.showwarning("Aviso", "Selecione um equipamento")
            return

        try:
            valores = self.tree.item(self.item_selecionado, "values")
            if not valores:
                return
        except:
            self.item_selecionado = None
            return

        nome_equip = valores[0]
        idx = next((i for i, eq in enumerate(self.equipamentos) if eq.get("nome") == nome_equip), None)
        if idx is None:
            return

        if messagebox.askyesno("Confirmar", f"Excluir equipamento '{nome_equip}'?"):
            eq_id = self.equipamentos[idx].get("id")

            def excluir_db():
                try:
                    if eq_id:
                        self.db.excluir_equipamento(eq_id)
                    del self.equipamentos[idx]
                    self.monitor.atualizar_configuracoes(self.equipamentos, self.config.get_configuracoes(), self.config.get_clientes())
                    self.atualizar_lista()
                except Exception as e:
                    erro_msg = str(e)
                    messagebox.showerror("Erro", f"Erro ao excluir: {erro_msg}")

            threading.Thread(target=excluir_db, daemon=True).start()