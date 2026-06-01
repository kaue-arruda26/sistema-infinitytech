import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import streamlit.components.v1 as components

# =========================================================================
# 1. FUNÇÃO DE CONEXÃO SEGURA COM O BANCO DE DADOS (SUPABASE / NUVEM)
# =========================================================================
def abrir_conexao():
    """
    Conecta ao banco de dados PostgreSQL do Supabase utilizando as 
    credenciais seguras armazenadas no st.secrets.
    """
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )

# Configurações iniciais da página do Streamlit
st.set_page_config(page_title="InfinityTech Gestão", layout="wide")
st.title("💻 Sistema de Gestão e O.S. - InfinityTech")

# Criação das 4 abas principais do sistema
aba_clientes, aba_estoque, aba_os, aba_caixa = st.tabs([
    "👤 Clientes", 
    "📦 Catálogo de Estoque (Produtos/Acessórios)", 
    "📝 Gerenciamento de O.S. / Atendimentos", 
    "📊 Painel de Caixa"
])

# =========================================================================
# 2. ABA DE CLIENTES
# =========================================================================
with aba_clientes:
    st.header("Cadastro de Novos Clientes")
    with st.form("form_cliente", clear_on_submit=True):
        nome = st.text_input("Nome Completo:")
        documento = st.text_input("CPF ou RG:")
        whatsapp = st.text_input("WhatsApp (Com DDD):")
        email = st.text_input("E-mail:")
        
        if st.form_submit_button("Salvar Cliente"):
            if nome and whatsapp:
                try:
                    conn = abrir_conexao()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Clientes (Nome, WhatsApp, Email, Documento) 
                        VALUES (%s, %s, %s, %s)
                    """, (nome, whatsapp, email if email else None, documento if documento else None))
                    conn.commit()
                    st.success(f"🎉 Cliente '{nome}' cadastrado com sucesso!")
                except psycopg2.IntegrityError:
                    st.error("⚠️ Este WhatsApp ou CPF/RG já está cadastrado no sistema!")
                except Exception as e:
                    st.error(f"Erro inesperado: {e}")
                finally:
                    conn.close()
            else:
                st.warning("⚠️ Nome e WhatsApp são campos obrigatórios.")

# =========================================================================
# 3. ABA DE ESTOQUE (Catálogo Universal da Loja)
# =========================================================================
with aba_estoque:
    st.header("📦 Cadastro de Modelos Base no Catálogo")
    st.markdown("Use esta aba para registrar um **novo modelo** que a loja nunca trabalhou antes.")
    
    with st.form("form_novo_produto", clear_on_submit=True):
        tipo_item = st.selectbox(
            "Tipo do Produto / Mercadoria:",
            ["💻 Notebook", "🖱️ Acessório (Mouse, Teclado, Carregador)", "🔌 Componente/Peça (SSD, Memória, Tela)", "📦 Outros"]
        )
        
        marca = st.text_input("Marca (Ex: Dell, Logitech, Kingston, Razer):")
        modelo = st.text_input("Modelo / Configuração / Descrição:")
        custo = st.number_input("Custo de Aquisição (R$):", min_value=0.0, step=10.0)
        val_minimo = st.number_input("Valor Mínimo de Venda (R$):", min_value=0.0, step=10.0)
        val_venda = st.number_input("Valor Comercial Sugerido (R$):", min_value=0.0, step=10.0)
        
        quantidade = st.number_input("Quantidade inicial de entrada:", min_value=1, step=1, value=1)
        
        if st.form_submit_button("Adicionar ao Estoque da Loja"):
            if marca and modelo:
                try:
                    conn = abrir_conexao()
                    cursor = conn.cursor()
                    
                    modelo_com_tipo = f"[{tipo_item.split(' ')[1]}] {modelo}"
                    
                    # No PostgreSQL usamos RETURNING para pegar o ID gerado na hora
                    cursor.execute("""
                        INSERT INTO Produtos (Marca, Modelo, CustoProduto, ValorMinimo, ValorVenda)
                        VALUES (%s, %s, %s, %s, %s) RETURNING IdProduto
                    """, (marca, modelo_com_tipo, custo, val_minimo, val_venda))
                    id_prod_criado = cursor.fetchone()[0]
                    
                    for i in range(int(quantidade)):
                        sn_gerado = f"REF-{id_prod_criado}-{i+1}"
                        cursor.execute("""
                            INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status) 
                            VALUES (%s, %s, 'Disponivel')
                        """, (id_prod_criado, sn_gerado))
                    
                    conn.commit()
                    st.success(f"✅ Sucesso! Cadastradas {quantidade} unidades prontas para venda!")
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")
                finally:
                    conn.close()
            else:
                st.warning("⚠️ Marca e Modelo/Descrição são obrigatórios.")

# =========================================================================
# 4. ABA DE ORDENS DE SERVIÇO / GERENCIAMENTO
# =========================================================================
with aba_os:
    st.header("📝 Painel de Controle de Atendimentos")
    sub_consulta, sub_nova_os = st.tabs(["🔍 Consultar e Atualizar O.S.", "➕ Abrir Nova O.S. ou Venda"])
    
    with sub_consulta:
        st.subheader("Buscar Informações do Atendimento")
        opcao_busca = st.radio("Como deseja buscar?", ["Por Número da O.S.", "Por Dados do Cliente (WhatsApp ou CPF/RG)"])
        id_busca_final = None
        
        if opcao_busca == "Por Número da O.S.":
            numero_os_busca = st.number_input("Digite o número da Ordem de Serviço:", min_value=1, step=1, value=1)
            id_busca_final = int(numero_os_busca)
        else:
            dados_busca = st.text_input("Digite o WhatsApp ou o CPF/RG exato do cliente:")
            if dados_busca:
                try:
                    conn = abrir_conexao()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT f.IdLancamento 
                        FROM FluxoCaixa f JOIN Clientes c ON f.IdCliente = c.IdCliente 
                        WHERE c.Documento = %s OR c.WhatsApp = %s 
                        ORDER BY f.IdLancamento DESC LIMIT 1
                    """, (dados_busca, dados_busca))
                    res_doc = cursor.fetchone()
                    conn.close()
                    if res_doc:
                        id_busca_final = res_doc[0]
                        st.info(f"O.S. encontrada para este cliente: Nº {id_busca_final}")
                    else:
                        st.error("❌ Nenhum atendimento encontrado para este documento ou WhatsApp.")
                except Exception as e:
                    st.error(f"Erro ao buscar por dados: {e}")

        if "dados_os" not in st.session_state:
            st.session_state.dados_os = None

        if st.button("Buscar no Sistema", key="btn_busca_os") and id_busca_final:
            try:
                conn = abrir_conexao()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f.IdLancamento, c.Nome, c.WhatsApp, p.Marca, p.Modelo, i.NumeroSerie, i.Status, f.Valor, f.Descricao, f.DataLancamento, i.IdItem, c.Documento
                    FROM FluxoCaixa f
                    JOIN Clientes c ON f.IdCliente = c.IdCliente
                    JOIN ItensEstoque i ON f.IdItem = i.IdItem
                    JOIN Produtos p ON i.IdProduto = p.IdProduto
                    WHERE f.IdLancamento = %s
                """, (id_busca_final,))
                st.session_state.dados_os = cursor.fetchone()
                conn.close()
            except Exception as e:
                st.error(f"Erro ao buscar no banco: {e}")
        
        if st.session_state.dados_os and id_busca_final and st.session_state.dados_os[0] == id_busca_final:
            dados = st.session_state.dados_os
            id_item_banco = dados[10]
            
            st.write("---")
            st.success(f"📋 **Atendimento Nº {dados[0]} Carregado!**")
            
            col_cli, col_not, col_status = st.columns(3)
            with col_cli:
                st.markdown(f"### 👤 Cliente\n**Nome:** {dados[1]}\n\n**WhatsApp:** {dados[2]}\n\n**CPF/RG:** {dados[11] if dados[11] else '---'}")
            with col_not:
                st.markdown(f"### 📦 Item/Equipamento\n**Modelo:** {dados[3]} {dados[4]}\n\n**Identificador/SN:** {dados[5]}")
            with col_status:
                st.markdown(f"### 📊 Status\n**{dados[6].upper()}**")
                    
            st.write("---")
            st.markdown(f"**💰 Valor cobrado:** R$ {dados[7]:.2f}")
            st.markdown(f"**📝 Histórico/Detalhes:** {dados[8]}")
            st.caption(f"📅 Abertura: {dados[9].strftime('%d/%m/%Y %H:%M')}")
            
            st.write("---")
            st.subheader("🖨️ Impressão de Comprovante de Balcão")
            
            html_os = f"""
            <html>
            <head>
                <style>
                    @media print {{ body {{ width: 72mm; font-family: monospace; font-size: 11px; margin: 0; }} }}
                    .recibo {{ width: 240px; font-family: monospace; padding: 2px; line-height: 1.2; }}
                    .centralizado {{ text-align: center; }}
                    .linha {{ border-top: 1px dashed #000; margin: 4px 0; }}
                    .espaco-assinatura {{ margin-top: 25px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="recibo">
                    <div class="centralizado">
                        <strong>** INFINITY TECH **</strong><br>
                        Assistencia Tecnica e Vendas<br>
                        Rua Santa Efigenia, 264 Box 9-A<br>
                        Sao Paulo - SP<br>
                        ----------------------------
                    </div>
                    <strong>COMPROVANTE O.S. NO {dados[0]}</strong><br>
                    Data: {dados[9].strftime('%d/%m/%Y %H:%M')}<br>
                    <div class="linha"></div>
                    <strong>CLIENTE:</strong> {dados[1]}<br>
                    <strong>DOC:</strong> {dados[11] if dados[11] else '---'}<br>
                    <strong>WHATS:</strong> {dados[2]}<br>
                    <div class="linha"></div>
                    <strong>PROD/APARELHO:</strong> {dados[3]} {dados[4]}<br>
                    <strong>S/N ou REF:</strong> {dados[5]}<br>
                    <strong>DETALHES:</strong> {dados[8]}<br>
                    <div class="linha"></div>
                    <strong>VALOR BRUTO: R$ {dados[7]:.2f}</strong><br>
                    <div class="linha"></div>
                    <div class="espaco-assinatura">___________________________<br>Assinatura do Cliente</div>
                    <div class="espaco-assinatura">___________________________<br>Assinatura InfinityTech</div>
                </div>
                <script>window.print();</script>
            </body>
            </html>
            """
            
            if st.button("🖨️ Mandar para Impressora de Balcão", type="primary"):
                components.html(html_os, height=1)
                st.info("💡 Janela de impressão aberta.")

            st.write("---")
            st.subheader("⚙️ Ações Administrativas")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                if st.button("🛠️ Em Manutenção"):
                    conn = abrir_conexao(); c = conn.cursor(); c.execute("UPDATE ItensEstoque SET Status = 'Manutencao' WHERE IdItem = %s", (id_item_banco,)); conn.commit(); conn.close(); st.rerun()
            with col_b2:
                if st.button("🔵 Pronto para Retirada"):
                    conn = abrir_conexao(); c = conn.cursor(); c.execute("UPDATE ItensEstoque SET Status = 'Pronto' WHERE IdItem = %s", (id_item_banco,)); conn.commit(); conn.close(); st.rerun()
            with col_b3:
                if st.button("🟢 Entregue / Finalizado"):
                    conn = abrir_conexao(); c = conn.cursor(); c.execute("UPDATE ItensEstoque SET Status = 'Entregue' WHERE IdItem = %s", (id_item_banco,)); conn.commit(); conn.close(); st.rerun()

    with sub_nova_os:
        st.subheader("Abertura de Novo Atendimento / Venda")
        busca_cliente_unificada = st.text_input("Digite o WhatsApp ou o CPF/RG do cliente para iniciar:")
        id_cliente_selecionado = None
        
        if busca_cliente_unificada:
            conn = abrir_conexao()
            cursor = conn.cursor()
            cursor.execute("SELECT IdCliente, Nome FROM Clientes WHERE WhatsApp = %s OR Documento = %s", (busca_cliente_unificada, busca_cliente_unificada))
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado:
                id_cliente_selecionado = resultado[0]
                st.success(f"✅ Cliente Vinculado: **{resultado[1]}**")
            else:
                st.error("❌ Cliente não encontrado! Cadastre-o na aba 'Clientes' primeiro.")
                
        if id_cliente_selecionado:
            st.write("---")
            tipo_atendimento = st.radio("O que este cliente está fazendo?", ["🛒 Comprando uma Mercadoria da Loja", "🛠️ Deixando um Notebook para Conserto"])
            st.write("---")
            
            id_prod_final = None; marca_manut = ""; modelo_manut = ""; valor_sugerido_venda = 0.0
            
            if tipo_atendimento == "🛒 Comprando uma Mercadoria da Loja":
                conn = abrir_conexao(); cursor = conn.cursor()
                cursor.execute("SELECT IdProduto, Marca, Modelo, ValorVenda FROM Produtos")
                modelos_loja = cursor.fetchall(); conn.close()
                if not modelos_loja:
                    st.warning("⚠️ Não há produtos cadastrados.")
                else:
                    lista_modelos = {f"{m[1]} - {m[2]} (Preço: R$ {m[3]})": (m[0], m[3]) for m in modelos_loja}
                    modelo_escolhido = st.selectbox("Selecione o Produto Comercializado:", list(lista_modelos.keys()))
                    id_prod_final, valor_sugerido_venda = lista_modelos[modelo_escolhido]
                    valor_final = st.number_input("Valor Final Cobrado (R$):", value=float(valor_sugerido_venda))
                    detalhes = st.text_area("Observações da Venda:")
            else:
                col_m1, col_m2 = st.columns(2)
                with col_m1: marca_manut = st.text_input("Marca do Aparelho:")
                with col_m2: modelo_manut = st.text_input("Modelo/Configuração:")
                sn_informado = st.text_input("Número de Série do Equipamento:")
                valor_final = st.number_input("Preço Inicial do Conserto (R$):", value=0.0)
                detalhes = st.text_area("Defeito / Relato:")

            if st.button("🚀 Confirmar e Gerar Atendimento", key="btn_gerar_os_novo"):
                try:
                    conn = abrir_conexao(); cursor = conn.cursor()
                    if tipo_atendimento == "🛒 Comprando uma Mercadoria da Loja":
                        cursor.execute("""
                            SELECT IdItem FROM ItensEstoque 
                            WHERE IdProduto = %s AND LOWER(Status) = 'disponivel' 
                            ORDER BY IdItem ASC LIMIT 1
                        """, (id_prod_final,))
                        item_disponivel = cursor.fetchone()
                        
                        if not item_disponivel:
                            st.error("❌ OPERAÇÃO BLOQUEADA: Não há nenhuma unidade física deste produto disponível!")
                        else:
                            id_item_final = item_disponivel[0]
                            cursor.execute("UPDATE ItensEstoque SET Status = 'Vendido' WHERE IdItem = %s", (id_item_final,))
                            cursor.execute("INSERT INTO FluxoCaixa (IdItem, IdCliente, Tipo, Valor, Descricao) VALUES (%s, %s, 'E', %s, %s)", (id_item_final, id_cliente_selecionado, valor_final, f"[VENDA] - {detalhes}"))
                            conn.commit()
                            st.success("🎯 Venda gerada com sucesso!")
                            st.balloons()
                    else:
                        if not marca_manut or not modelo_manut:
                            st.error("❌ Digite a Marca e o Modelo.")
                        else:
                            cursor.execute("INSERT INTO Produtos (Marca, Modelo, CustoProduto, ValorMinimo, ValorVenda) VALUES (%s, %s, 0, 0, %s) RETURNING IdProduto", (marca_manut, modelo_manut, valor_final))
                            id_prod_final = cursor.fetchone()[0]
                            sn_final = sn_informado if sn_informado else f"OS-TEMP"
                            cursor.execute("INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status) VALUES (%s, %s, 'Manutencao') RETURNING IdItem", (id_prod_final, sn_final))
                            id_item_final = cursor.fetchone()[0]
                            cursor.execute("INSERT INTO FluxoCaixa (IdItem, IdCliente, Tipo, Valor, Descricao) VALUES (%s, %s, 'E', %s, %s)", (id_item_final, id_cliente_selecionado, valor_final, f"[ASSISTÊNCIA] - {detalhes}"))
                            conn.commit()
                            st.success("🎯 Ordem de Serviço aberta com sucesso!")
                    conn.close()
                except Exception as e:
                    st.error(f"Erro: {e}")

# =========================================================================
# 5. ABA DE PAINEL DE CAIXA / FINANCEIRO (Busca Ágil Integrada)
# =========================================================================
with aba_caixa:
    st.header("📊 Painel Financeiro e Faturamento")
    col_caixa1, col_caixa2 = st.columns([1, 1])
    
    try:
        conn = abrir_conexao()
        
        # Carregando dados via pandas de forma otimizada para PostgreSQL
        df_estoque = pd.read_sql("""
            SELECT p.IdProduto, p.Marca, p.Modelo, i.NumeroSerie, i.Status, p.CustoProduto, p.ValorVenda
            FROM ItensEstoque i
            JOIN Produtos p ON i.IdProduto = p.IdProduto
        """, conn)
        
        df_caixa = pd.read_sql("""
            SELECT f.IdLancamento AS "Nº O.S.", c.Nome AS "Cliente", f.Valor AS "Valor (R$)", 
                   f.Descricao AS "Descrição", f.DataLancamento AS "Data/Hora" 
            FROM FluxoCaixa f 
            JOIN Clientes c ON f.IdCliente = c.IdCliente 
            WHERE f.Tipo = 'E' 
            ORDER BY f.IdLancamento DESC
        """, conn)
        conn.close()
        
        # COLUNA DA ESQUERDA: PESQUISA E CONTROLE DE ESTOQUE
        with col_caixa1:
            st.subheader("🔍 Localizar Item no Estoque")
            termo_busca = st.text_input("Digite a Marca ou Modelo para pesquisar:", value="")
            st.write("---")
            
            if termo_busca.strip() != "":
                if not df_estoque.empty:
                    df_disponiveis = df_estoque[df_estoque["Status"].str.lower().str.strip() == "disponivel"]
                    
                    conn = abrir_conexao()
                    cursor = conn.cursor()
                    # ILIKE ignora maiúsculas/minúsculas no PostgreSQL
                    cursor.execute("SELECT IdProduto, Marca, Modelo FROM Produtos WHERE Marca ILIKE %s OR Modelo ILIKE %s", (f"%{termo_busca}%", f"%{termo_busca}%"))
                    produtos_filtrados = cursor.fetchall()
                    conn.close()
                    
                    if produtos_filtrados:
                        st.markdown(f"### 📋 Resultado da Busca por '{termo_busca}'")
                        for prod_cat in produtos_filtrados:
                            id_p, marca_p, modelo_p = prod_cat
                            qtd_atual = len(df_disponiveis[df_disponiveis["IdProduto"] == id_p])
                            
                            col_nome, col_qtd, col_btn_mais, col_btn_menos, col_btn_del = st.columns([3, 1, 1, 1, 1])
                            with col_nome:
                                st.write(f"**{marca_p}** - {modelo_p}")
                            with col_qtd:
                                st.markdown(f"`{qtd_atual} un.`")
                            with col_btn_mais:
                                if st.button("➕", key=f"btn_mais_{id_p}"):
                                    conn = abrir_conexao(); cursor = conn.cursor()
                                    cursor.execute("SELECT COUNT(*) FROM ItensEstoque WHERE IdProduto = %s", (id_p,))
                                    contagem = cursor.fetchone()[0]
                                    novo_sn = f"REF-{id_p}-{contagem + 1}"
                                    cursor.execute("INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status) VALUES (%s, %s, 'Disponivel')", (id_p, novo_sn))
                                    conn.commit(); conn.close(); st.rerun()
                            with col_btn_menos:
                                if st.button("❌", key=f"btn_menos_{id_p}"):
                                    if qtd_atual > 0:
                                        conn = abrir_conexao(); cursor = conn.cursor()
                                        cursor.execute("""
                                            SELECT IdItem FROM ItensEstoque 
                                            WHERE IdProduto = %s AND LOWER(Status) = 'disponivel'
                                            ORDER BY IdItem ASC LIMIT 1
                                        """, (id_p,))
                                        item_id_baixa = cursor.fetchone()[0]
                                        cursor.execute("UPDATE ItensEstoque SET Status = 'Vendido' WHERE IdItem = %s", (item_id_baixa,))
                                        conn.commit(); conn.close(); st.rerun()
                                    else:
                                        st.error("Estoque zerado!")
                            with col_btn_del:
                                if st.button("🗑️", key=f"btn_del_{id_p}"):
                                    try:
                                        conn = abrir_conexao(); cursor = conn.cursor()
                                        cursor.execute("DELETE FROM ItensEstoque WHERE IdProduto = %s", (id_p,))
                                        cursor.execute("DELETE FROM Produtos WHERE IdProduto = %s", (id_p,))
                                        conn.commit(); conn.close(); st.rerun()
                                    except Exception as err_del:
                                        st.error(f"Erro ao apagar: {err_del}")
                            st.write("---")
                    else:
                        st.warning("⚠️ Nenhum produto encontrado.")
            else:
                st.info("💡 Use a barra acima para gerenciar um produto específico.")

        # COLUNA DA DIREITA: HISTÓRICO FINANCEIRO
        with col_caixa2:
            st.subheader("💸 Histórico de Vendas e O.S. Recentes")
            if not df_caixa.empty:
                df_caixa["Data/Hora"] = pd.to_datetime(df_caixa["Data/Hora"]).dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(df_caixa, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum registro de faturamento encontrado.")
                
            st.write("---")
            st.subheader("📦 Download Planilha Completa")
            if not df_estoque.empty:
                df_excel = df_estoque.copy()
                if "IdProduto" in df_excel.columns:
                    df_excel = df_excel.drop(columns=["IdProduto"])
                
                csv_data = df_excel.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="🟢 Exportar Estoque para o Excel (CSV)",
                    data=csv_data,
                    file_name="Estoque_InfinityTech.csv",
                    mime="text/csv",
                    type="primary"
                )
    except Exception as e:
        st.error(f"Erro no painel: {e}")