import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timezone, timedelta
import requests

def converter_para_sp(dt):
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt_sp = dt.astimezone(timezone(timedelta(hours=-3)))
    else:
        dt_sp = dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    return dt_sp.replace(tzinfo=None)

def obter_agora_sp():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).replace(tzinfo=None)

import re

# Configurações iniciais da página do Streamlit
st.set_page_config(page_title="InfinityTech ERP", layout="wide", page_icon="💻")


# =========================================================================
# 1. FUNÇÃO DE CONEXÃO E AUXILIARES DE BANCO DE DADOS
# =========================================================================
def abrir_conexao():
    """
    Conecta ao banco de dados PostgreSQL do Supabase utilizando as 
    credenciais armazenadas no st.secrets.
    """
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )

def executar_query(query, params=None, fetch=None):
    """
    Executa uma query no banco de dados com tratamento de conexões automático.
    fetch: None, 'one', 'all'
    """
    conn = abrir_conexao()
    cursor = conn.cursor()
    resultado = None
    try:
        cursor.execute(query, params)
        if fetch == 'one':
            resultado = cursor.fetchone()
        elif fetch == 'all':
            resultado = cursor.fetchall()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
    return resultado

def validar_cpf(cpf):
    # Remove caracteres nao numericos
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11:
        return False
    # CPFs com todos os digitos repetidos sao invalidos
    if cpf in [d * 11 for d in "0123456789"]:
        return False
    
    # Valida primeiro digito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto in [10, 11]:
        resto = 0
    if resto != int(cpf[9]):
        return False
        
    # Valida segundo digito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto in [10, 11]:
        resto = 0
    if resto != int(cpf[10]):
        return False
        
    return True

