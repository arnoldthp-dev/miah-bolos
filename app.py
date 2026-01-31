import streamlit as st
from supabase import create_client

# 1. Buscando as credenciais de forma segura
# O Streamlit vai procurar isso no painel "Secrets" que você configurou
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]

# 2. Inicializando o cliente
supabase = create_client(url, key)

import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import io

# --- 0. SISTEMA DE ACESSO (TRAVA DE SEGURANÇA) ---
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    # Tela de Login Centralizada
    st.markdown("<h1 style='text-align: center;'>🍦 MIAH PDV</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("Acesso Restrito")
            # Ao publicar, configure 'password_geral' nos Secrets do Streamlit Cloud.
            # Localmente, a senha padrão será 'miah2026'
            senha_geral = st.secrets.get("password_geral", "miah2026") 
            senha_digitada = st.text_input("Digite a senha da loja", type="password")
            
            if st.button("Entrar", use_container_width=True):
                if senha_digitada == senha_geral:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
    return False

# Interrompe a execução se não estiver logado
if not check_password():
    st.stop()

# --- 1. CONFIGURAÇÃO E CONEXÃO ---
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

st.set_page_config(page_title="Miah - PDV", layout="wide", page_icon="🍦")

# Carregamento de CSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# --- CSS DEFINITIVO PARA ALINHAMENTO E COMPACTAÇÃO ---
st.markdown("""
    <style>
    /* 1. Botão de Destaque (INICIAR NOVA VENDA) */
    [data-testid="stSidebar"] div.stButton > button:first-child {
        background-color: #94acc3 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        height: 3em !important;
        border: none !important;
        width: 100% !important;
        margin-bottom: 0.5px !important;
    }

    /* 2. Botões de Módulos (Sidebar) */
    [data-testid="stSidebar"] div.stButton > button:not(:first-child) {
        background-color: transparent !important;
        color: #31333F !important;
        border: none !important;
        padding: 2px 2px !important;
        width: 100% !important;
        display: flex !important;
        justify-content: flex-start !important;
    }

    [data-testid="stSidebar"] div.stButton > button:not(:first-child) p,
    [data-testid="stSidebar"] div.stButton > button:not(:first-child) span {
        text-align: left !important;
        width: 100% !important;
        justify-content: flex-start !important;
        display: flex !important;
    }
    
    [data-testid="stSidebar"] div.stButton > button:not(:first-child):hover {
        background-color: #f0f2f6 !important;
        color: #94acc3 !important;
    }

    /* 3. AJUSTE DE CENTRALIZAÇÃO DOS BOTÕES DO CARRINHO (+, -, X) */
    div[data-testid="stHorizontalBlock"] div.stButton > button {
        padding: 0px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        min-width: 38px !important;
        height: 38px !important;
        border-radius: 8px !important;
    }

    div[data-testid="stHorizontalBlock"] div.stButton > button p {
        margin: 0px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        font-weight: bold !important;
    }

    .sap-header {
        font-size: 18px;
        font-weight: bold;
        color: #888;
        margin-top: 15px;
        margin-bottom: 2px;
        text-transform: uppercase;
        padding-left: 1px;
    }
    
    /* ESTILOS PARA TABELA COMPACTA (EXCEL STYLE) */
    .compact-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        margin-bottom: 0px;
    }
    .compact-table th {
        background-color: #f0f2f6;
        padding: 8px;
        text-align: left;
        border: 1px solid #ddd;
        font-weight: bold;
    }
    .compact-cell {
        padding: 4px 8px;
        border-bottom: 1px solid #eee;
        height: 40px;
        display: flex;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# Inicialização de estados
if 'venda_id' not in st.session_state: st.session_state.venda_id = None
if 'show_modal' not in st.session_state: st.session_state.show_modal = False
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = "PDV"

# --- 2. COMPONENTES DE INTERFACE ---

@st.dialog("FECHAMENTO DE COMANDA")
def fechar_venda_modal():
    if st.session_state.venda_id is None:
        st.warning("Nenhuma venda selecionada para fechamento.")
        if st.button("FECHAR"):
            st.session_state.show_modal = False
            st.rerun()
        return

    itens_res = supabase.table("venda_itens").select("*").eq("venda_id", st.session_state.venda_id).execute()
    sub = sum(i['subtotal'] for i in itens_res.data)
    
    st.markdown("### RESUMO DO PEDIDO")
    
    html_table = """
    <table class='miah-table'>
        <thead><tr><th style='text-align:left'>ITEM</th><th>QTD</th><th>UNIT.</th><th>TOTAL</th></tr></thead>
        <tbody>
    """
    for i in itens_res.data:
        pu = f"R$ {i['preco_unitario']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        pt = f"R$ {i['subtotal']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        html_table += f"<tr><td style='text-align:left'>{i['descricao'].upper()}</td><td>{int(i['quantidade'])}</td><td>{pu}</td><td>{pt}</td></tr>"
    
    html_table += "</tbody></table>"
    st.markdown(html_table, unsafe_allow_html=True)
    
    desconto = st.number_input("DESCONTO (R$)", min_value=0.0, max_value=float(sub), format="%.2f", step=0.01)
    tot_pagar = sub - desconto
    
    st.markdown(f"<div class='total-destaque'>TOTAL A PAGAR: R$ {tot_pagar:,.2f}</div>".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
    
    st.markdown("**FORMA DE PAGAMENTO**")
    forma = st.radio("SELECIONE UMA OPÇÃO", ["DINHEIRO", "PIX", "CRÉDITO", "DÉBITO"], horizontal=True, label_visibility="collapsed")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("PAGAMENTO FINALIZADO", type="primary", use_container_width=True):
            supabase.rpc("finalizar_comanda", {"p_venda_id": int(st.session_state.venda_id), "p_forma_pagamento": forma, "p_desconto": desconto}).execute()
            st.session_state.venda_id = None; st.session_state.show_modal = False; st.rerun()
    with c2:
        if st.button("IMPRIMIR COMANDA", use_container_width=True):
            st.info("IMPRIMINDO...")
            
    if st.button("VOLTAR", use_container_width=True):
        st.session_state.show_modal = False; st.rerun()

# --- 3. SIDEBAR DE NAVEGAÇÃO ---

with st.sidebar:
    st.markdown("<h2 style='font-size: 20px; padding-left: 5px;'>MIAH Bolos e Salgados</h2>", unsafe_allow_html=True)
    
    if st.button("🛒 INICIAR NOVA VENDA", use_container_width=True):
        st.session_state.pagina_atual = "PDV"
        st.session_state.venda_id = None
        st.rerun()
    
    st.markdown('<div class="sap-header">📊 Vendas</div>', unsafe_allow_html=True)
    if st.button("Comandas em aberto", use_container_width=True): st.session_state.pagina_atual = "Comandas em aberto"; st.rerun()
    if st.button("Analítico de vendas", use_container_width=True): st.session_state.pagina_atual = "Analítico de vendas"; st.rerun()
    if st.button("Dashboard", use_container_width=True): st.session_state.pagina_atual = "Dashboard"; st.rerun()

    st.markdown('<div class="sap-header">📦 Estoque</div>', unsafe_allow_html=True)
    if st.button("Contagem de itens", use_container_width=True): st.session_state.pagina_atual = "Contagem de itens"; st.rerun()
    if st.button("Lançar baixas/perdas", use_container_width=True): st.session_state.pagina_atual = "Lançar baixas/perdas"; st.rerun()
    if st.button("Relatório de estoque", use_container_width=True): st.session_state.pagina_atual = "Relatório de estoque"; st.rerun()

    st.markdown('<div class="sap-header">💰 Financeiro</div>', unsafe_allow_html=True)
    if st.button("Lançar despesas", use_container_width=True): st.session_state.pagina_atual = "Lançar despesas"; st.rerun()
    if st.button("Relatório de contas a pagar", use_container_width=True): st.session_state.pagina_atual = "Relatório de contas a pagar"; st.rerun()

    st.markdown('<div class="sap-header">⚙️ Master Data</div>', unsafe_allow_html=True)
    if st.button("Cadastro de clientes", use_container_width=True): st.session_state.pagina_atual = "Cadastro de clientes"; st.rerun()
    if st.button("Cadastro de itens", use_container_width=True): st.session_state.pagina_atual = "Cadastro de itens"; st.rerun()

    st.divider()
    if st.button("🔓 Sair / Logout", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# --- 4. LÓGICA DAS TELAS ---

if st.session_state.pagina_atual == "PDV":
    st.title("MIAH BOLOS E SALGADOS")

    if st.session_state.venda_id is None:
        st.subheader("IDENTIFICAÇÃO DO ATENDIMENTO")
        # FILTRO ATIVO: eq("ativo", True)
        clis_db = supabase.table("clientes").select("codigo, nome, telefone").eq("ativo", True).execute()
        dict_clis = {f"{c['codigo']} - {c['nome']}": c for c in clis_db.data}
        sel_cli = st.selectbox("BUSCAR CLIENTE", options=[""] + list(dict_clis.keys()))
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            n_cli = c1.text_input("CLIENTE", value=dict_clis[sel_cli]['nome'] if sel_cli else "")
            t_cli = c2.text_input("TELEFONE", value=dict_clis[sel_cli]['telefone'] if sel_cli else "")
            cmd_cli = c3.text_input("COMANDA", placeholder="EX: 17")
            if st.button("ABRIR COMANDA", type="primary", use_container_width=True, key="btn_abrir"):
                if n_cli and t_cli:
                    res = supabase.rpc("abrir_comanda", {"p_cliente_nome": n_cli, "p_telefone": t_cli, "p_comanda": cmd_cli}).execute()
                    st.session_state.venda_id = res.data; st.rerun()
    else:
        v_info = supabase.table("vendas").select("numero_pedido").eq("id", st.session_state.venda_id).single().execute()
        st.info(f"📄 PEDIDO: **{v_info.data['numero_pedido']}**")
        col_v, col_c = st.columns([1.8, 1.4])

        with col_v:
            st.subheader("VITRINE")
            
            # 1. Barra de Pesquisa adicionada aqui
            busca_item = st.text_input("🔍 PESQUISAR PRODUTO", placeholder="Digite o nome do salgado ou bolo...").upper()

            res_prod = supabase.table("produtos").select("id, codigo, nome, preco").eq("tipo", "VENDA").eq("ativo", True).execute()
            res_est = supabase.table("estoque").select("codigo_produto, quantidade").execute()

            if res_prod.data and res_est.data:
                df_p = pd.DataFrame(res_prod.data)
                df_e = pd.DataFrame(res_est.data)
                df_vitrine = pd.merge(df_p, df_e, left_on='codigo', right_on='codigo_produto', how='left')
                df_vitrine['quantidade'] = df_vitrine['quantidade'].fillna(0)
                
                # 2. Lógica de Filtro: Filtra o DataFrame com base no texto digitado
                if busca_item:
                    df_vitrine = df_vitrine[df_vitrine['nome'].str.contains(busca_item, na=False)]

                # 3. Renderização dos Cards (apenas os filtrados)
                if not df_vitrine.empty:
                    cols_v = st.columns(3)
                    for idx, row in df_vitrine.reset_index().iterrows():
                        with cols_v[idx % 3]:
                            with st.container(border=True):
                                st.markdown(f"**{row['nome']}**")
                                st.write(f"R$ {row['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                st.caption(f"ESTOQUE: {int(row['quantidade'])}")
                                
                                qtd_venda = st.number_input("QTD", min_value=1, value=1, key=f"q_{row['id']}", label_visibility="collapsed")
                                
                                if st.button("ADICIONAR", key=f"add_{row['id']}", use_container_width=True):
                                    supabase.rpc("adicionar_item_comanda", {
                                        "p_venda_id": int(st.session_state.venda_id), 
                                        "p_item_id": int(row['id']), 
                                        "p_quantidade": float(qtd_venda)
                                    }).execute()
                                    st.rerun()
                else:
                    st.warning("Nenhum item encontrado com esse nome.")

        with col_c:
            st.subheader("🛒 CARRINHO")
            itens = supabase.table("venda_itens").select("*").eq("venda_id", st.session_state.venda_id).order("id").execute()
            total_acum = sum(i['subtotal'] for i in itens.data)
            
            if itens.data:
                h = st.columns([3, 0.8, 1.2, 1.2, 1.2]); h[0].markdown("**ITEM**"); h[1].markdown("**QTD**"); h[2].markdown("**UNIT.**"); h[3].markdown("**TOTAL**"); h[4].write("") 
                st.markdown("<hr style='margin: 0px 0px 10px 0px; border-top: 1px solid #bbb;'>", unsafe_allow_html=True)

            for i in itens.data:
                with st.container(border=True):
                    r = st.columns([3, 0.8, 1.2, 1.2, 1.2]); r[0].write(f"**{i['descricao']}**"); r[1].write(f"{int(i['quantidade'])}"); r[2].write(f"{i['preco_unitario']:,.2f}"); r[3].write(f"**{i['subtotal']:,.2f}**")
                    b_sub = r[4].columns(3) 
                    if b_sub[0].button("➕", key=f"p_{i['id']}"): supabase.rpc("adicionar_item_comanda", {"p_venda_id": int(st.session_state.venda_id), "p_item_id": int(i['item_id']), "p_quantidade": 1.0}).execute(); st.rerun()
                    if b_sub[1].button("➖", key=f"m_{i['id']}"): supabase.rpc("diminuir_item_venda_id", {"p_item_venda_id": i['id']}).execute(); st.rerun()
                    if b_sub[2].button("X", key=f"d_{i['id']}"): supabase.rpc("remover_item_comanda", {"p_item_venda_id": i['id']}).execute(); st.rerun()
            
            st.divider()
            st.markdown(f"### TOTAL GERAL: R$ {total_acum:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            if st.button("FECHAR COMANDA", type="primary", use_container_width=True, key="btn_fechar_checkout"):
                st.session_state.show_modal = True; st.rerun()
            c_rod = st.columns(2)
            if c_rod[0].button("SALVAR", key="btn_salvar", use_container_width=True): 
                st.session_state.venda_id = None; st.session_state.show_modal = False; st.rerun()
            if c_rod[1].button("CANCELAR", key="btn_cancelar", use_container_width=True):
                if st.session_state.venda_id: supabase.rpc("cancelar_comanda", {"p_venda_id": int(st.session_state.venda_id)}).execute()
                st.session_state.venda_id = None; st.session_state.show_modal = False; st.rerun()

    if st.session_state.show_modal:
        fechar_venda_modal()

elif st.session_state.pagina_atual == "Comandas em aberto":
    st.title("📋 COMANDAS EM ABERTO")
    res_vendas = supabase.table("vendas").select("*").eq("status", "aberta").order("created_at").execute()
    if res_vendas.data:
        ids_abertos = [v['id'] for v in res_vendas.data]
        res_itens = supabase.table("venda_itens").select("venda_id, subtotal").in_("venda_id", ids_abertos).execute()
        df_itens = pd.DataFrame(res_itens.data)
        totais_por_venda = df_itens.groupby('venda_id')['subtotal'].sum() if not df_itens.empty else pd.Series()
        total_geral_aberto = df_itens['subtotal'].sum() if not df_itens.empty else 0.0

        st.markdown(f"""<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #94acc3; margin-bottom: 25px;">
                        <span style="color: #555; font-size: 14px; text-transform: uppercase; font-weight: bold;">Valor Total em Aberto</span>
                        <h2 style="color: #31333F; margin: 0;">R$ {total_geral_aberto:,.2f}</h2>
                        <span style="color: #888; font-size: 13px;">{len(res_vendas.data)} comandas</span></div>""".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, v in enumerate(res_vendas.data):
            total_card = totais_por_venda.get(v['id'], 0.0)
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"### 🎫 Comanda: {v['comanda'] if v['comanda'] else 'S/N'}")
                    st.markdown(f"**Cliente:** {v['cliente_nome'].upper()}")
                    st.markdown(f"#### R$ {total_card:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    if st.button("RETOMAR ATENDIMENTO", key=f"open_{v['id']}", use_container_width=True):
                        st.session_state.venda_id = v['id']; st.session_state.pagina_atual = "PDV"; st.rerun()
    else: st.info("Não há comandas abertas.")

elif st.session_state.pagina_atual == "Analítico de vendas":
    st.title("📊 ANALÍTICO DE VENDAS")

    # 1. Filtros de Data
    c1, c2, _ = st.columns([1, 1, 2])
    data_inicio = c1.date_input("DE", value=datetime.now())
    data_fim = c2.date_input("ATÉ", value=datetime.now())

    # 2. Query ao Banco
    query = supabase.table("venda_itens").select("""
        created_at, 
        numero_pedido, 
        codigo_item, 
        descricao, 
        quantidade, 
        preco_unitario, 
        subtotal, 
        desconto_item, 
        meio_pagamento,
        vendas!inner(status, cliente_nome)
    """).gte("created_at", data_inicio.strftime('%Y-%m-%d 00:00:00')) \
       .lte("created_at", data_fim.strftime('%Y-%m-%d 23:59:59')) \
       .order("created_at", desc=True)
    
    res = query.execute()

    if res.data:
        df = pd.DataFrame(res.data)
        
        # 3. TRATAMENTO DOS DADOS
        df['Status venda'] = df['vendas'].apply(lambda x: x['status'].upper())
        df['Nome cliente'] = df['vendas'].apply(lambda x: x['cliente_nome'].upper())
        
        # Formata a Data
        df['Data'] = pd.to_datetime(df['created_at']).dt.tz_convert('America/Sao_Paulo').dt.strftime('%d/%m/%Y %H:%M')
        
        # Calcula o Total Final
        df['Total final'] = df['subtotal'] - df['desconto_item'].fillna(0)

        # 4. REORGANIZAÇÃO NA SEQUÊNCIA SOLICITADA
        df_final = df[[
            'Data', 'numero_pedido', 'Status venda', 'Nome cliente', 
            'codigo_item', 'descricao', 'quantidade', 'preco_unitario', 
            'subtotal', 'desconto_item', 'Total final', 'meio_pagamento'
        ]].copy()

        # Renomeação de colunas
        df_final.columns = [
            'Data', 'Número Pedido', 'Status', 'Cliente', 
            'Cód. Item', 'Item', 'Qtd', 'Preço Unit.', 
            'Subtotal', 'Desconto', 'Total Final', 'Meio Pagamento'
        ]

        # 5. FUNÇÃO DE FORMATAÇÃO DE MOEDA (Brasil)
        def formatar_moeda(valor):
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # Aplicando a formatação visual
        df_visual = df_final.copy()
        colunas_moeda = ['Preço Unit.', 'Subtotal', 'Desconto', 'Total Final']
        for col in colunas_moeda:
            df_visual[col] = df_visual[col].apply(formatar_moeda)

        # 6. EXIBIÇÃO
        total_periodo = df_final['Total Final'].sum()
        st.markdown(f"### 💰 RECEITA TOTAL NO PERÍODO: {formatar_moeda(total_periodo)}")
        
        # Exibe o dataframe formatado
        st.dataframe(df_visual, use_container_width=True, hide_index=True)

        # 7. EXPORTAÇÃO (Dados brutos para o Excel permitir cálculos)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name='RelatorioVendas')
            # Ajuste opcional: Formatar colunas no Excel como Moeda
            workbook  = writer.book
            worksheet = writer.sheets['RelatorioVendas']
            format_moeda = workbook.add_format({'num_format': 'R$ #,##0.00'})
            # Colunas H, I, J, K no Excel (Preço Unit até Total Final)
            worksheet.set_column('H:K', 15, format_moeda)
        
        st.download_button(
            label="📥 EXPORTAR PARA EXCEL",
            data=buffer.getvalue(),
            file_name=f"analitico_miah_{data_inicio.strftime('%d%m%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Nenhuma venda encontrada para o período selecionado.")

elif st.session_state.pagina_atual == "Dashboard":
    st.title("📊 DASHBOARD DE VENDAS")

    # 1. Filtros de Data (Mesma lógica do Analítico)
    c1, c2, _ = st.columns([1, 1, 2])
    data_inicio = c1.date_input("DE", value=datetime.now(), key="dash_inicio")
    data_fim = c2.date_input("ATÉ", value=datetime.now(), key="dash_fim")

    # 2. Query ao Banco (Apenas vendas PAGAS)
    query = supabase.table("venda_itens").select("""
        subtotal, 
        desconto_item, 
        meio_pagamento,
        numero_pedido,
        vendas!inner(status)
    """).eq("vendas.status", "paga") \
       .gte("created_at", data_inicio.strftime('%Y-%m-%d 00:00:00')) \
       .lte("created_at", data_fim.strftime('%Y-%m-%d 23:59:59'))
    
    res = query.execute()

    if res.data:
        df = pd.DataFrame(res.data)
        
        # Cálculos de Indicadores
        df['total_liquido'] = df['subtotal'] - df['desconto_item'].fillna(0)
        total_vendas_valor = df['total_liquido'].sum()
        total_descontos = df['desconto_item'].sum()
        qtd_pedidos_distintos = df['numero_pedido'].nunique()
        ticket_medio = total_vendas_valor / qtd_pedidos_distintos if qtd_pedidos_distintos > 0 else 0

        # Formatação de Moeda
        def fmt_moeda(v):
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # 3. EXIBIÇÃO DOS CARDS DE MÉTRICAS
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Vendas (Líquido)", fmt_moeda(total_vendas_valor))
        m2.metric("Descontos", fmt_moeda(total_descontos))
        m3.metric("Ticket Médio", fmt_moeda(ticket_medio))
        m4.metric("Qtd Pedidos", f"{qtd_pedidos_distintos} un")

        st.divider()

        # 4. TOTAL POR MEIO DE PAGAMENTO
        st.subheader("💳 Faturamento por Meio de Pagamento")
        df_pag = df.groupby('meio_pagamento')['total_liquido'].sum().reset_index()
        df_pag = df_pag.sort_values(by='total_liquido', ascending=False)

        cols_pag = st.columns(len(df_pag) if not df_pag.empty else 1)
        for idx, row in df_pag.iterrows():
            with cols_pag[idx]:
                st.markdown(f"""
                    <div style="background-color: #f8f9fb; padding: 15px; border-radius: 10px; border: 1px solid #eee; text-align: center;">
                        <span style="color: #666; font-size: 14px; text-transform: uppercase;">{row['meio_pagamento']}</span>
                        <h3 style="margin: 5px 0; color: #31333F;">{fmt_moeda(row['total_liquido'])}</h3>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Sem dados para o período selecionado.")
    
    if st.button("Voltar ao PDV"):
        st.session_state.pagina_atual = "PDV"; st.rerun()

elif st.session_state.pagina_atual == "Contagem de itens":
    st.title("Lançamento de estoque")
    prods_db = supabase.table("produtos").select("codigo, nome").eq("ativo", True).eq("tipo", "VENDA").execute()
    if prods_db.data:
        opcoes = {f"{p['codigo']} - {p['nome'].upper()}": p['codigo'] for p in prods_db.data}
        selecionado = st.selectbox("BUSCAR PRODUTO", options=[""] + list(opcoes.keys()))
        if selecionado:
            cod = opcoes[selecionado]; est_res = supabase.table("estoque").select("quantidade").eq("codigo_produto", cod).single().execute()
            st.info(f"Saldo atual: **{est_res.data['quantidade'] if est_res.data else 0}**")
            nova_qtd = st.number_input("NOVA QUANTIDADE", min_value=0.0, step=1.0)
            if st.button("✅ ATUALIZAR", type="primary", use_container_width=True):
                supabase.rpc("atualizar_estoque_manual", {"p_codigo_produto": cod, "p_nova_quantidade": nova_qtd}).execute()
                st.success("Atualizado!"); st.rerun()
    if st.button("Voltar"): st.session_state.pagina_atual = "PDV"; st.rerun()

elif st.session_state.pagina_atual == "Relatório de estoque":
    st.title("📋 RELATÓRIO GERAL DE ESTOQUE")
    res_prod = supabase.table("produtos").select("codigo, nome, preco, custo, ativo").eq("tipo", "VENDA").execute()
    res_est = supabase.table("estoque").select("codigo_produto, quantidade").execute()
    if res_prod.data:
        df = pd.merge(pd.DataFrame(res_prod.data), pd.DataFrame(res_est.data), left_on='codigo', right_on='codigo_produto', how='left')
        st.dataframe(df, use_container_width=True, hide_index=True)
    if st.button("Voltar"): st.session_state.pagina_atual = "PDV"; st.rerun()

elif st.session_state.pagina_atual == "Cadastro de clientes":
    st.title("👥 GESTÃO DE CLIENTES")
    def carregar_clientes():
        res = supabase.table("clientes").select("*").eq("ativo", True).order("id", desc=True).execute()
        return pd.DataFrame(res.data)

    @st.dialog("CADASTRO / EDIÇÃO DE CLIENTE")
    def modal_cliente(cliente_data=None):
        is_edit = cliente_data is not None
        if is_edit: st.info(f"Editando: **{cliente_data['codigo']}**")
        nome = st.text_input("NOME COMPLETO", value=cliente_data['nome'] if is_edit else "").upper()
        tel = st.text_input("TELEFONE", value=cliente_data['telefone'] if is_edit else "")
        st.divider()
        if st.button("SALVAR", type="primary", use_container_width=True):
            if nome and tel:
                if is_edit: supabase.table("clientes").update({"nome": nome, "telefone": tel}).eq("id", cliente_data['id']).execute()
                else: supabase.rpc("get_or_create_cliente", {"p_nome": nome, "p_telefone": tel}).execute()
                st.rerun()
            else: st.error("Preencha os campos.")

    col_busca, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("➕ NOVO CLIENTE", use_container_width=True, type="primary"): modal_cliente()
    with col_busca: busca = st.text_input("🔍 BUSCAR", placeholder="Nome, código ou telefone...", label_visibility="collapsed")
    df_clis = carregar_clientes()
    if not df_clis.empty:
        if busca:
            mask = df_clis.apply(lambda row: busca.lower() in str(row.values).lower(), axis=1)
            df_clis = df_clis[mask]
        st.markdown("""<table class='compact-table'><thead><tr><th style='width: 15%'>CÓDIGO</th><th style='width: 45%'>NOME</th>
                       <th style='width: 25%'>TELEFONE</th><th style='width: 15%; text-align: center;'>AÇÕES</th></tr></thead></table>""", unsafe_allow_html=True)
        for _, row in df_clis.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1.5, 4.5, 2.5, 0.75, 0.75])
                c1.markdown(f"<div class='compact-cell'>{row['codigo']}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='compact-cell'>{row['nome']}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='compact-cell'>{row['telefone']}</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                    if st.button("📝", key=f"edit_{row['id']}", use_container_width=True): modal_cliente(row)
                with c5:
                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                    if st.button("🚫", key=f"ina_{row['id']}", use_container_width=True):
                        supabase.table("clientes").update({"ativo": False}).eq("id", row['id']).execute(); st.rerun()
    if st.button("Voltar"): st.session_state.pagina_atual = "PDV"; st.rerun()

else:
    st.title(f"📂 {st.session_state.pagina_atual}")
    st.info("Módulo em desenvolvimento.")
    if st.button("Voltar"): st.session_state.pagina_atual = "PDV"; st.rerun()