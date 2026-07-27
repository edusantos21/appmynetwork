# aba_servidores.py - PADRAO CORRIGIDO
import customtkinter as ctk
from tkinter import messagebox, ttk
import threading


class AbaServidores:
    def __init__(self, parent, config, db, monitor, atualizar_callback):
        self.parent = parent
        self.config = config
        self.db = db
        self.monitor = monitor
        self.atualizar_callback = atualizar_callback
        self.servidores = db.listar_por_tipo("servidor")
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

        self.tree = ttk.Treeview(tree_frame, columns=("nome", "ip", "status", "latencia", "localidade"), show="headings")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("ip", text="IP")
        self.tree.heading("status", text="Status")
        self.tree.heading("latencia", text="Latencia (ms)")
        self.tree.heading("localidade", text="Localidade")

        self.tree.column("nome", width=200)
        self.tree.column("ip", width=150)
        self.tree.column("status", width=100)
        self.tree.column("latencia", width=100)
        self.tree.column("localidade", width=150)

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

        for srv in self.servidores:
            status = srv.get("status", "N/A")
            latencia_raw = srv.get("latencia", 0)
            try:
                latencia = float(latencia_raw) if latencia_raw else 0
            except:
                latencia = 0
            latencia_str = f"{int(latencia)}" if latencia > 0 else "-"

            item_id = self.tree.insert("", "end", values=(
                srv.get("nome", ""), srv.get("ip", ""),
                status, latencia_str, srv.get("localidade", "")
            ))

            if nome_selecionado and nome_selecionado == srv.get("nome", ""):
                self.tree.selection_set(item_id)
                self.item_selecionado = item_id

    def _atualizar_linha(self, idx):
        srv = self.servidores[idx]
        nome = srv.get("nome", "")
        for item_id in self.tree.get_children():
            valores = self.tree.item(item_id, "values")
            if valores and valores[0] == nome:
                status = srv.get("status", "N/A")
                latencia_str = f"{int(srv.get('latencia', 0))}" if srv.get('latencia', 0) > 0 else "-"
                self.tree.item(item_id, values=(nome, srv.get("ip", ""), status, latencia_str, srv.get("localidade", "")))
                break

    def adicionar(self):
        self.localidades = self.db.listar_localidades()
        
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Adicionar Servidor")
        dialog.geometry("450x350")
        dialog.minsize(400, 300)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (225)
        y = (dialog.winfo_screenheight() // 2) - (175)
        dialog.geometry(f"450x350+{x}+{y}")

        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(main_frame, text="Nome:").pack(anchor="w", pady=(5, 0))
        entry_nome = ctk.CTkEntry(main_frame, width=380)
        entry_nome.pack(anchor="w", pady=5)

        ctk.CTkLabel(main_frame, text="IP:").pack(anchor="w", pady=(10, 0))
        entry_ip = ctk.CTkEntry(main_frame, width=380)
        entry_ip.pack(anchor="w", pady=5)

        ctk.CTkLabel(main_frame, text="Localidade:").pack(anchor="w", pady=(10, 0))
        localidades_lista = self.localidades.copy() if self.localidades else ["Nenhuma localidade cadastrada"]
        combo_local = ctk.CTkComboBox(main_frame, values=localidades_lista, width=380)
        combo_local.pack(anchor="w", pady=5)
        if localidades_lista[0] != "Nenhuma localidade cadastrada":
            combo_local.set(localidades_lista[0])

        lbl_status = ctk.CTkLabel(main_frame, text="", font=("Arial", 10))
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

            servidor = {
                "nome": nome, "ip": ip, "localidade": localidade,
                "tipo": "servidor", "modo_operacao": "cliente",
                "porta": "80", "status": "N/A", "latencia": 0,
                "ssh_enabled": False, "ssh_usuario": "", "ssh_senha": "", "ssh_porta": 22,
                "dados_snmp": {}, "p2p_tipo": "", "p2p_par": ""
            }

            lbl_status.configure(text="Salvando...", text_color="orange")

            def salvar_db():
                try:
                    sucesso, srv_id = self.db.salvar_equipamento(servidor)
                    if sucesso:
                        servidor["id"] = srv_id
                        self.servidores.append(servidor)
                    self.monitor.atualizar_configuracoes(
                        self.db.listar_equipamentos(), self.config.get_configuracoes(),
                        self.db.listar_clientes()
                    )
                    lbl_status.after(0, lambda: lbl_status.configure(text="Salvo!", text_color="green"))
                    self.atualizar_lista()
                    dialog.after(0, dialog.destroy)
                except Exception as e:
                    erro_msg = str(e)
                    lbl_status.after(0, lambda msg=erro_msg: lbl_status.configure(text=f"Erro: {msg}", text_color="red"))

            threading.Thread(target=salvar_db, daemon=True).start()

        ctk.CTkButton(main_frame, text="Salvar", command=salvar, width=150).pack(pady=20)

    def editar(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um servidor")
            return

        try:
            valores = self.tree.item(self.item_selecionado, "values")
            if not valores:
                return
        except:
            self.item_selecionado = None
            return

        nome_srv = valores[0]
        idx = next((i for i, s in enumerate(self.servidores) if s.get("nome") == nome_srv), None)
        if idx is None:
            return

        srv = self.servidores[idx]
        self.localidades = self.db.listar_localidades()

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Editar Servidor")
        dialog.geometry("450x350")
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (225)
        y = (dialog.winfo_screenheight() // 2) - (175)
        dialog.geometry(f"450x350+{x}+{y}")

        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(main_frame, text="Nome:").pack(anchor="w", pady=(5, 0))
        entry_nome = ctk.CTkEntry(main_frame, width=380)
        entry_nome.insert(0, srv.get("nome", ""))
        entry_nome.pack(anchor="w", pady=5)

        ctk.CTkLabel(main_frame, text="IP:").pack(anchor="w", pady=(10, 0))
        entry_ip = ctk.CTkEntry(main_frame, width=380)
        entry_ip.insert(0, srv.get("ip", ""))
        entry_ip.pack(anchor="w", pady=5)

        ctk.CTkLabel(main_frame, text="Localidade:").pack(anchor="w", pady=(10, 0))
        localidades_lista = self.localidades.copy() if self.localidades else ["Nenhuma localidade cadastrada"]
        combo_local = ctk.CTkComboBox(main_frame, values=localidades_lista, width=380)
        combo_local.set(srv.get("localidade", ""))
        combo_local.pack(anchor="w", pady=5)

        lbl_status = ctk.CTkLabel(main_frame, text="", font=("Arial", 10))
        lbl_status.pack(anchor="w", pady=5)

        def salvar():
            srv["nome"] = entry_nome.get().strip()
            srv["ip"] = entry_ip.get().strip()
            localidade = combo_local.get()
            srv["localidade"] = "" if localidade == "Nenhuma localidade cadastrada" else localidade

            lbl_status.configure(text="Salvando...", text_color="orange")

            def salvar_db():
                try:
                    self.db.salvar_equipamento(srv)
                    self.monitor.atualizar_configuracoes(
                        self.db.listar_equipamentos(), self.config.get_configuracoes(),
                        self.db.listar_clientes()
                    )
                    lbl_status.after(0, lambda: lbl_status.configure(text="Salvo!", text_color="green"))
                    self._atualizar_linha(idx)
                    dialog.after(0, dialog.destroy)
                except Exception as e:
                    erro_msg = str(e)
                    lbl_status.after(0, lambda msg=erro_msg: lbl_status.configure(text=f"Erro: {msg}", text_color="red"))

            threading.Thread(target=salvar_db, daemon=True).start()

        ctk.CTkButton(main_frame, text="Salvar", command=salvar, width=150).pack(pady=20)

    def excluir(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione um servidor")
            return

        try:
            valores = self.tree.item(self.item_selecionado, "values")
            if not valores:
                return
        except:
            self.item_selecionado = None
            return

        nome_srv = valores[0]
        idx = next((i for i, s in enumerate(self.servidores) if s.get("nome") == nome_srv), None)
        if idx is None:
            return

        if messagebox.askyesno("Confirmar", f"Excluir servidor '{nome_srv}'?"):
            srv_id = self.servidores[idx].get("id")

            def excluir_db():
                try:
                    if srv_id:
                        self.db.excluir_equipamento(srv_id)
                    del self.servidores[idx]
                    self.monitor.atualizar_configuracoes(
                        self.db.listar_equipamentos(), self.config.get_configuracoes(),
                        self.db.listar_clientes()
                    )
                    self.atualizar_lista()
                except Exception as e:
                    erro_msg = str(e)
                    messagebox.showerror("Erro", f"Erro ao excluir: {erro_msg}")

            threading.Thread(target=excluir_db, daemon=True).start()