def buscar_cep(cep):
    # Remove caracteres nao numericos
    cep_clean = re.sub(r'\D', '', cep)
    if len(cep_clean) != 8:
        return None
    try:
        response = requests.get(f"https://viacep.com.br/ws/{cep_clean}/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "erro" not in data:
                return data
    except Exception:
        pass
    return None

# =========================================================================
# 2. SISTEMA DE DESIGN (CSS CUSTOMIZADO)
# =========================================================================
st.markdown("""
<style>
    /* Carrega fonte Outfit do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Estilos Globais */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Títulos e Headers */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #1E293B;
    }

    /* Cartão de Métrica Customizado */
    .metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        padding: 24px;
        transition: all 0.25s ease-in-out;
        margin-bottom: 20px;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -8px rgba(99, 102, 241, 0.15);
        border-color: #6366F1;
    }
    .metric-title {
        font-size: 13px;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 32px;
        color: #0F172A;
        font-weight: 700;
        margin-top: 8px;
    }
    
    /* Cores de Métricas */
    .val-primary { color: #4F46E5; }
    .val-success { color: #10B981; }
    .val-warning { color: #F59E0B; }
    .val-danger { color: #EF4444; }

    /* Badges de Status do Estoque / O.S. */
    .badge {
        padding: 6px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        text-align: center;
    }
    .badge-available { background-color: rgba(16, 185, 129, 0.12); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.2); }
    .badge-sold { background-color: rgba(59, 130, 246, 0.12); color: #3B82F6; border: 1px solid rgba(59, 130, 246, 0.2); }
    .badge-maintenance { background-color: rgba(245, 158, 11, 0.12); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.2); }
    .badge-ready { background-color: rgba(139, 92, 246, 0.12); color: #8B5CF6; border: 1px solid rgba(139, 92, 246, 0.2); }
    .badge-delivered { background-color: rgba(100, 116, 139, 0.12); color: #64748B; border: 1px solid rgba(100, 116, 139, 0.2); }

    /* Estilo do Menu Sidebar */
    .sidebar-header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 20px;
    }
    .sidebar-title {
        font-size: 20px;
        font-weight: 700;
        color: #4F46E5;
        margin: 0;
    }
    .sidebar-subtitle {
        font-size: 12px;
        color: #64748B;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# 3. CONTROLE DE SESSÃO E LOGIN
# =========================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

def realizar_login(usuario, senha):
    try:
        user_data = executar_query("""
            SELECT Senha, Role, Nome 
            FROM Usuarios 
            WHERE Usuario = %s
        """, (usuario,), fetch='one')
        
        if user_data and user_data[0] == senha:
            st.session_state.logged_in = True
            st.session_state.user_role = user_data[1]
            st.session_state.user_name = user_data[2]
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")

if not st.session_state.logged_in:
    # CSS customizado para fundo escuro e estilização premium da tela de login
    st.markdown("""
    <style>
        /* Fundo escuro radial matching com o logo */
        [data-testid="stAppViewContainer"] {
            background-color: #080A0F !important;
            background-image: radial-gradient(circle at 30% 30%, #111D37 0%, #080A0F 80%) !important;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        
        /* Ajusta o espaçamento do container principal */
        .block-container {
            padding-top: 4rem !important;
            padding-bottom: 2rem !important;
        }
        
        /* Rótulos (Labels) */
        label {
            color: #94A3B8 !important;
            font-size: 14px !important;
            font-weight: 500 !important;
        }
        
        /* Inputs de texto escuros (Prevenção de fundo branco e letra branca invisível) */
        .stTextInput input {
            color: #FFFFFF !important;
            background-color: #121826 !important;
            border-radius: 10px !important;
            border: none !important;
        }
        
        /* Containers internos do baseweb do Streamlit */
        div[data-baseweb="base-input"], div[data-baseweb="input"] {
            background-color: #121826 !important;
            border: 1px solid #1E293B !important;
            border-radius: 10px !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #6366F1 !important;
        }
        
        /* Garantir texto legível nas opções de Radio Buttons */
        .stRadio p, .stRadio label, .stRadio span {
            color: #E2E8F0 !important;
            font-size: 14px !important;
        }
        
        /* Estilização para as Abas (Tabs) do Streamlit no tema escuro */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
        }
        button[data-baseweb="tab"] p {
            color: #94A3B8 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #FFFFFF !important;
        }
        
        /* Card do formulário */
        .login-card {
            background-color: rgba(13, 18, 30, 0.75);
            border: 1px solid rgba(99, 102, 241, 0.15);
            border-radius: 20px;
            padding: 35px;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(12px);
        }
    </style>
    """, unsafe_allow_html=True)

    # Layout em duas colunas: Esquerda (Logo completo), Direita (Formulário)
    col_l1, col_l2 = st.columns([1.1, 0.9], gap="large")
    
    with col_l1:
        # Exibir logotipo completo
        st.image("logo.png", use_container_width=True)
        
    with col_l2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 15px;">
            <h2 style="color: #FFFFFF; margin: 0; font-family: 'Outfit'; font-size: 32px; font-weight: 700; letter-spacing: -0.5px;">InfinityTech ERP</h2>
            <p style="color: #64748B; font-size: 14px; margin-top: 5px;">Acesse o painel ou crie sua conta</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs para Login e Cadastro
        tab_login, tab_cadastro = st.tabs(["🔒 Entrar", "📝 Criar Conta"])
        
        with tab_login:
            user_input = st.text_input("Usuário:", key="login_usuario")
            pass_input = st.text_input("Senha:", type="password", key="login_senha")
            
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            if st.button("Acessar Sistema", type="primary", use_container_width=True, key="btn_login"):
                if user_input and pass_input:
                    realizar_login(user_input, pass_input)
                else:
                    st.warning("Preencha o usuário e a senha.")
                    
        with tab_cadastro:
            cad_nome = st.text_input("Nome Completo:", placeholder="Ex: Kaue Arruda", key="cad_nome")
            cad_usuario = st.text_input("Nome de Usuário (login):", placeholder="Ex: kaue", key="cad_usuario")
            cad_senha = st.text_input("Senha:", type="password", key="cad_senha")
            
            # Escolha de nível de acesso
            cad_role_desc = st.radio(
                "Tipo de Conta (Nível de Acesso):",
                ["Lojista (Permissão padrão para vendas/cadastro)", "Administrador (Permissão completa - Limite: 1 ADM)"],
                key="cad_role"
            )
            
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            if st.button("Finalizar Cadastro", type="primary", use_container_width=True, key="btn_cadastro"):
                if cad_nome and cad_usuario and cad_senha:
                    cad_usuario_clean = cad_usuario.strip().lower()
                    role_desejada = "adm" if "Administrador" in cad_role_desc else "lojista"
                    
                    try:
                        if role_desejada == "adm":
                            qtd_adm = executar_query("SELECT COUNT(*) FROM Usuarios WHERE Role = 'adm'", fetch='one')[0]
                            if qtd_adm >= 1:
                                st.error("Erro: O sistema já possui um Administrador cadastrado. Não é permitido criar outra conta como ADM.")
                            else:
                                executar_query("""
                                    INSERT INTO Usuarios (Usuario, Senha, Nome, Role)
                                    VALUES (%s, %s, %s, %s)
                                """, (cad_usuario_clean, cad_senha, cad_nome, role_desejada))
                                st.session_state.logged_in = True
                                st.session_state.user_role = role_desejada
                                st.session_state.user_name = cad_nome
                                st.toast("Conta ADM criada com sucesso!", icon="👑")
                                st.rerun()
                        else:
                            executar_query("""
                                INSERT INTO Usuarios (Usuario, Senha, Nome, Role)
                                VALUES (%s, %s, %s, %s)
                            """, (cad_usuario_clean, cad_senha, cad_nome, role_desejada))
                            st.session_state.logged_in = True
                            st.session_state.user_role = role_desejada
                            st.session_state.user_name = cad_nome
                            st.toast("Conta Lojista criada com sucesso!", icon="💼")
                            st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("Erro: Este nome de usuário já está sendo utilizado.")
                    except Exception as e:
                        st.error(f"Erro ao cadastrar conta: {e}")
                else:
                    st.warning("Preencha todos os campos obrigatórios para se cadastrar.")
                    
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =========================================================================
# 4. SIDEBAR - MENU DE NAVEGAÇÃO
# =========================================================================
with st.sidebar:
    # Exibir logotipo da empresa centralizado no topo da barra lateral
    st.image("logo.png", use_container_width=True)
    st.markdown("""
    <div class="sidebar-header" style="margin-top: -10px; margin-bottom: 15px;">
        <h2 class="sidebar-title">InfinityTech ERP</h2>
        <p class="sidebar-subtitle">Gestão & Assistência Técnica</p>
    </div>
    """, unsafe_allow_html=True)
    
    opcoes_menu = [
        "🏠 Painel Geral (Dashboard)", 
        "👤 Clientes (CRM)", 
        "📦 Produtos & Estoque", 
        "📝 Ordens de Serviço (O.S.)"
    ]
    if st.session_state.user_role == 'adm':
        opcoes_menu.append("📊 Financeiro & Caixa")
        opcoes_menu.append("👥 Contas & Acessos")
        
    opcao = st.radio("Navegação do Sistema:", opcoes_menu)
    
    st.write("---")
    st.caption(f"Usuário: {st.session_state.user_name}")
    if st.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = ""
        st.session_state.user_name = ""
        st.rerun()

# =========================================================================
# 4. TELA: PAINEL GERAL (DASHBOARD)
# =========================================================================
if opcao == "🏠 Painel Geral (Dashboard)":
    st.title("🏠 Painel de Indicadores Gerais")
    st.markdown("Visão consolidada da saúde da loja em tempo real.")
    st.write("---")
    
    try:
        # Busca faturamento e despesas
        financeiro = executar_query("""
            SELECT 
                SUM(CASE WHEN Tipo = 'E' THEN Valor ELSE 0 END) as receita,
                SUM(CASE WHEN Tipo = 'S' THEN Valor ELSE 0 END) as despesa
            FROM FluxoCaixa
        """, fetch='one')
        receita = float(financeiro[0]) if financeiro[0] else 0.0
        despesa = float(financeiro[1]) if financeiro[1] else 0.0
        saldo = receita - despesa

        # Busca quantidade de clientes
        total_clientes = executar_query("SELECT COUNT(*) FROM Clientes", fetch='one')[0]

        # Busca quantidade de O.S. ativas (Manutencao ou Pronto)
        total_os_ativas = executar_query("""
            SELECT COUNT(*) FROM ItensEstoque WHERE Status IN ('Manutencao', 'Pronto')
        """, fetch='one')[0]

        # Busca quantidade de produtos com estoque baixo (menor ou igual a 1 unidade disponível)
        baixo_estoque = executar_query("""
            SELECT p.Marca, p.Modelo, COUNT(i.IdItem) AS Qtd
            FROM Produtos p
            LEFT JOIN ItensEstoque i ON p.IdProduto = i.IdProduto AND LOWER(i.Status) = 'disponivel'
            WHERE p.Ativo = true
            GROUP BY p.IdProduto, p.Marca, p.Modelo
            HAVING COUNT(i.IdItem) <= 1
        """, fetch='all')
        total_baixo_estoque = len(baixo_estoque)

        # Renderizando as métricas
        if st.session_state.user_role == 'adm':
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Saldo Líquido</div>
                    <div class="metric-value val-success">R$ {saldo:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Clientes Cadastrados</div>
                    <div class="metric-value val-primary">{total_clientes}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Ordens de Serviço Ativas</div>
                    <div class="metric-value val-warning">{total_os_ativas}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Alertas de Estoque Baixo</div>
                    <div class="metric-value val-danger">{total_baixo_estoque}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("---")
            
            # Grid inferior com Alertas de Estoque Baixo e O.S. Pendentes
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("⚠️ Produtos com Estoque Baixo ou Crítico")
                if baixo_estoque:
                    df_baixo = pd.DataFrame(baixo_estoque, columns=["Marca", "Modelo", "Qtd Disponível"])
                    st.dataframe(df_baixo, use_container_width=True, hide_index=True)
                else:
                    st.success("Estoque saudável! Nenhum produto com estoque crítico.")
                    
            with col_g2:
                st.subheader("🛠️ Ordens de Serviço Ativas (Recentes)")
                os_ativas = executar_query("""
                    SELECT f.IdLancamento, c.Nome, p.Marca, p.Modelo, i.Status, f.Valor
                    FROM FluxoCaixa f
                    JOIN Clientes c ON f.IdCliente = c.IdCliente
                    JOIN ItensEstoque i ON f.IdItem = i.IdItem
                    JOIN Produtos p ON i.IdProduto = p.IdProduto
                    WHERE i.Status IN ('Manutencao', 'Pronto')
                    ORDER BY f.IdLancamento DESC LIMIT 5
                """, fetch='all')
                if os_ativas:
                    df_os = pd.DataFrame(os_ativas, columns=["Nº OS", "Cliente", "Marca", "Modelo", "Status", "Preço (R$)"])
                    st.dataframe(df_os, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma Ordem de Serviço em aberto no momento.")
        else:
            # Lojista vê apenas Clientes Cadastrados e OS Ativas
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Clientes Cadastrados</div>
                    <div class="metric-value val-primary">{total_clientes}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Ordens de Serviço Ativas</div>
                    <div class="metric-value val-warning">{total_os_ativas}</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("---")
            st.subheader("🛠️ Ordens de Serviço Ativas (Recentes)")
            os_ativas = executar_query("""
                SELECT f.IdLancamento, c.Nome, p.Marca, p.Modelo, i.Status
                FROM FluxoCaixa f
                JOIN Clientes c ON f.IdCliente = c.IdCliente
                JOIN ItensEstoque i ON f.IdItem = i.IdItem
                JOIN Produtos p ON i.IdProduto = p.IdProduto
                WHERE i.Status IN ('Manutencao', 'Pronto')
                ORDER BY f.IdLancamento DESC LIMIT 5
            """, fetch='all')
            if os_ativas:
                df_os = pd.DataFrame(os_ativas, columns=["Nº OS", "Cliente", "Marca", "Modelo", "Status"])
                st.dataframe(df_os, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma Ordem de Serviço em aberto no momento.")

    except Exception as e:
        st.error(f"Erro ao carregar painel de indicadores: {e}")

# =========================================================================
# 5. TELA: CLIENTES (CRUD COMPLETO)
# =========================================================================
elif opcao == "👤 Clientes (CRM)":
    st.title("👤 Gerenciamento de Clientes (CRM)")
    aba_lista, aba_cadastrar = st.tabs(["🔍 Consultar e Editar Clientes", "➕ Cadastrar Novo Cliente"])
    
    with aba_cadastrar:
        st.header("Cadastrar Novo Cliente")
        
        # Inicializando session state do CEP de cadastro se nao existir
        if "ultimo_cep_inserido" not in st.session_state:
            st.session_state.ultimo_cep_inserido = ""
        if "cep_data_inserido" not in st.session_state:
            st.session_state.cep_data_inserido = {"logradouro": "", "bairro": "", "localidade": "", "uf": ""}
        if "cep_key_counter" not in st.session_state:
            st.session_state.cep_key_counter = 0

        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0;'>Ficha de Cadastro</h3>", unsafe_allow_html=True)
            
            st.markdown("##### Informações Pessoais")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                nome = st.text_input("Nome Completo:", key="cad_nome")
                whatsapp = st.text_input("WhatsApp (com DDD):", placeholder="Ex: 11988887777", key="cad_whatsapp")
            with col_p2:
                cpf_input = st.text_input("CPF (somente numeros):", placeholder="Ex: 12345678909", max_chars=11, key="cad_cpf")
                email = st.text_input("E-mail:", key="cad_email")
            
            st.markdown("##### Endereço Residencial")
            
            # Input de CEP com busca automatica colocado no inicio do endereco
            cep_key = f"inserir_cep_{st.session_state.cep_key_counter}"
            cep_val = st.text_input("CEP (somente numeros):", placeholder="Ex: 01103010", max_chars=8, key=cep_key, help="Digite os 8 numeros do CEP para buscar o endereco automaticamente")
            cep_clean = re.sub(r'\D', '', cep_val)
            
            if len(cep_clean) == 8 and cep_clean != st.session_state.ultimo_cep_inserido:
                data_cep = buscar_cep(cep_clean)
                if data_cep:
                    st.session_state.cep_data_inserido = data_cep
                    st.session_state.ultimo_cep_inserido = cep_clean
                    st.toast("Endereço preenchido automaticamente!", icon="📍")
                else:
                    st.error("CEP nao localizado.")
            
            col_e1, col_e2, col_e3 = st.columns([3, 1, 2])
            with col_e1:
                logradouro = st.text_input("Logradouro (Rua/Avenida):", value=st.session_state.cep_data_inserido.get("logradouro", ""), key="cad_logradouro")
            with col_e2:
                numero = st.text_input("Numero:", key="cad_numero")
            with col_e3:
                complemento = st.text_input("Complemento:", key="cad_complemento")
                
            col_e4, col_e5, col_e6 = st.columns([2, 2, 1])
            with col_e4:
                bairro = st.text_input("Bairro:", value=st.session_state.cep_data_inserido.get("bairro", ""), key="cad_bairro")
            with col_e5:
                cidade = st.text_input("Cidade:", value=st.session_state.cep_data_inserido.get("localidade", ""), key="cad_cidade")
            with col_e6:
                estado = st.text_input("UF:", value=st.session_state.cep_data_inserido.get("uf", ""), key="cad_estado")
                
            st.write("")
            if st.button("Salvar Cliente", type="primary", use_container_width=True):
                if nome and whatsapp:
                    cpf_clean = re.sub(r'\D', '', cpf_input) if cpf_input else ""
                    if cpf_clean and not validar_cpf(cpf_clean):
                        st.error("Erro: O CPF digitado é inválido!")
                    else:
                        try:
                            executar_query("""
                                INSERT INTO Clientes (Nome, WhatsApp, Email, Documento, CEP, Logradouro, Numero, Complemento, Bairro, Cidade, Estado)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (nome, whatsapp, email if email else None, cpf_clean if cpf_clean else None, 
                                  cep_clean if cep_clean else None, logradouro, numero, complemento, bairro, cidade, estado))
                            
                            # Limpa os campos do formulário redefinindo as chaves no session_state
                            st.session_state.ultimo_cep_inserido = ""
                            st.session_state.cep_data_inserido = {"logradouro": "", "bairro": "", "localidade": "", "uf": ""}
                            st.session_state.cep_key_counter += 1
                            
                            for k in ["cad_nome", "cad_whatsapp", "cad_cpf", "cad_email", "cad_logradouro", "cad_numero", "cad_complemento", "cad_bairro", "cad_cidade", "cad_estado"]:
                                if k in st.session_state:
                                    st.session_state[k] = ""
                                    
                            st.success(f"Cliente '{nome}' cadastrado com sucesso!")
                            st.toast(f"Cliente '{nome}' cadastrado com sucesso!", icon="🎉")
                            st.rerun()
                        except psycopg2.IntegrityError:
                            st.error("Erro: WhatsApp ou CPF já cadastrado no sistema.")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("Nome e WhatsApp são obrigatórios.")
                        
    with aba_lista:
        st.header("Lista de Clientes")
        termo_busca = st.text_input("Buscar cliente por Nome, WhatsApp, CPF ou CEP:")
        
        # Query com filtro atualizada para trazer todos os campos
        query_busca = """
            SELECT IdCliente, Nome, WhatsApp, Email, Documento, CEP, Logradouro, Numero, Complemento, Bairro, Cidade, Estado
            FROM Clientes 
            WHERE Nome ILIKE %s OR WhatsApp ILIKE %s OR Documento ILIKE %s OR CEP ILIKE %s
            ORDER BY Nome ASC
        """
        param_busca = f"%{termo_busca}%"
        clientes = executar_query(query_busca, (param_busca, param_busca, param_busca, param_busca), fetch='all')
        
        if clientes:
            # Mostra tabela simples
            tabela_dados = []
            for c in clientes:
                tabela_dados.append([c[0], c[1], c[2], c[3] if c[3] else "---", c[4] if c[4] else "---", f"{c[6] if c[6] else ''}, {c[7] if c[7] else ''} - {c[10] if c[10] else ''}"])
            df_clientes = pd.DataFrame(tabela_dados, columns=["ID", "Nome", "WhatsApp", "E-mail", "CPF", "Endereco"])
            st.dataframe(df_clientes, use_container_width=True, hide_index=True)
            
            st.write("---")
            st.subheader("Editar / Excluir Cadastro de Cliente")
            
            lista_clientes_select = {f"{c[1]} (WA: {c[2]})": c for c in clientes}
            cliente_selecionado_str = st.selectbox("Selecione o Cliente para Modificar:", list(lista_clientes_select.keys()))
            
            if cliente_selecionado_str:
                cli = lista_clientes_select[cliente_selecionado_str]
                id_cli, nome_cli, wa_cli, email_cli, doc_cli, cep_cli, log_cli, num_cli, comp_cli, bai_cli, cid_cli, est_cli = cli
                
                # Inicializando session state do CEP de edicao para este cliente se nao existir ou se mudou o cliente
                if "cliente_selecionado_id" not in st.session_state or st.session_state.cliente_selecionado_id != id_cli:
                    st.session_state.cliente_selecionado_id = id_cli
                    st.session_state.ultimo_cep_editado = re.sub(r'\D', '', cep_cli) if cep_cli else ""
                    st.session_state.cep_data_editado = {
                        "logradouro": log_cli if log_cli else "",
                        "bairro": bai_cli if bai_cli else "",
                        "localidade": cid_cli if cid_cli else "",
                        "uf": est_cli if est_cli else ""
                    }

                with st.container(border=True):
                    st.markdown(f"#### ✏️ Edicao de Ficha: {nome_cli}")
                    
                    # Input de CEP para edicao fora do form (apenas numeros)
                    cep_edit_input = st.text_input("CEP (somente numeros):", value=st.session_state.ultimo_cep_editado, key="edit_cep_input", max_chars=8)
                    cep_edit_clean = re.sub(r'\D', '', cep_edit_input)
                    
                    if len(cep_edit_clean) == 8 and cep_edit_clean != re.sub(r'\D', '', st.session_state.ultimo_cep_editado):
                        data_cep_edit = buscar_cep(cep_edit_clean)
                        if data_cep_edit:
                            st.session_state.cep_data_editado = data_cep_edit
                            st.session_state.ultimo_cep_editado = cep_edit_clean
                            st.toast("Endereco de edicao auto-preenchido!", icon="📍")
                        else:
                            st.error("CEP nao localizado.")

                    with st.form("form_editar_cliente"):
                        st.markdown("##### Informacoes Pessoais")
                        col_pe1, col_pe2 = st.columns(2)
                        with col_pe1:
                            novo_nome = st.text_input("Nome Completo:", value=nome_cli)
                            novo_whatsapp = st.text_input("WhatsApp:", value=wa_cli)
                        with col_pe2:
                            novo_documento = st.text_input("CPF:", value=doc_cli if doc_cli else "", max_chars=11)
                            novo_email = st.text_input("E-mail:", value=email_cli if email_cli else "")
                            
                        st.markdown("##### Endereco Residencial")
                        col_ee1, col_ee2, col_ee3 = st.columns([3, 1, 2])
                        with col_ee1:
                            novo_log = st.text_input("Logradouro:", value=st.session_state.cep_data_editado.get("logradouro", ""))
                        with col_ee2:
                            novo_num = st.text_input("Numero:", value=num_cli if num_cli else "")
                        with col_ee3:
                            novo_comp = st.text_input("Complemento:", value=comp_cli if comp_cli else "")
                            
                        col_ee4, col_ee5, col_ee6 = st.columns([2, 2, 1])
                        with col_ee4:
                            novo_bai = st.text_input("Bairro:", value=st.session_state.cep_data_editado.get("bairro", ""))
                        with col_ee5:
                            novo_cid = st.text_input("Cidade:", value=st.session_state.cep_data_editado.get("localidade", ""))
                        with col_ee6:
                            novo_est = st.text_input("UF:", value=st.session_state.cep_data_editado.get("uf", ""))
                            
                        st.write("")
                        if st.form_submit_button("Salvar Alteracoes", type="primary", use_container_width=True):
                            if novo_nome and novo_whatsapp:
                                cpf_edit_clean = re.sub(r'\D', '', novo_documento) if novo_documento else ""
                                if cpf_edit_clean and not validar_cpf(cpf_edit_clean):
                                    st.error("Erro: O CPF digitado e invalido!")
                                else:
                                    try:
                                        executar_query("""
                                            UPDATE Clientes 
                                            SET Nome = %s, Documento = %s, WhatsApp = %s, Email = %s,
                                                CEP = %s, Logradouro = %s, Numero = %s, Complemento = %s,
                                                Bairro = %s, Cidade = %s, Estado = %s
                                            WHERE IdCliente = %s
                                        """, (novo_nome, cpf_edit_clean if cpf_edit_clean else None, novo_whatsapp, novo_email if novo_email else None,
                                              cep_edit_clean if cep_edit_clean else None, novo_log, novo_num, novo_comp, novo_bai, novo_cid, novo_est, id_cli))
                                        
                                        # Limpa estado de edicao
                                        if "cliente_selecionado_id" in st.session_state:
                                            del st.session_state.cliente_selecionado_id
                                            
                                        st.success(f"Cadastro de '{novo_nome}' atualizado com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar: {e}")
                            else:
                                st.warning("Nome e WhatsApp sao obrigatorios.")
                    
                    # Exclusão fora do formulário (apenas ADM)
                    if st.session_state.user_role == 'adm':
                        st.write("---")
                        st.write("🗑️ **Excluir Cliente**")
                        confirmar_exclusao = st.checkbox(f"Confirmo que desejo excluir permanentemente o cliente '{nome_cli}' e desvincular suas ordens antigas.", key="conf_del_cli")
                        if st.button("Excluir Cliente Permanentemente", type="primary", disabled=not confirmar_exclusao, use_container_width=True):
                            try:
                                executar_query("DELETE FROM Clientes WHERE IdCliente = %s", (id_cli,))
                                st.success(f"Cliente '{nome_cli}' excluido com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir cliente: {e}")
        else:
            st.info("Nenhum cliente cadastrado ou correspondente a busca.")

# =========================================================================
# 6. TELA: PRODUTOS & ESTOQUE (CRUD COMPLETO)
# =========================================================================
elif opcao == "📦 Produtos & Estoque":
    st.title("📦 Controle de Estoque & Catálogo de Produtos")
    
    if st.session_state.user_role == 'adm':
        aba_inventario, aba_novo_prod = st.tabs(["🔍 Consultar Catálogo & Estoque", "➕ Adicionar Novo Produto ao Catálogo"])
    else:
        aba_inventario = st.container()
        
    if st.session_state.user_role == 'adm':
        with aba_novo_prod:
            st.header("Cadastrar Novo Modelo no Catálogo")
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
                quantidade = st.number_input("Quantidade Inicial de Entrada (Unidades Físicas):", min_value=0, step=1, value=1)
                
                if st.form_submit_button("Adicionar ao Catálogo e Gerar Lote"):
                    if marca and modelo:
                        try:
                            modelo_com_tipo = f"[{tipo_item.split(' ')[1]}] {modelo}"
                            
                            conn = abrir_conexao()
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO Produtos (Marca, Modelo, CustoProduto, ValorMinimo, ValorVenda)
                                VALUES (%s, %s, %s, %s, %s) RETURNING IdProduto
                            """, (marca, modelo_com_tipo, custo, val_minimo, val_venda))
                            id_prod = cursor.fetchone()[0]
                            
                            # Inserindo unidades físicas iniciais
                            for i in range(int(quantidade)):
                                sn_gerado = f"REF-{id_prod}-{i+1}"
                                cursor.execute("""
                                    INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status) 
                                    VALUES (%s, %s, 'Disponivel')
                                """, (id_prod, sn_gerado))
                                
                            conn.commit()
                            conn.close()
                            st.success(f"Produto '{marca} - {modelo_com_tipo}' cadastrado e {quantidade} unidades adicionadas ao estoque!")
                        except Exception as e:
                            st.error(f"Erro ao salvar produto: {e}")
                    else:
                        st.warning("Marca e Modelo são obrigatórios.")
                        
    with aba_inventario:
        st.header("Catálogo Geral da Loja")
        termo_busca = st.text_input("Pesquisar por Marca ou Modelo de Produto:")
        
        # Carrega produtos ativos no catálogo
        query_produtos = """
            SELECT p.IdProduto, p.Marca, p.Modelo, p.CustoProduto, p.ValorMinimo, p.ValorVenda,
                   COUNT(CASE WHEN LOWER(i.Status) = 'disponivel' THEN 1 END) as disponivel,
                   COUNT(i.IdItem) as total
            FROM Produtos p
            LEFT JOIN ItensEstoque i ON p.IdProduto = i.IdProduto
            WHERE p.Ativo = true AND (p.Marca ILIKE %s OR p.Modelo ILIKE %s)
            GROUP BY p.IdProduto, p.Marca, p.Modelo, p.CustoProduto, p.ValorMinimo, p.ValorVenda
            ORDER BY p.Marca, p.Modelo
        """
        param_busca = f"%{termo_busca}%"
        dados_produtos = executar_query(query_produtos, (param_busca, param_busca), fetch='all')
        
        if dados_produtos:
            df_prod = pd.DataFrame(dados_produtos, columns=["ID", "Marca", "Modelo", "Custo (R$)", "Mínimo (R$)", "Venda (R$)", "Disponível", "Total Cadastrado"])
            st.dataframe(df_prod, use_container_width=True, hide_index=True)
            
            st.write("---")
            st.subheader("Gerenciar Catálogo & Unidades de Estoque")
            
            lista_select_produtos = {f"{p[1]} - {p[2]}": p for p in dados_produtos}
            prod_selecionado_str = st.selectbox("Selecione o Produto para Modificar/Gerenciar:", list(lista_select_produtos.keys()))
            
            if prod_selecionado_str:
                prod = lista_select_produtos[prod_selecionado_str]
                id_p, marca_p, modelo_p, custo_p, min_p, venda_p, disp_p, tot_p = prod
                
                if st.session_state.user_role == 'adm':
                    # Layout colunas para dividir edição do produto e gerenciamento de unidades físicas
                    col_edit, col_itens = st.columns([1, 1])
                    
                    with col_edit:
                        st.markdown("#### ✏️ Editar Informações do Catálogo")
                        with st.form(f"form_editar_prod_{id_p}"):
                            nova_marca = st.text_input("Marca:", value=marca_p)
                            novo_modelo = st.text_input("Modelo/Descrição:", value=modelo_p)
                            novo_custo = st.number_input("Custo de Aquisição (R$):", value=float(custo_p), step=10.0)
                            novo_min = st.number_input("Valor Mínimo (R$):", value=float(min_p), step=10.0)
                            novo_venda = st.number_input("Valor Venda (R$):", value=float(venda_p), step=10.0)
                            nova_qtd_disp = st.number_input("Quantidade Disponível em Estoque (Unidades):", value=int(disp_p), min_value=0, step=1, help="Altere para aumentar ou diminuir as unidades físicas disponíveis deste produto.")
                            
                            if st.form_submit_button("Salvar Alterações no Catálogo", type="primary"):
                                try:
                                    conn = abrir_conexao()
                                    cursor = conn.cursor()
                                    
                                    # 1. Atualizar informações básicas do produto
                                    cursor.execute("""
                                        UPDATE Produtos
                                        SET Marca = %s, Modelo = %s, CustoProduto = %s, ValorMinimo = %s, ValorVenda = %s
                                        WHERE IdProduto = %s
                                    """, (nova_marca, novo_modelo, novo_custo, novo_min, novo_venda, id_p))
                                    
                                    # 2. Ajustar quantidade física em estoque
                                    qtd_atual = int(disp_p)
                                    qtd_nova = int(nova_qtd_disp)
                                    
                                    if qtd_nova > qtd_atual:
                                        # Adicionar novas unidades disponíveis
                                        diff = qtd_nova - qtd_atual
                                        for i in range(diff):
                                            cursor.execute("SELECT COUNT(*) FROM ItensEstoque WHERE IdProduto = %s", (id_p,))
                                            contagem = cursor.fetchone()[0]
                                            sn_gerado = f"REF-{id_p}-{contagem + 1}"
                                            cursor.execute("""
                                                INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status) 
                                                VALUES (%s, %s, 'Disponivel')
                                            """, (id_p, sn_gerado))
                                    elif qtd_nova < qtd_atual:
                                        # Remover unidades disponíveis excedentes (começando pelas mais recentes)
                                        diff = qtd_atual - qtd_nova
                                        cursor.execute("""
                                            SELECT IdItem FROM ItensEstoque 
                                            WHERE IdProduto = %s AND LOWER(Status) = 'disponivel'
                                            ORDER BY IdItem DESC LIMIT %s
                                        """, (id_p, diff))
                                        ids_deletar = [row[0] for row in cursor.fetchall()]
                                        if ids_deletar:
                                            cursor.execute("""
                                                DELETE FROM ItensEstoque
                                                WHERE IdItem = ANY(%s)
                                            """, (ids_deletar,))
                                            
                                    conn.commit()
                                    conn.close()
                                    st.success("Catálogo e quantidade de estoque atualizados com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar alterações: {e}")
                                    
                        st.write("---")
                        st.markdown("#### 🗑️ Desativar Produto do Catálogo")
                        confirmar_excluir_prod = st.checkbox(f"Confirmo que desejo ocultar/desativar o produto '{marca_p} - {modelo_p}' para novas vendas (preservando o histórico antigo no banco).", key=f"conf_del_prod_{id_p}")
                        if st.button("Desativar Produto", type="primary", disabled=not confirmar_excluir_prod, key=f"btn_del_prod_{id_p}"):
                            try:
                                # Seta Ativo = false para preservar as vendas e ordens de serviço passadas
                                executar_query("UPDATE Produtos SET Ativo = false WHERE IdProduto = %s", (id_p,))
                                st.success("Produto desativado e ocultado do catálogo com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao desativar produto: {e}")
                                
                    with col_itens:
                        st.markdown("#### 📋 Unidades Físicas (Estoque Individual)")
                        
                        # Carrega as unidades desse produto específico
                        itens_fisicos = executar_query("""
                            SELECT IdItem, NumeroSerie, Status 
                            FROM ItensEstoque 
                            WHERE IdProduto = %s 
                            ORDER BY IdItem ASC
                        """, (id_p,), fetch='all')
                        
                        if itens_fisicos:
                            df_itens = pd.DataFrame(itens_fisicos, columns=["ID Item", "Número de Série / REF", "Status"])
                            st.dataframe(df_itens, use_container_width=True, hide_index=True)
                            
                            # Ações rápidas para alterar status ou remover uma unidade
                            st.write("⚙️ **Modificar Unidade Física Específica**")
                            lista_select_itens = {f"ID: {it[0]} - S/N: {it[1]} ({it[2]})": it for it in itens_fisicos}
                            item_selecionado_str = st.selectbox("Selecione a unidade:", list(lista_select_itens.keys()))
                            
                            if item_selecionado_str:
                                it = lista_select_itens[item_selecionado_str]
                                id_item_it, sn_it, status_it = it
                                
                                col_i1, col_i2 = st.columns(2)
                                with col_i1:
                                    novo_status_it = st.selectbox(
                                        "Novo Status da Unidade:",
                                        ["Disponivel", "Vendido", "Manutencao", "Pronto", "Entregue"],
                                        index=["Disponivel", "Vendido", "Manutencao", "Pronto", "Entregue"].index(status_it)
                                    )
                                    if st.button("Atualizar Status", key=f"btn_status_item_{id_item_it}"):
                                        try:
                                            executar_query("UPDATE ItensEstoque SET Status = %s WHERE IdItem = %s", (novo_status_it, id_item_it))
                                            st.success("Status atualizado!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(e)
                                with col_i2:
                                    st.write("Ações")
                                    if st.button("🗑️ Deletar Unidade", key=f"btn_del_item_{id_item_it}", type="primary"):
                                        try:
                                            executar_query("DELETE FROM ItensEstoque WHERE IdItem = %s", (id_item_it,))
                                            st.success("Unidade removida!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao remover: {e}")
                        else:
                            st.warning("Nenhuma unidade física em estoque.")
                            
                        # Formulário para adicionar nova unidade física desse produto
                        st.write("---")
                        st.markdown("#### ➕ Adicionar Unidade Física Individual")
                        with st.form(f"form_add_unidade_{id_p}", clear_on_submit=True):
                            novo_sn_individual = st.text_input("Número de Série (ou deixe em branco para gerar auto):")
                            if st.form_submit_button("Cadastrar Nova Unidade no Estoque"):
                                try:
                                    conn = abrir_conexao()
                                    cursor = conn.cursor()
                                    if not novo_sn_individual.strip():
                                        cursor.execute("SELECT COUNT(*) FROM ItensEstoque WHERE IdProduto = %s", (id_p,))
                                        contagem = cursor.fetchone()[0]
                                        sn_final_un = f"REF-{id_p}-{contagem + 1}"
                                    else:
                                        sn_final_un = novo_sn_individual
                                        
                                    cursor.execute("""
                                        INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status) 
                                        VALUES (%s, %s, 'Disponivel')
                                    """, (id_p, sn_final_un))
                                    conn.commit()
                                    conn.close()
                                    st.success(f"Unidade '{sn_final_un}' adicionada com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                else:
                    # Lojista vê apenas a listagem geral de unidades físicas
                    st.markdown("#### 📋 Unidades Físicas (Estoque Individual)")
                    try:
                        itens_fisicos = executar_query("""
                            SELECT IdItem, NumeroSerie, Status 
                            FROM ItensEstoque 
                            WHERE IdProduto = %s 
                            ORDER BY IdItem ASC
                        """, (id_p,), fetch='all')
                        
                        if itens_fisicos:
                            df_itens = pd.DataFrame(itens_fisicos, columns=["ID Item", "Número de Série / REF", "Status"])
                            st.dataframe(df_itens, use_container_width=True, hide_index=True)
                        else:
                            st.warning("Nenhuma unidade física em estoque.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
        else:
            st.info("Nenhum produto cadastrado no catálogo.")

# =========================================================================
# 7. TELA: ORDENS DE SERVIÇO / ATENDIMENTOS (CRUD COMPLETO)
# =========================================================================
elif opcao == "📝 Ordens de Serviço (O.S.)":
    st.title("📝 Gerenciamento de Ordens de Serviço & Atendimentos")
    aba_os_consulta, aba_os_abrir = st.tabs(["🔍 Consultar e Atualizar O.S.", "➕ Abrir Novo Atendimento / Venda"])
    
    with aba_os_abrir:
        st.header("Abertura de Atendimento")
        
        # Passo 1: Selecionar Cliente
        lista_clientes_db = executar_query("SELECT IdCliente, Nome, WhatsApp FROM Clientes ORDER BY Nome ASC", fetch='all')
        if not lista_clientes_db:
            st.warning("⚠️ Cadastre um cliente primeiro na aba de Clientes para abrir uma O.S.")
        else:
            dic_cli = {f"{c[1]} (WA: {c[2]})": c[0] for c in lista_clientes_db}
            cliente_os_selecionado = st.selectbox("Selecione o Cliente:", list(dic_cli.keys()))
            id_cli_os = dic_cli[cliente_os_selecionado]
            
            st.write("---")
            tipo_atendimento = st.radio("O que este cliente está solicitando?", ["🛒 Venda de Mercadoria do Estoque", "🛠️ Ordem de Serviço (Conserto / Assistência)"])
            st.write("---")
            
            if tipo_atendimento == "🛒 Venda de Mercadoria do Estoque":
                # Inicializar carrinho no session state caso não exista
                if "carrinho_venda" not in st.session_state:
                    st.session_state.carrinho_venda = []

                # Carregar produtos ativos com estoque disponível
                prod_disp_db = executar_query("""
                    SELECT p.IdProduto, p.Marca, p.Modelo, p.ValorVenda, COUNT(i.IdItem)
                    FROM Produtos p
                    JOIN ItensEstoque i ON p.IdProduto = i.IdProduto
                    WHERE p.Ativo = true AND LOWER(i.Status) = 'disponivel'
                    GROUP BY p.IdProduto, p.Marca, p.Modelo, p.ValorVenda
                """, fetch='all')
                
                if not prod_disp_db:
                    st.error("Não há produtos no catálogo com unidades físicas 'Disponíveis'. Abasteça o estoque primeiro.")
                else:
                    st.markdown("### 🛒 Montagem da Venda (Carrinho)")
                    
                    # Seletor de produtos e quantidades
                    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
                    
                    with col_sel1:
                        dic_prod = {f"{p[1]} - {p[2]} (Qtd Disp: {p[4]})": p for p in prod_disp_db}
                        prod_selecionado_venda = st.selectbox("Selecione o Produto:", list(dic_prod.keys()), key="select_prod_cart")
                    
                    p_info = dic_prod[prod_selecionado_venda]
                    id_prod_venda, marca_venda, modelo_venda, preco_venda, qtd_disponivel_item = p_info
                    
                    with col_sel2:
                        qtd_venda = st.number_input(
                            "Quantidade:", 
                            min_value=1, 
                            max_value=int(qtd_disponivel_item), 
                            value=1, 
                            step=1,
                            key="input_qtd_cart"
                        )
                    
                    with col_sel3:
                        preco_final_unitario = st.number_input(
                            "Preço Unitário (R$):", 
                            min_value=0.0, 
                            value=float(preco_venda), 
                            step=10.0,
                            key="input_preco_cart"
                        )
                    
                    # Botão para adicionar ao carrinho
                    if st.button("➕ Adicionar ao Carrinho", use_container_width=True):
                        # Verifica se o produto já está no carrinho
                        existente = False
                        for item in st.session_state.carrinho_venda:
                            if item["id_produto"] == id_prod_venda:
                                # Verifica se a soma das quantidades não excede o estoque disponível
                                nova_qtd_total = item["qtd"] + qtd_venda
                                if nova_qtd_total > qtd_disponivel_item:
                                    st.error(f"Erro: Quantidade total no carrinho ({nova_qtd_total}) excede o estoque disponível ({qtd_disponivel_item}).")
                                else:
                                    item["qtd"] = nova_qtd_total
                                    item["preco_unitario"] = preco_final_unitario  # Atualiza o preço
                                existente = True
                                break
                        
                        if not existente:
                            st.session_state.carrinho_venda.append({
                                "id_produto": id_prod_venda,
                                "marca": marca_venda,
                                "modelo": modelo_venda,
                                "qtd": int(qtd_venda),
                                "preco_unitario": float(preco_final_unitario)
                            })
                        st.toast("Item adicionado ao carrinho!", icon="🛒")
                        st.rerun()

                    # Exibição do Carrinho
                    if st.session_state.carrinho_venda:
                        st.write("---")
                        st.markdown("#### 📦 Itens no Carrinho")
                        
                        tabela_carrinho = []
                        total_geral = 0.0
                        for idx, item in enumerate(st.session_state.carrinho_venda):
                            subtotal = item["qtd"] * item["preco_unitario"]
                            total_geral += subtotal
                            tabela_carrinho.append([
                                f"{item['marca']} - {item['modelo']}",
                                item["qtd"],
                                f"R$ {item['preco_unitario']:.2f}",
                                f"R$ {subtotal:.2f}",
                                idx
                            ])
                        
                        # Mostra em uma tabela do Pandas para visualização limpa
                        df_cart = pd.DataFrame(
                            [[row[0], row[1], row[2], row[3]] for row in tabela_carrinho], 
                            columns=["Produto", "Quantidade", "Preço Unitário", "Subtotal"]
                        )
                        st.dataframe(df_cart, use_container_width=True, hide_index=True)
                        
                        # Opção para remover item individual do carrinho
                        col_rem1, col_rem2 = st.columns([3, 1])
                        with col_rem1:
                            st.markdown(f"### ⚖️ **Total Geral da Venda:** <span style='color:#10B981; font-weight: 700; font-size: 24px;'>R$ {total_geral:,.2f}</span>", unsafe_allow_html=True)
                        with col_rem2:
                            item_remover_idx = st.selectbox(
                                "Remover item:", 
                                options=range(len(st.session_state.carrinho_venda)),
                                format_func=lambda x: f"{st.session_state.carrinho_venda[x]['marca']} - {st.session_state.carrinho_venda[x]['modelo']}",
                                key="remove_select_cart"
                            )
                            if st.button("🗑️ Remover", key="btn_remove_cart"):
                                st.session_state.carrinho_venda.pop(item_remover_idx)
                                st.toast("Item removido do carrinho!", icon="🗑️")
                                st.rerun()
                                
                        st.write("---")
                        observacoes_venda = st.text_area("Observações da Venda / Forma de Pagamento:", placeholder="Ex: Venda realizada no cartão de crédito em 3x.")
                        
                        col_actions1, col_actions2 = st.columns(2)
                        with col_actions1:
                            if st.button("❌ Limpar Carrinho", use_container_width=True):
                                st.session_state.carrinho_venda = []
                                st.toast("Carrinho limpo!", icon="🧹")
                                st.rerun()
                                
                        with col_actions2:
                            if st.button("🛒 Confirmar e Finalizar Venda", type="primary", use_container_width=True):
                                try:
                                    conn = abrir_conexao()
                                    cursor = conn.cursor()
                                    
                                    # Gera o CodigoVenda único para esta venda agrupada
                                    codigo_venda = f"VND-{obter_agora_sp().strftime('%Y%m%d-%H%M%S')}-{id_cli_os}"
                                    
                                    # Processa cada item do carrinho
                                    for item in st.session_state.carrinho_venda:
                                        id_p_venda = item["id_produto"]
                                        qtd_solicitada = item["qtd"]
                                        preco_u = item["preco_unitario"]
                                        
                                        # Pega a quantidade de unidades físicas disponíveis correspondente
                                        cursor.execute("""
                                            SELECT IdItem FROM ItensEstoque 
                                            WHERE IdProduto = %s AND LOWER(Status) = 'disponivel' 
                                            ORDER BY IdItem ASC LIMIT %s
                                        """, (id_p_venda, qtd_solicitada))
                                        itens_fisicos = cursor.fetchall()
                                        
                                        if len(itens_fisicos) < qtd_solicitada:
                                            st.error(f"Erro: As unidades disponíveis para '{item['marca']} {item['modelo']}' foram vendidas por outro terminal.")
                                            conn.rollback()
                                            conn.close()
                                            st.stop()
                                            
                                        # Atualiza e insere cada unidade física no caixa
                                        for row_it in itens_fisicos:
                                            id_item_venda = row_it[0]
                                            # Atualiza status do item físico para Vendido
                                            cursor.execute("UPDATE ItensEstoque SET Status = 'Vendido' WHERE IdItem = %s", (id_item_venda,))
                                            
                                            # Grava no fluxo de caixa individualmente para rastreamento de número de série e fechamento financeiro, vinculando ao mesmo CodigoVenda
                                            cursor.execute("""
                                                INSERT INTO FluxoCaixa (IdItem, IdCliente, Tipo, Valor, Descricao, CodigoVenda)
                                                VALUES (%s, %s, 'E', %s, %s, %s)
                                            """, (id_item_venda, id_cli_os, preco_u, f"[VENDA MULTIPLA] - {observacoes_venda}", codigo_venda))
                                            
                                    conn.commit()
                                    conn.close()
                                    st.session_state.carrinho_venda = []  # Limpa o carrinho pós venda
                                    st.success("Venda múltipla efetuada e gravada com sucesso!")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao processar venda múltipla: {e}")
                    else:
                        st.info("O carrinho está vazio. Selecione um produto acima e clique em 'Adicionar ao Carrinho' para iniciar a venda.")
            else:
                # Ordem de Serviço / Assistência
                col_m1, col_m2 = st.columns(2)
                with col_m1: marca_equipamento = st.text_input("Marca do Aparelho (Ex: Dell, Apple):")
                with col_m2: modelo_equipamento = st.text_input("Modelo / Configuração (Ex: Inspiron 15, Macbook Pro):")
                sn_equipamento = st.text_input("Número de Série do Equipamento (Opcional):")
                valor_os = st.number_input("Preço Inicial/Estimado do Conserto (R$):", value=0.0, min_value=0.0)
                defeito_os = st.text_area("Defeito / Relato do Cliente / Diagnóstico Inicial:")
                
                if st.button("Abrir Ordem de Serviço", type="primary"):
                    if marca_equipamento and modelo_equipamento:
                        try:
                            conn = abrir_conexao()
                            cursor = conn.cursor()
                            
                            # Cadastra um "produto" temporário para esta O.S. no catálogo
                            modelo_os_com_tipo = f"[Notebook] {modelo_equipamento}"
                            cursor.execute("""
                                INSERT INTO Produtos (Marca, Modelo, CustoProduto, ValorMinimo, ValorVenda)
                                VALUES (%s, %s, 0, 0, %s) RETURNING IdProduto;
                            """, (marca_equipamento, modelo_os_com_tipo, valor_os))
                            id_prod_os = cursor.fetchone()[0]
                            
                            # Cadastra o item com status 'Manutencao'
                            sn_final_os = sn_equipamento if sn_equipamento.strip() else f"OS-{id_prod_os}"
                            cursor.execute("""
                                INSERT INTO ItensEstoque (IdProduto, NumeroSerie, Status)
                                VALUES (%s, %s, 'Manutencao') RETURNING IdItem;
                            """, (id_prod_os, sn_final_os))
                            id_item_os = cursor.fetchone()[0]
                            
                            # Cria a O.S. no Caixa/Lançamentos
                            cursor.execute("""
                                INSERT INTO FluxoCaixa (IdItem, IdCliente, Tipo, Valor, Descricao)
                                VALUES (%s, %s, 'E', %s, %s) RETURNING IdLancamento;
                            """, (id_item_os, id_cli_os, valor_os, f"[ASSISTENCIA] - {defeito_os}"))
                            id_lancamento_os = cursor.fetchone()[0]
                            
                            conn.commit()
                            conn.close()
                            st.success(f"Ordem de Serviço Nº {id_lancamento_os} aberta com sucesso para o aparelho '{marca_equipamento} - {modelo_equipamento}'!")
                        except Exception as e:
                            st.error(f"Erro ao criar O.S.: {e}")
                    else:
                        st.warning("Marca e Modelo do Equipamento são obrigatórios.")
                        
    with aba_os_consulta:
        st.header("Gerenciar Atendimentos & Ordens de Serviço")
        termo_busca_os = st.text_input("Pesquisar O.S. por ID (Número), Nome do Cliente ou Serial:")
        
        # Query detalhada de O.S. e Vendas (incluindo WhatsApp do cliente, custo do produto e ID do produto)
        query_os = """
            SELECT f.IdLancamento, c.Nome, p.Marca, p.Modelo, i.NumeroSerie, i.Status, f.Valor, f.Descricao, f.DataLancamento, i.IdItem, c.IdCliente, c.WhatsApp, f.CodigoVenda, p.CustoProduto, p.IdProduto
            FROM FluxoCaixa f
            JOIN Clientes c ON f.IdCliente = c.IdCliente
            JOIN ItensEstoque i ON f.IdItem = i.IdItem
            JOIN Produtos p ON i.IdProduto = p.IdProduto
            WHERE CAST(f.IdLancamento AS TEXT) ILIKE %s OR c.Nome ILIKE %s OR i.NumeroSerie ILIKE %s OR f.CodigoVenda ILIKE %s
            ORDER BY f.IdLancamento DESC
        """
        param_busca_os = f"%{termo_busca_os}%"
        atendimentos = executar_query(query_os, (param_busca_os, param_busca_os, param_busca_os, param_busca_os), fetch='all')
        
        if atendimentos:
            # Agrupar atendimentos por CodigoVenda para vendas agrupadas, mantendo O.S. e vendas avulsas separadas
            atendimentos_agrupados = {}
            for a in atendimentos:
                id_lanc, nome_cli, marca, modelo, sn, status, valor, desc, data, id_item, id_cli, whats, codigo_venda, custo_prod, id_prod_os = a
                data = converter_para_sp(data)
                is_assistencia = desc.startswith("[ASSISTENCIA]")
                
                if is_assistencia:
                    key = f"OS-{id_lanc}"
                    atendimentos_agrupados[key] = {
                        "tipo": "OS",
                        "id_lanc": id_lanc,
                        "nome_cli": nome_cli,
                        "produtos_resumo": f"{marca} {modelo}",
                        "seriais": sn,
                        "status": status,
                        "valor_total": float(valor),
                        "descricao": desc,
                        "data": data,
                        "id_cli": id_cli,
                        "whats": whats,
                        "custo_produto": float(custo_prod) if custo_prod else 0.0,
                        "id_prod_os": id_prod_os,
                        "itens": [{
                            "id_lanc": id_lanc,
                            "id_item": id_item,
                            "marca": marca,
                            "modelo": modelo,
                            "sn": sn,
                            "valor": float(valor),
                            "desc": desc
                        }],
                        "codigo_venda": None
                    }
                else:
                    if codigo_venda:
                        key = codigo_venda
                    else:
                        key = f"VND-OLD-{id_lanc}"
                        
                    if key not in atendimentos_agrupados:
                        atendimentos_agrupados[key] = {
                            "tipo": "VENDA",
                            "id_lanc": id_lanc,
                            "nome_cli": nome_cli,
                            "produtos_resumo_dict": {},
                            "seriais_list": [],
                            "status": "Vendido",
                            "valor_total": 0.0,
                            "descricao": desc,
                            "data": data,
                            "id_cli": id_cli,
                            "whats": whats,
                            "custo_produto": 0.0,
                            "id_prod_os": None,
                            "itens": [],
                            "codigo_venda": codigo_venda
                        }
                    
                    group = atendimentos_agrupados[key]
                    group["valor_total"] += float(valor)
                    prod_key = f"{marca} {modelo}"
                    group["produtos_resumo_dict"][prod_key] = group["produtos_resumo_dict"].get(prod_key, 0) + 1
                    if sn:
                        group["seriais_list"].append(sn)
                    group["itens"].append({
                        "id_lanc": id_lanc,
                        "id_item": id_item,
                        "marca": marca,
                        "modelo": modelo,
                        "sn": sn,
                        "valor": float(valor),
                        "desc": desc
                    })

            lista_atendimentos_processada = []
            for key, group in atendimentos_agrupados.items():
                if group["tipo"] == "VENDA":
                    prod_parts = [f"{qtd}x {prod}" for prod, qtd in group["produtos_resumo_dict"].items()]
                    group["produtos_resumo"] = ", ".join(prod_parts)
                    group["seriais"] = ", ".join(sorted(list(set(group["seriais_list"]))))
                lista_atendimentos_processada.append(group)

            # Transforma em DataFrame para listar
            dados_df = []
            for a in lista_atendimentos_processada:
                no_exibicao = a["codigo_venda"] if a["codigo_venda"] else f"Venda Avulsa #{a['id_lanc']}"
                if a["tipo"] == "OS":
                    no_exibicao = f"OS #{a['id_lanc']}"
                    
                dados_df.append([
                    no_exibicao,
                    a["nome_cli"],
                    a["produtos_resumo"],
                    a["seriais"],
                    a["status"].upper(),
                    a["valor_total"],
                    a["data"].strftime('%d/%m/%Y %H:%M')
                ])
            df_atend = pd.DataFrame(dados_df, columns=["Nº OS/Venda", "Cliente", "Equipamento/Produto", "Nº Série", "Status", "Preço (R$)", "Data"])
            st.dataframe(df_atend, use_container_width=True, hide_index=True)
            
            st.write("---")
            st.subheader("Atualizar Informações ou Excluir Lançamento de O.S./Venda")
            
            dic_selecao_os = {}
            for a in lista_atendimentos_processada:
                if a["tipo"] == "OS":
                    key = f"OS Nº {a['id_lanc']} - Cliente: {a['nome_cli']} ({a['produtos_resumo']})"
                else:
                    ref_id = a["codigo_venda"] if a["codigo_venda"] else f"ANTIGA-{a['id_lanc']}"
                    key = f"VENDA: {ref_id} - Cliente: {a['nome_cli']} (Total: R$ {a['valor_total']:.2f})"
                dic_selecao_os[key] = a
                
            os_selecionada_str = st.selectbox("Selecione o Atendimento para Editar/Deletar:", list(dic_selecao_os.keys()))
            
            if os_selecionada_str:
                atend_sel = dic_selecao_os[os_selecionada_str]
                
                if atend_sel["tipo"] == "OS":
                    item_os = atend_sel["itens"][0]
                    id_lanc_os = atend_sel["id_lanc"]
                    nome_cli = atend_sel["nome_cli"]
                    marca_p = item_os["marca"]
                    modelo_p = item_os["modelo"]
                    sn_os = item_os["sn"]
                    status_os = atend_sel["status"]
                    valor_os = atend_sel["valor_total"]
                    desc_os = atend_sel["descricao"]
                    data_os = atend_sel["data"]
                    id_item_os = item_os["id_item"]
                    id_cli_os = atend_sel["id_cli"]
                    whats_cli = atend_sel["whats"]
                    custo_os = atend_sel["custo_produto"]
                    id_prod_os = atend_sel["id_prod_os"]
                    
                    col_os_e, col_os_d = st.columns([2, 1])
                    
                    with col_os_e:
                        st.markdown(f"#### ✏️ Modificar Detalhes da OS Nº {id_lanc_os}")
                        with st.form(f"form_editar_os_{id_lanc_os}"):
                            novo_valor_os = st.number_input("Valor Final Cobrado (R$):", value=float(valor_os), min_value=0.0)
                            novo_custo_os = st.number_input("Custo da(s) Peça(s) Comprada(s) (R$):", value=float(custo_os), min_value=0.0)
                            novo_sn_os = st.text_input("Número de Série/REF:", value=sn_os)
                            novo_desc_os = st.text_area("Histórico / Diagnóstico Técnico / Detalhes:", value=desc_os)
                            
                            col_os_btn = st.columns(2)
                            with col_os_btn[0]:
                                if st.form_submit_button("Salvar Modificações", type="primary"):
                                    try:
                                        conn = abrir_conexao()
                                        cursor = conn.cursor()
                                        # Atualiza valor e descrição no FluxoCaixa
                                        cursor.execute("""
                                            UPDATE FluxoCaixa 
                                            SET Valor = %s, Descricao = %s 
                                            WHERE IdLancamento = %s
                                        """, (novo_valor_os, novo_desc_os, id_lanc_os))
                                        # Atualiza custo do produto em Produtos
                                        cursor.execute("""
                                            UPDATE Produtos 
                                            SET CustoProduto = %s 
                                            WHERE IdProduto = %s
                                        """, (novo_custo_os, id_prod_os))
                                        # Atualiza número de série do equipamento no ItensEstoque
                                        cursor.execute("""
                                            UPDATE ItensEstoque 
                                            SET NumeroSerie = %s 
                                            WHERE IdItem = %s
                                        """, (novo_sn_os, id_item_os))
                                        conn.commit()
                                        conn.close()
                                        st.success("O.S. atualizada com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao salvar alterações: {e}")
                                        
                        st.write("---")
                        st.markdown("#### ⚙️ Controle de Status da Assistência")
                        col_st1, col_st2, col_st3 = st.columns(3)
                        with col_st1:
                            if st.button("🛠️ Em Manutenção", key=f"btn_st_man_{id_lanc_os}", disabled=(status_os == "Manutencao")):
                                executar_query("UPDATE ItensEstoque SET Status = 'Manutencao' WHERE IdItem = %s", (id_item_os,))
                                st.success("Status: Em Manutenção")
                                st.rerun()
                        with col_st2:
                            if st.button("🔵 Pronto para Retirada", key=f"btn_st_pro_{id_lanc_os}", disabled=(status_os == "Pronto")):
                                executar_query("UPDATE ItensEstoque SET Status = 'Pronto' WHERE IdItem = %s", (id_item_os,))
                                st.success("Status: Pronto para Retirada")
                                st.rerun()
                        with col_st3:
                            if st.button("🟢 Entregue / Finalizado", key=f"btn_st_ent_{id_lanc_os}", disabled=(status_os == "Entregue")):
                                executar_query("UPDATE ItensEstoque SET Status = 'Entregue' WHERE IdItem = %s", (id_item_os,))
                                st.success("Status: Finalizado e Entregue")
                                st.rerun()
                        
                        st.write("")
                        st.markdown("#### 📲 Comunicar Cliente via WhatsApp")
                        
                        whats_limpo = re.sub(r'\D', '', whats_cli) if whats_cli else ""
                        if whats_limpo:
                            if not whats_limpo.startswith("55"):
                                whats_limpo = "55" + whats_limpo
                                
                            msg_manutencao = f"Olá, {nome_cli}! O seu equipamento {marca_p} {modelo_p} (Serial: {sn_os}) da Ordem de Serviço Nº {id_lanc_os} já está em manutenção na nossa assistência técnica. Assim que estiver pronto, entraremos em contato!"
                            msg_pronto = f"Olá, {nome_cli}! Temos boas notícias: o seu equipamento {marca_p} {modelo_p} (Serial: {sn_os}) da Ordem de Serviço Nº {id_lanc_os} está PRONTO! Você já pode vir retirá-lo na nossa loja. Valor final: R$ {valor_os:.2f}."
                            msg_entregue = f"Olá, {nome_cli}! O seu equipamento {marca_p} {modelo_p} (Serial: {sn_os}) da Ordem de Serviço Nº {id_lanc_os} foi entregue com sucesso e a O.S. foi finalizada. Agradecemos a preferência pela Infinity Tech!"
                            
                            import urllib.parse
                            link_man = f"https://wa.me/{whats_limpo}?text={urllib.parse.quote(msg_manutencao)}"
                            link_pro = f"https://wa.me/{whats_limpo}?text={urllib.parse.quote(msg_pronto)}"
                            link_ent = f"https://wa.me/{whats_limpo}?text={urllib.parse.quote(msg_entregue)}"
                            
                            col_w1, col_w2, col_w3 = st.columns(3)
                            with col_w1:
                                st.link_button("🛠️ Enviar: Em Manutenção", link_man, use_container_width=True)
                            with col_w2:
                                st.link_button("🔵 Enviar: Pronto p/ Retirada", link_pro, use_container_width=True)
                            with col_w3:
                                st.link_button("🟢 Enviar: Equipamento Entregue", link_ent, use_container_width=True)
                        else:
                            st.warning("⚠️ Cliente não possui WhatsApp cadastrado para enviar atualizações.")
                            
                        # Exclusão fora do formulário (apenas ADM)
                        if st.session_state.user_role == 'adm':
                            st.write("---")
                            st.markdown("#### 🗑️ Cancelar / Excluir Ordem de Serviço")
                            confirmar_excluir_os = st.checkbox(f"Confirmo que desejo apagar definitivamente a OS Nº {id_lanc_os}.", key=f"conf_del_os_{id_lanc_os}")
                            if st.button("Excluir Ordem de Serviço", type="primary", disabled=not confirmar_excluir_os, key=f"btn_del_os_{id_lanc_os}"):
                                try:
                                    executar_query("DELETE FROM FluxoCaixa WHERE IdLancamento = %s", (id_lanc_os,))
                                    st.success("Ordem de Serviço apagada com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir O.S.: {e}")
                                    
                    with col_os_d:
                        st.markdown("#### 🖨️ Comprovante de Balcão")
                        html_recibo = f"""
                        <html>
                        <head>
                            <style>
                                @media print {{ body {{ width: 72mm; font-family: monospace; font-size: 11px; margin: 0; }} }}
                                .recibo {{ width: 240px; font-family: monospace; padding: 2px; line-height: 1.2; color: #000; }}
                                .centralizado {{ text-align: center; }}
                                .linha {{ border-top: 1px dashed #000; margin: 4px 0; }}
                                .espaco-assinatura {{ margin-top: 25px; text-align: center; }}
                            </style>
                        </head>
                        <body>
                            <div class="recibo">
                                <div class="centralizado">
                                    <strong>** INFINITY TECH **</strong><br>
                                    CNPJ: 67.113.214/0001-45<br>
                                    Assistencia Tecnica e Vendas<br>
                                    Rua Santa Efigenia, 264 Box 9-A<br>
                                    Sao Paulo - SP<br>
                                    Whats: (11) 97086-8573<br>
                                    ----------------------------
                                </div>
                                <strong>COMPROVANTE O.S. NO {id_lanc_os}</strong><br>
                                Data: {data_os.strftime('%d/%m/%Y %H:%M')}<br>
                                <div class="linha"></div>
                                <strong>CLIENTE:</strong> {nome_cli}<br>
                                <strong>WHATS:</strong> (Disponível no sistema)<br>
                                <div class="linha"></div>
                                <strong>PROD/APARELHO:</strong> {marca_p} {modelo_p}<br>
                                <strong>S/N ou REF:</strong> {sn_os}<br>
                                <strong>STATUS:</strong> {status_os.upper()}<br>
                                <strong>DETALHES:</strong> {desc_os}<br>
                                <div class="linha"></div>
                                <strong>VALOR BRUTO: R$ {valor_os:.2f}</strong><br>
                                <div class="linha"></div>
                                <div class="espaco-assinatura">___________________________<br>Assinatura do Cliente</div>
                                <div class="espaco-assinatura">___________________________<br>Assinatura InfinityTech</div>
                            </div>
                            <script>window.print();</script>
                        </body>
                        </html>
                        """
                        if st.button("🖨️ Imprimir Cupom de Balcão", key=f"btn_print_{id_lanc_os}"):
                            components.html(html_recibo, height=1)
                            st.info("💡 Janela de impressão enviada ao navegador.")
                            
                else:
                    # É uma VENDA agrupada ou individual
                    codigo_venda = atend_sel["codigo_venda"]
                    id_lanc_ref = atend_sel["id_lanc"]
                    nome_cli = atend_sel["nome_cli"]
                    valor_total = atend_sel["valor_total"]
                    desc_venda = atend_sel["descricao"]
                    data_venda = atend_sel["data"]
                    id_cli_os = atend_sel["id_cli"]
                    whats_cli = atend_sel["whats"]
                    itens_venda = atend_sel["itens"]
                    
                    col_os_e, col_os_d = st.columns([2, 1])
                    
                    with col_os_e:
                        st.markdown(f"#### ✏️ Detalhes da Venda: {codigo_venda if codigo_venda else f'Nº {id_lanc_ref}'}")
                        
                        # Tabela de itens da venda
                        tabela_detalhe_itens = []
                        for it in itens_venda:
                            tabela_detalhe_itens.append([
                                f"{it['marca']} - {it['modelo']}",
                                it["sn"] if it["sn"] else "---",
                                f"R$ {it['valor']:.2f}"
                            ])
                        df_detalhe = pd.DataFrame(tabela_detalhe_itens, columns=["Produto", "Número de Série / REF", "Valor Unitário"])
                        st.dataframe(df_detalhe, use_container_width=True, hide_index=True)
                        st.markdown(f"### ⚖️ **Total Geral:** <span style='color:#10B981; font-weight: 700; font-size: 24px;'>R$ {valor_total:,.2f}</span>", unsafe_allow_html=True)
                        
                        # Form para editar observação/pagamento
                        with st.form(f"form_editar_venda_{codigo_venda if codigo_venda else id_lanc_ref}"):
                            nova_desc_venda = st.text_area("Observações da Venda / Forma de Pagamento:", value=desc_venda)
                            if st.form_submit_button("Salvar Observações", type="primary"):
                                try:
                                    if codigo_venda:
                                        executar_query("""
                                            UPDATE FluxoCaixa 
                                            SET Descricao = %s 
                                            WHERE CodigoVenda = %s
                                        """, (nova_desc_venda, codigo_venda))
                                    else:
                                        executar_query("""
                                            UPDATE FluxoCaixa 
                                            SET Descricao = %s 
                                            WHERE IdLancamento = %s
                                        """, (nova_desc_venda, id_lanc_ref))
                                    st.success("Observações atualizadas com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")
                                    
                        # Exclusão da venda (apenas ADM)
                        if st.session_state.user_role == 'adm':
                            st.write("---")
                            st.markdown("#### 🗑️ Cancelar / Excluir Venda")
                            confirmar_excluir_venda = st.checkbox(f"Confirmo que desejo cancelar esta venda. Isso removerá os registros financeiros e retornará os itens ao estoque como 'Disponível'.", key=f"conf_del_vnd_{codigo_venda if codigo_venda else id_lanc_ref}")
                            if st.button("Excluir Venda e Devolver Itens ao Estoque", type="primary", disabled=not confirmar_excluir_venda, key=f"btn_del_vnd_{codigo_venda if codigo_venda else id_lanc_ref}"):
                                try:
                                    conn = abrir_conexao()
                                    cursor = conn.cursor()
                                    
                                    # Pega todos os itens da venda para estornar estoque
                                    ids_itens_estornar = [it["id_item"] for it in itens_venda if it["id_item"] is not None]
                                    
                                    if ids_itens_estornar:
                                        cursor.execute("""
                                            UPDATE ItensEstoque 
                                            SET Status = 'Disponivel' 
                                            WHERE IdItem = ANY(%s)
                                        """, (ids_itens_estornar,))
                                        
                                    if codigo_venda:
                                        cursor.execute("DELETE FROM FluxoCaixa WHERE CodigoVenda = %s", (codigo_venda,))
                                    else:
                                        cursor.execute("DELETE FROM FluxoCaixa WHERE IdLancamento = %s", (id_lanc_ref,))
                                        
                                    conn.commit()
                                    conn.close()
                                    st.success("Venda cancelada com sucesso e estoque devolvido!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao cancelar: {e}")
                                    
                    with col_os_d:
                        st.markdown("#### 🖨️ Comprovante de Balcão")
                        
                        # Constrói a listagem HTML dos itens vendidos
                        itens_html_list = ""
                        for it in itens_venda:
                            itens_html_list += f"""
                            <tr>
                                <td style='padding: 3px 0; font-family: monospace; font-size: 11px;'>{it['marca']} {it['modelo']}<br><small>S/N: {it['sn'] if it['sn'] else 'N/A'}</small></td>
                                <td style='text-align: right; vertical-align: top; font-family: monospace; font-size: 11px;'>R$ {it['valor']:.2f}</td>
                            </tr>
                            """
                            
                        html_recibo_venda = f"""
                        <html>
                        <head>
                            <style>
                                @media print {{ body {{ width: 72mm; font-family: monospace; font-size: 11px; margin: 0; }} }}
                                .recibo {{ width: 240px; font-family: monospace; padding: 2px; line-height: 1.2; color: #000; }}
                                .centralizado {{ text-align: center; }}
                                .linha {{ border-top: 1px dashed #000; margin: 4px 0; }}
                                .espaco-assinatura {{ margin-top: 25px; text-align: center; }}
                                table {{ width: 100%; border-collapse: collapse; }}
                            </style>
                        </head>
                        <body>
                            <div class="recibo">
                                <div class="centralizado">
                                    <strong>** INFINITY TECH **</strong><br>
                                    CNPJ: 67.113.214/0001-45<br>
                                    Assistencia Tecnica e Vendas<br>
                                    Rua Santa Efigenia, 264 Box 9-A<br>
                                    Sao Paulo - SP<br>
                                    Whats: (11) 97086-8573<br>
                                    ----------------------------
                                </div>
                                <strong>COMPROVANTE DE VENDA</strong><br>
                                ID: {codigo_venda if codigo_venda else f'VND-{id_lanc_ref}'}<br>
                                Data: {data_venda.strftime('%d/%m/%Y %H:%M')}<br>
                                <div class="linha"></div>
                                <strong>CLIENTE:</strong> {nome_cli}<br>
                                <div class="linha"></div>
                                <table>
                                    <thead>
                                        <tr style='border-bottom: 1px dashed #000;'>
                                            <th style='text-align: left; font-family: monospace; font-size: 11px;'>Item</th>
                                            <th style='text-align: right; font-family: monospace; font-size: 11px;'>Preço</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {itens_html_list}
                                    </tbody>
                                </table>
                                <div class="linha"></div>
                                <strong>TOTAL GERAL: R$ {valor_total:.2f}</strong><br>
                                <div class="linha"></div>
                                <div style='font-size: 10px; margin-top: 5px;'>
                                    <strong>Obs:</strong> {desc_venda}
                                </div>
                                <div class="espaco-assinatura">___________________________<br>Assinatura do Cliente</div>
                                <div class="espaco-assinatura">___________________________<br>Assinatura InfinityTech</div>
                            </div>
                            <script>window.print();</script>
                        </body>
                        </html>
                        """
                        if st.button("🖨️ Imprimir Cupom de Venda", key=f"btn_print_venda_{codigo_venda if codigo_venda else id_lanc_ref}"):
                            components.html(html_recibo_venda, height=1)
                            st.info("💡 Janela de impressão enviada ao navegador.")
        else:
            st.info("Nenhuma ordem de serviço ou atendimento localizado.")

# =========================================================================
# 8. TELA: FINANCEIRO & CAIXA (CRUD COMPLETO)
# =========================================================================
elif opcao == "📊 Financeiro & Caixa":
    st.title("📊 Painel Financeiro & Fluxo de Caixa")
    aba_lancamentos, aba_novo_lanc = st.tabs(["📊 Histórico de Caixa", "💸 Lançar Entrada/Saída Manual"])
    
    with aba_novo_lanc:
        st.header("Lançamento Financeiro Manual")
        st.markdown("Use esta tela para registrar despesas operacionais (aluguel, peças, café) ou receitas diretas avulsas.")
        with st.form("form_novo_lancamento", clear_on_submit=True):
            tipo_lanc = st.selectbox("Tipo de Lançamento:", ["Entrada (Receita)", "Saída (Despesa)"])
            valor_lanc = st.number_input("Valor do Lançamento (R$):", min_value=0.01, step=1.00)
            desc_lanc = st.text_area("Descrição/Justificativa:")
            
            if st.form_submit_button("Gravar Transação"):
                try:
                    tipo_char = 'E' if tipo_lanc == "Entrada (Receita)" else 'S'
                    executar_query("""
                        INSERT INTO FluxoCaixa (Tipo, Valor, Descricao)
                        VALUES (%s, %s, %s)
                    """, (tipo_char, valor_lanc, desc_lanc))
                    st.success("Lançamento financeiro registrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar lançamento: {e}")
                    
    with aba_lancamentos:
        st.header("Histórico de Fluxo de Caixa")
        
        # Filtros de data e tipo
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            agora_sp = obter_agora_sp()
            data_inicio = st.date_input("De:", value=datetime(agora_sp.year, agora_sp.month, 1))
        with col_f2:
            data_fim = st.date_input("Até:", value=obter_agora_sp())
        with col_f3:
            tipo_filtro = st.selectbox("Filtrar por Tipo:", ["Todos", "Entradas (Receitas)", "Saídas (Despesas)"])
            
        # Montagem da Query Dinâmica
        query_caixa = """
            SELECT f.IdLancamento, f.Tipo, f.Valor, f.Descricao, f.DataLancamento, c.Nome
            FROM FluxoCaixa f
            LEFT JOIN Clientes c ON f.IdCliente = c.IdCliente
            WHERE CAST(f.DataLancamento AS DATE) BETWEEN %s AND %s
        """
        params_caixa = [data_inicio, data_fim]
        
        if tipo_filtro == "Entradas (Receitas)":
            query_caixa += " AND f.Tipo = 'E'"
        elif tipo_filtro == "Saídas (Despesas)":
            query_caixa += " AND f.Tipo = 'S'"
            
        query_caixa += " ORDER BY f.IdLancamento DESC"
        
        caixa_dados = executar_query(query_caixa, params_caixa, fetch='all')
        
        if caixa_dados:
            total_e = 0.0
            total_s = 0.0
            tabela_final = []
            
            for item in caixa_dados:
                id_l, tipo_l, valor_l, desc_l, date_l, nome_c = item
                date_l = converter_para_sp(date_l)
                nome_c_final = nome_c if nome_c else "Lançamento Avulso"
                tipo_str = "🟢 Entrada" if tipo_l == 'E' else "🔴 Saída"
                
                if tipo_l == 'E':
                    total_e += float(valor_l)
                else:
                    total_s += float(valor_l)
                    
                tabela_final.append([id_l, tipo_str, valor_l, desc_l, nome_c_final, date_l.strftime('%d/%m/%Y %H:%M')])
                
            df_fin = pd.DataFrame(tabela_final, columns=["ID Lançamento", "Tipo", "Valor (R$)", "Descrição", "Cliente/Origem", "Data"])
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
            
            # Resumo financeiro do período
            st.write("---")
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.info(f"🟢 **Total de Entradas:** R$ {total_e:.2f}")
            with col_res2:
                st.warning(f"🔴 **Total de Saídas:** R$ {total_s:.2f}")
            with col_res3:
                saldo_p = total_e - total_s
                st.success(f"⚖️ **Saldo do Período:** R$ {saldo_p:.2f}")
                
            # CRUD: Editar/Excluir lançamento do caixa
            st.write("---")
            st.subheader("Editar / Excluir Lançamento Financeiro")
            
            dic_selecao_fin = {f"Lançamento Nº {c[0]} - {c[1]} - R$ {c[2]:.2f}": c for c in caixa_dados}
            lanc_selecionado_str = st.selectbox("Selecione o Lançamento para Modificar:", list(dic_selecao_fin.keys()))
            
            if lanc_selecionado_str:
                lanc_sel = dic_selecao_fin[lanc_selecionado_str]
                id_lanc_f, tipo_lanc_f, valor_lanc_f, desc_lanc_f, date_lanc_f, _ = lanc_sel
                
                with st.form(f"form_editar_fin_{id_lanc_f}"):
                    novo_tipo_f = st.selectbox("Tipo:", ["Entrada (Receita)", "Saída (Despesa)"], index=0 if tipo_lanc_f == 'E' else 1)
                    novo_valor_f = st.number_input("Valor (R$):", value=float(valor_lanc_f), min_value=0.0)
                    nova_desc_f = st.text_area("Descrição:", value=desc_lanc_f)
                    
                    if st.form_submit_button("Salvar Alterações Financeiras", type="primary"):
                        try:
                            char_tipo_f = 'E' if novo_tipo_f == "Entrada (Receita)" else 'S'
                            executar_query("""
                                UPDATE FluxoCaixa 
                                SET Tipo = %s, Valor = %s, Descricao = %s 
                                WHERE IdLancamento = %s
                            """, (char_tipo_f, novo_valor_f, nova_desc_f, id_lanc_f))
                            st.success("Transação atualizada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                
                st.write("🗑️ **Excluir Registro**")
                confirmar_excluir_fin = st.checkbox(f"Confirmo que desejo apagar permanentemente o registro financeiro Nº {id_lanc_f}.", key=f"conf_del_fin_{id_lanc_f}")
                if st.button("Excluir Lançamento Financeiro", type="primary", disabled=not confirmar_excluir_fin, key=f"btn_del_fin_{id_lanc_f}"):
                    try:
                        executar_query("DELETE FROM FluxoCaixa WHERE IdLancamento = %s", (id_lanc_f,))
                        st.success("Lançamento excluído com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao deletar: {e}")
        else:
            st.info("Nenhum lançamento financeiro registrado neste período.")

# =========================================================================
# 9. TELA: CONTAS & ACESSOS (CRUD DE USUÁRIOS - APENAS ADM)
# =========================================================================
elif opcao == "👥 Contas & Acessos":
    st.title("👥 Gerenciamento de Contas & Níveis de Acesso")
    st.markdown("Cadastre novos colaboradores e selecione suas permissões.")
    st.write("---")
    
    # Apenas admin pode ver
    if st.session_state.user_role != 'adm':
        st.error("Acesso negado.")
        st.stop()
        
    aba_lista_contas, aba_cadastrar_conta = st.tabs(["🔍 Contas Cadastradas", "➕ Cadastrar Nova Conta"])
    
    with aba_cadastrar_conta:
        st.header("Cadastrar Novo Usuário")
        with st.form("form_cadastrar_usuario", clear_on_submit=True):
            novo_usuario = st.text_input("Nome de Usuário (login):", placeholder="Ex: kaue.arruda")
            novo_nome_real = st.text_input("Nome Completo (exibido na tela):", placeholder="Ex: Kaue Arruda")
            nova_senha = st.text_input("Senha de Acesso:", type="password")
            
            # Aqui é a parte que mostra ADM e Lojista
            nivel_acesso = st.radio(
                "Nível de Acesso (Perfil):",
                ["Lojista (Acesso básico a vendas e cadastros)", "Administrador (Acesso completo a financeiro e estoque)"]
            )
            
            if st.form_submit_button("Criar Conta", type="primary", use_container_width=True):
                if novo_usuario and novo_nome_real and nova_senha:
                    # Remove espaços
                    novo_usuario_clean = novo_usuario.strip().lower()
                    role_final = "adm" if "Administrador" in nivel_acesso else "lojista"
                    
                    try:
                        executar_query("""
                            INSERT INTO Usuarios (Usuario, Senha, Nome, Role)
                            VALUES (%s, %s, %s, %s)
                        """, (novo_usuario_clean, nova_senha, novo_nome_real, role_final))
                        st.success(f"Conta '{novo_nome_real}' cadastrada com sucesso como {role_final.upper()}!")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("Erro: Este nome de usuário já está sendo utilizado.")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("Preencha todos os campos obrigatórios (Usuário, Nome Completo e Senha).")
                    
    with aba_lista_contas:
        st.header("Usuários com Acesso ao Sistema")
        try:
            usuarios_db = executar_query("""
                SELECT IdUsuario, Usuario, Nome, Role 
                FROM Usuarios 
                ORDER BY Nome ASC
            """, fetch='all')
            
            if usuarios_db:
                dados_tabela_usuarios = []
                for u in usuarios_db:
                    role_display = "👑 Administrador (adm)" if u[3] == 'adm' else "💼 Lojista"
                    dados_tabela_usuarios.append([u[0], u[1], u[2], role_display])
                    
                df_usr = pd.DataFrame(dados_tabela_usuarios, columns=["ID", "Nome de Usuário", "Nome Exibido", "Perfil de Acesso"])
                st.dataframe(df_usr, use_container_width=True, hide_index=True)
                
                # Opção para excluir usuário
                st.write("---")
                st.subheader("Excluir Conta de Usuário")
                
                lista_exclusao = {f"{u[2]} (Usuário: {u[1]})": u for u in usuarios_db}
                usuario_excluir_str = st.selectbox("Selecione a conta para remover:", list(lista_exclusao.keys()))
                
                if usuario_excluir_str:
                    usr_sel = lista_exclusao[usuario_excluir_str]
                    id_usr, user_usr, nome_usr, role_usr = usr_sel
                    
                    # Impede que o usuário logado exclua a si mesmo
                    if user_usr == st.session_state.user_name.lower() or user_usr == "kaue":
                        st.warning("Você não pode excluir a sua própria conta ativa ou a conta administradora principal.")
                    else:
                        confirmar_usr_del = st.checkbox(f"Confirmo que desejo revogar o acesso de '{nome_usr}'.")
                        if st.button("Excluir Usuário", type="primary", disabled=not confirmar_usr_del):
                            try:
                                executar_query("DELETE FROM Usuarios WHERE IdUsuario = %s", (id_usr,))
                                st.success(f"Acesso de '{nome_usr}' revogado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir usuário: {e}")
            else:
                st.warning("Nenhum usuário cadastrado.")
        except Exception as e:
            st.error(f"Erro ao buscar usuários: {e}")