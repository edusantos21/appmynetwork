# aba_localidades.py - FINAL (botões dentro + scroll fininho + sem flicker)
import customtkinter as ctk
from tkinter import messagebox, ttk
import threading


class AbaLocalidades:
    def __init__(self, parent, config, db, atualizar_callback):
        self.parent = parent
        self.config = config
        self.db = db
        self.atualizar_callback = atualizar_callback
        self.localidades = db.listar_localidades()
        self.item_selecionado = None

        self.criar_aba()

    def criar_aba(self):
        self.container = ctk.CTkFrame(self.parent)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        tree_frame = ctk.CTkFrame(self.container)
        tree_frame.pack(fill="both", expand=True, pady=(10, 0))
        tree_frame.pack_propagate(False)

        # ✅ Botões DENTRO do tree_frame
        btn_frame = ctk.CTkFrame(tree_frame)
        btn_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(btn_frame, text="+ Adicionar Localidade", command=self.adicionar, width=150).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Editar", command=self.editar, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Excluir", command=self.excluir, width=100).pack(side="left", padx=5)

        self.tree = ttk.Treeview(tree_frame, columns=("nome", "equipamentos", "clientes"), show="headings")
        self.tree.heading("nome", text="Localidade")
        self.tree.heading("equipamentos", text="Equipamentos")
        self.tree.heading("clientes", text="Clientes Reais")

        self.tree.column("nome", width=300)
        self.tree.column("equipamentos", width=120, anchor="center")
        self.tree.column("clientes", width=150, anchor="center")

        # ✅ Scroll fininho do customtkinter
        scrollbar = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.atualizar_lista()

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

        equipamentos = self.db.listar_equipamentos()

        totais = {}
        for eq in equipamentos:
            localidade = eq.get("localidade", "Sem Localidade")
            if localidade not in totais:
                totais[localidade] = {"equipamentos": 0, "clientes_reais": 0}
            
            totais[localidade]["equipamentos"] += 1

            modo = eq.get("modo_operacao", "cliente")
            if modo == "cliente":
                dados_snmp = eq.get("dados_snmp", {})
                valor_clientes = dados_snmp.get("clientes", 0)
                try:
                    clientes = int(valor_clientes) if valor_clientes else 0
                except (ValueError, TypeError):
                    clientes = 0
                totais[localidade]["clientes_reais"] += clientes

        for local in self.localidades:
            dados = totais.get(local, {"equipamentos": 0, "clientes_reais": 0})
            equipamentos_qtd = int(dados["equipamentos"]) if dados["equipamentos"] else 0
            clientes_qtd = int(dados["clientes_reais"]) if dados["clientes_reais"] else 0
            
            item_id = self.tree.insert("", "end", values=(local, equipamentos_qtd, clientes_qtd))
            
            if nome_selecionado == local:
                self.tree.selection_set(item_id)
                self.item_selecionado = item_id

        if "Sem Localidade" in totais:
            dados = totais["Sem Localidade"]
            equipamentos_qtd = int(dados["equipamentos"]) if dados["equipamentos"] else 0
            clientes_qtd = int(dados["clientes_reais"]) if dados["clientes_reais"] else 0
            
            item_id = self.tree.insert("", "end", values=("Sem Localidade", equipamentos_qtd, clientes_qtd))
            if nome_selecionado == "Sem Localidade":
                self.tree.selection_set(item_id)
                self.item_selecionado = item_id

    def _atualizar_linha(self, idx):
        local = self.localidades[idx]
        equipamentos = self.db.listar_equipamentos()
        
        equip_qtd = sum(1 for eq in equipamentos if eq.get("localidade") == local)
        clientes_qtd = 0
        for eq in equipamentos:
            if eq.get("localidade") == local and eq.get("modo_operacao", "cliente") == "cliente":
                clientes_qtd += int(eq.get("dados_snmp", {}).get("clientes", 0) or 0)
        
        for item_id in self.tree.get_children():
            valores = self.tree.item(item_id, "values")
            if valores and valores[0] == local:
                self.tree.item(item_id, values=(local, equip_qtd, clientes_qtd))
                break

    def adicionar(self):
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Nova Localidade")
        dialog.geometry("400x200")
        dialog.minsize(400, 200)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (200)
        y = (dialog.winfo_screenheight() // 2) - (100)
        dialog.geometry(f"400x200+{x}+{y}")

        ctk.CTkLabel(dialog, text="Nome da Localidade:").pack(anchor="w", padx=20, pady=(20, 5))
        entry_nome = ctk.CTkEntry(dialog, width=350)
        entry_nome.pack(padx=20, pady=5)

        lbl_status = ctk.CTkLabel(dialog, text="", font=("Arial", 11))
        lbl_status.pack(anchor="w", padx=20, pady=5)

        def salvar():
            nome = entry_nome.get().strip()
            if nome and nome not in self.localidades:
                lbl_status.configure(text="Salvando...", text_color="orange")

                def salvar_db():
                    try:
                        self.db.salvar_localidade(nome)
                        self.localidades.append(nome)
                        lbl_status.after(0, lambda: lbl_status.configure(text="Salvo!", text_color="green"))
                        self.atualizar_lista()
                        dialog.after(0, dialog.destroy)
                    except Exception as e:
                        erro_msg = str(e)
                        lbl_status.after(0, lambda msg=erro_msg: lbl_status.configure(text=f"Erro: {msg}", text_color="red"))

                threading.Thread(target=salvar_db, daemon=True).start()
            elif nome in self.localidades:
                messagebox.showwarning("Aviso", "Localidade ja existe!")

        ctk.CTkButton(dialog, text="Salvar", command=salvar, width=200).pack(pady=20)

    def editar(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione uma localidade")
            return

        try:
            valores = self.tree.item(self.item_selecionado, "values")
            if not valores:
                return
        except:
            self.item_selecionado = None
            return

        if valores[0] == "Sem Localidade":
            messagebox.showwarning("Aviso", "Nao e possivel editar 'Sem Localidade'")
            return

        local_antigo = valores[0]
        idx = self.localidades.index(local_antigo)

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Editar Localidade")
        dialog.geometry("400x200")
        dialog.minsize(400, 200)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (200)
        y = (dialog.winfo_screenheight() // 2) - (100)
        dialog.geometry(f"400x200+{x}+{y}")

        ctk.CTkLabel(dialog, text="Nome da Localidade:").pack(anchor="w", padx=20, pady=(20, 5))
        entry_nome = ctk.CTkEntry(dialog, width=350)
        entry_nome.insert(0, local_antigo)
        entry_nome.pack(padx=20, pady=5)

        lbl_status = ctk.CTkLabel(dialog, text="", font=("Arial", 11))
        lbl_status.pack(anchor="w", padx=20, pady=5)

        def salvar():
            novo_nome = entry_nome.get().strip()
            if novo_nome and novo_nome not in self.localidades:
                lbl_status.configure(text="Salvando...", text_color="orange")

                def salvar_db():
                    try:
                        equipamentos = self.db.listar_equipamentos()
                        for eq in equipamentos:
                            if eq.get("localidade") == local_antigo:
                                eq["localidade"] = novo_nome
                                self.db.salvar_equipamento(eq)

                        self.db.excluir_localidade(local_antigo)
                        self.db.salvar_localidade(novo_nome)

                        self.localidades[idx] = novo_nome

                        lbl_status.after(0, lambda: lbl_status.configure(text="Salvo!", text_color="green"))
                        self._atualizar_linha(idx)
                        dialog.after(0, dialog.destroy)
                    except Exception as e:
                        erro_msg = str(e)
                        lbl_status.after(0, lambda msg=erro_msg: lbl_status.configure(text=f"Erro: {msg}", text_color="red"))

                threading.Thread(target=salvar_db, daemon=True).start()
            elif novo_nome == local_antigo:
                dialog.destroy()
            else:
                messagebox.showwarning("Aviso", "Localidade ja existe!")

        ctk.CTkButton(dialog, text="Salvar", command=salvar, width=200).pack(pady=20)

    def excluir(self):
        if not self.item_selecionado:
            messagebox.showwarning("Aviso", "Selecione uma localidade")
            return

        try:
            valores = self.tree.item(self.item_selecionado, "values")
            if not valores:
                return
        except:
            self.item_selecionado = None
            return

        if valores[0] == "Sem Localidade":
            messagebox.showwarning("Aviso", "Nao e possivel excluir 'Sem Localidade'")
            return

        local = valores[0]

        equipamentos = self.db.listar_equipamentos()
        equipamentos_usando = [eq for eq in equipamentos if eq.get("localidade") == local]

        if equipamentos_usando:
            msg = f"Localidade '{local}' usada por {len(equipamentos_usando)} equipamento(s).\n\nDeseja excluir? Os equipamentos ficarao sem localidade."
            if not messagebox.askyesno("Confirmar", msg):
                return

        if messagebox.askyesno("Confirmar", f"Excluir localidade '{local}'?"):

            def excluir_db():
                try:
                    for eq in equipamentos_usando:
                        eq["localidade"] = ""
                        self.db.salvar_equipamento(eq)

                    self.db.excluir_localidade(local)
                    self.localidades.remove(local)
                    self.atualizar_lista()
                except Exception as e:
                    erro_msg = str(e)
                    messagebox.showerror("Erro", f"Erro ao excluir: {erro_msg}")

            threading.Thread(target=excluir_db, daemon=True).start()