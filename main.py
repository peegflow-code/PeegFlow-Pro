import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db, engine, Base
import services as api
from models import User, Company, Product, Sale, Expense
from datetime import datetime, timedelta
import base64

# Configurações iniciais da página
st.set_page_config(page_title='PeegFlow Pro', page_icon='⚡', layout='wide')
Base.metadata.create_all(bind=engine)
db = next(get_db())

# --- ESTILOS CSS (Login, PDV e Financeiro) ---
st.markdown("""<style>
    /* Estilo Geral */
    .stApp { background-color: #F4F7FE; color: #1B2559; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1F2937; }

    /* TELA DE LOGIN (Referência image_ea97e5) */
    .login-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 50px; }
    .login-box { background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 450px; text-align: center; }
    .login-logo-top { margin-bottom: 20px; }

    /* CUPOM FISCAL PDV (Referência image_e9b6e2) */
    .receipt-panel {
        background-color: #111827 !important; 
        border-radius: 20px; 
        padding: 25px; 
        color: white !important; 
        min-height: 550px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .receipt-title { color: #A3AED0 !important; font-size: 0.8rem; font-weight: 700; letter-spacing: 1px; border-bottom: 1px solid #2B3674; padding-bottom: 10px; margin-bottom: 20px; }
    .receipt-item { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 0.95rem; color: white !important; }
    .receipt-total-section { margin-top: 30px; border-top: 1px dashed #2B3674; padding-top: 20px; }
    .total-value { font-size: 2.8rem; font-weight: 800; color: #10B981 !important; line-height: 1; }

    /* MÓDULO FINANCEIRO (Referência image_ea9519) */
    .fin-card-white { background: white; padding: 35px; border-radius: 24px; border: 1px solid #E0E5F2; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .fin-card-purple { background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%); padding: 35px; border-radius: 24px; color: white; box-shadow: 0 10px 20px rgba(99, 102, 241, 0.2); }
    .fin-title { color: #A3AED0; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 10px; }
    .fin-value-main { color: #10B981; font-size: 2.5rem; font-weight: 800; margin-bottom: 20px; }
    
    /* Botões */
    div.stButton > button { border-radius: 12px; font-weight: 600; transition: all 0.3s; }
</style>""", unsafe_allow_html=True)

# Inicialização do estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_id': None, 'company_id': None, 'username': None, 'cart': []})

# --- FUNÇÃO AUXILIAR PARA IMAGEM (Pode ficar logo antes do if de login) ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

# --- LÓGICA DE LOGIN ---
if not st.session_state['logged_in']:
    # Layout de colunas apenas para limitar a largura no Desktop
    # No mobile, o Streamlit empilha, mas o HTML interno manterá o centro
    _, col_central, _ = st.columns([1, 1.2, 1])
    
    with col_central:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # 1. Carregar e converter a imagem
        img_b64 = get_img_as_base64("logo_peegflow.jpg")
        
        # 2. Renderizar Cabeçalho (Logo + Títulos) em HTML Puro
        # Isso garante que o alinhamento central funcione em qualquer dispositivo
        html_header = f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 80px; margin-bottom: 10px; border-radius: 50%;">
            <h2 style="text-align: center; color: #1B2559; margin: 0; font-size: 2rem;">Bem-vindo ao PeegFlow</h2>
            <p style="text-align: center; color: #A3AED0; margin-top: 10px; font-size: 1rem;">Insira os seus dados para aceder ao painel.</p>
        </div>
        """
        st.markdown(html_header, unsafe_allow_html=True)

        # 3. Formulário de Login
        with st.form("login_form"):
            u = st.text_input("USUÁRIO", placeholder="Ex: admin")
            p = st.text_input("SENHA", type="password", placeholder="••••••••")
            
            st.write("") # Espaçamento
            
            # Botão de Login
            if st.form_submit_button("Entrar no Sistema ⚡", use_container_width=True):
                user = api.authenticate(db, u, p)
                if user:
                    st.session_state.update({
                        'logged_in': True, 
                        'user_id': user.id, 
                        'company_id': user.company_id, 
                        'username': user.username
                    })
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")

            # Botão Demo
            if st.form_submit_button("🧪 Ativar Modo Demo (30 dias)", use_container_width=True):
                api.setup_demo_data(db)
                st.session_state.update({
                    'logged_in': True, 
                    'user_id': 99, 
                    'company_id': 99, 
                    'username': 'Admin Demo'
                })
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
# --- ESTRUTURA PRINCIPAL (SIDEBAR) ---
cid = st.session_state['company_id']
with st.sidebar:
    st.image("logo_peegflow.jpg", width=140)
    st.write(f"👤 **{st.session_state['username']}**")
    st.divider()
    choice = st.radio("Navegação", ["📊 Dashboard", "🛒 Checkout (PDV)", "💰 Fluxo Financeiro", "📦 Estoque"])
    if st.button("Sair"): st.session_state.clear(); st.rerun()

# --- DASHBOARD ---
if choice == "📊 Dashboard":
    st.title("Dashboard Executivo")
    df_daily = api.get_daily_sales_data(db, cid)
    
    col1, col2, col3 = st.columns(3)
    df_v, df_e = api.get_financial_data(db, cid)
    col1.metric("Vendas (30d)", f"€ {df_v['price'].sum():,.2f}")
    col2.metric("Ticket Médio", f"€ {df_v['price'].mean() if not df_v.empty else 0:,.2f}")
    col3.metric("Despesas", f"€ {df_e['amount'].sum():,.2f}")

    fig = px.area(df_daily, x='date', y='total', title="Evolução de Faturamento")
    fig.update_traces(line_color='#6366F1', fillcolor='rgba(99, 102, 241, 0.1)')
    st.plotly_chart(fig, use_container_width=True)

# --- PDV (Checkout) ---
elif choice == "🛒 Checkout (PDV)":
    st.title("Ponto de Venda")
    col_prod, col_receipt = st.columns([0.6, 0.4], gap="large")

    # --- COLUNA DA ESQUERDA (PRODUTOS) ---
    with col_prod:
        search = st.text_input("🔍 Pesquisar produto ou código de barras...", placeholder="Ex: iPhone...")
        prods = api.get_products(db, cid)

        # Grid de produtos
        p_cols = st.columns(3)
        # Filtro simples
        filtered_prods = [pr for pr in prods if search.lower() in pr.name.lower()]
        
        for i, p in enumerate(filtered_prods):
            with p_cols[i % 3]:
                st.markdown(f"""
                <div style="background: white; padding: 20px; border-radius: 15px; border: 1px solid #E0E5F2; text-align: center; margin-bottom: 10px;">
                    <div style="font-size: 2rem;">📱</div>
                    <div style="font-weight: 700; color: #1B2559; margin: 10px 0;">{p.name}</div>
                    <div style="color: #6366F1; font-weight: 800;">€ {p.price_retail:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Adicionar", key=f"add_{p.id}", use_container_width=True):
                    st.session_state['cart'].append({"id": p.id, "name": p.name, "price": p.price_retail})
                    st.rerun()

    # --- COLUNA DA DIREITA (CUPOM) ---
    with col_receipt:
        # 1. Construção do HTML do Cupom (Visual Preto)
        receipt_html = '<div class="receipt-panel">'
        
        # Cabeçalho
        receipt_html += f'<div class="receipt-title">CUPÃO FISCAL #{datetime.now().strftime("%H%M")}</div>'

        # Itens
        total = 0.0
        if not st.session_state['cart']:
            receipt_html += '<div style="color: #4B5563; text-align: center; margin-top: 60px;">Aguardando produtos...</div>'
        else:
            for item in st.session_state['cart']:
                total += item['price']
                receipt_html += f'<div class="receipt-item"><span>{item["name"]}</span><span style="font-weight: 700;">€ {item["price"]:,.2f}</span></div>'

        # Totalização
        receipt_html += '<div class="receipt-total-section">'
        receipt_html += f'<div class="receipt-item"><span style="color: #A3AED0;">Subtotal</span><span>€ {total:,.2f}</span></div>'
        receipt_html += f"""
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 10px;">
                <span style="color: #A3AED0; font-weight: 700; font-size: 0.9rem;">TOTAL</span>
                <span class="total-value">€ {total:,.2f}</span>
            </div>
        """
        receipt_html += '</div>' # Fecha seção total
        receipt_html += '</div>' # Fecha o painel preto AQUI.
        
        # 2. Renderiza o visual
        st.markdown(receipt_html, unsafe_allow_html=True)

        # 3. Botões (Ficam FORA do HTML, logo abaixo)
        st.write("") # Espaçamento
        
        if st.button("FINALIZAR VENDA (F10)", type="primary", use_container_width=True):
            if st.session_state['cart']:
                for item in st.session_state['cart']:
                    # Certifique-se que api.process_sale existe e aceita esses argumentos
                    api.process_sale(db, item['id'], 1, "varejo", st.session_state['user_id'], cid)
                st.session_state['cart'] = []
                st.success("Venda processada!")
                st.rerun()
            else:
                st.warning("Carrinho vazio!")

        if st.button("🗑️ Limpar Tudo", use_container_width=True):
            st.session_state['cart'] = []
            st.rerun()


# --- FINANCEIRO ATUALIZADO ---
elif choice == "💰 Fluxo Financeiro":
    st.title("Gestão Financeira Integrada")
    
    # Criação de abas para separar Relatórios de Cadastros
    tab_fechamento, tab_calendario = st.tabs(["📊 Fechamento de Caixa", "🗓️ Calendário Fiscal & Despesas"])

    # --- ABA 1: FECHAMENTO DE CAIXA ---
    with tab_fechamento:
        st.markdown("### Selecione o Período")
        
        # Filtros de Data
        c_date1, c_date2 = st.columns(2)
        with c_date1:
            dt_inicio = st.date_input("Data Início", datetime.now().replace(day=1))
        with c_date2:
            dt_fim = st.date_input("Data Fim", datetime.now())

        # Converter para datetime para passar para o serviço
        dt_start_full = datetime.combine(dt_inicio, datetime.min.time())
        dt_end_full = datetime.combine(dt_fim, datetime.max.time())

        if st.button("🔍 Gerar Fechamento"):
            # Busca dados filtrados
            df_vendas, df_despesas = api.get_financial_by_range(db, cid, dt_start_full, dt_end_full)
            
            # Cálculos
            total_entradas = df_vendas['price'].sum() if not df_vendas.empty else 0.0
            total_saidas = df_despesas['amount'].sum() if not df_despesas.empty else 0.0
            saldo = total_entradas - total_saidas

            # Cards de Resumo (Estilo CSS do usuário)
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            col_kpi1.markdown(f"""
                <div class="fin-card-white" style="padding: 20px;">
                    <div class="fin-title">Total Entradas</div>
                    <div style="color: #10B981; font-size: 1.8rem; font-weight: 800;">€ {total_entradas:,.2f}</div>
                </div>""", unsafe_allow_html=True)
            
            col_kpi2.markdown(f"""
                <div class="fin-card-white" style="padding: 20px;">
                    <div class="fin-title">Total Saídas</div>
                    <div style="color: #FF4B4B; font-size: 1.8rem; font-weight: 800;">€ {total_saidas:,.2f}</div>
                </div>""", unsafe_allow_html=True)

            cor_saldo = "#10B981" if saldo >= 0 else "#FF4B4B"
            col_kpi3.markdown(f"""
                <div class="fin-card-white" style="padding: 20px; border: 2px solid {cor_saldo};">
                    <div class="fin-title">Saldo Líquido</div>
                    <div style="color: {cor_saldo}; font-size: 1.8rem; font-weight: 800;">€ {saldo:,.2f}</div>
                </div>""", unsafe_allow_html=True)

            st.divider()

            # Detalhamento
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.subheader("📥 Detalhe de Entradas (Vendas)")
                if not df_vendas.empty:
                    # Tratamento visual da tabela
                    st.dataframe(
                        df_vendas[['date', 'product_name', 'quantity', 'price']].rename(columns={'date': 'Data', 'product_name': 'Produto', 'quantity': 'Qtd', 'price': 'Valor'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma venda neste período.")

            with col_det2:
                st.subheader("📤 Detalhe de Saídas (Despesas)")
                if not df_despesas.empty:
                    st.dataframe(
                        df_despesas[['date', 'category', 'description', 'amount']].rename(columns={'date': 'Data', 'category': 'Categoria', 'description': 'Descrição', 'amount': 'Valor'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma despesa neste período.")

    # --- ABA 2: CALENDÁRIO FISCAL (CADASTROS) ---
    with tab_calendario:
        c_form, c_list = st.columns([0.4, 0.6], gap="large")

        # Formulário de Cadastro
        with c_form:
            st.markdown('<div class="fin-card-purple">', unsafe_allow_html=True)
            st.markdown("### 📝 Nova Despesa")
            with st.form("form_despesa"):
                d_desc = st.text_input("Descrição", placeholder="Ex: Aluguel, Luz, Fornecedor X")
                d_valor = st.number_input("Valor (€)", min_value=0.0, format="%.2f")
                d_tipo = st.selectbox("Tipo de Despesa", ["Fixa (Recorrente)", "Variável (Extra)", "Impostos", "Pessoal"])
                d_data = st.date_input("Data de Vencimento/Pagamento", datetime.now())
                
                submitted = st.form_submit_button("💾 Salvar Despesa", use_container_width=True)
                if submitted:
                    if d_desc and d_valor > 0:
                        # Converte data para datetime completo
                        d_data_full = datetime.combine(d_data, datetime.now().time())
                        api.add_expense(db, cid, d_desc, d_valor, d_tipo, d_data_full)
                        st.success("Despesa lançada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha descrição e valor.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Listagem Geral de Despesas (Futuras e Passadas)
        with c_list:
            st.subheader("📅 Histórico e Previsão de Contas")
            
            # Pega todas as despesas dos últimos 60 dias e próximos 30 dias
            d_start = datetime.now() - timedelta(days=60)
            d_end = datetime.now() + timedelta(days=30)
            _, df_all_expenses = api.get_financial_by_range(db, cid, d_start, d_end)
            
            if not df_all_expenses.empty:
                # Ordenar por data
                df_all_expenses['date'] = pd.to_datetime(df_all_expenses['date'])
                df_all_expenses = df_all_expenses.sort_values(by='date', ascending=False)
                
                # Exibir tabela interativa
                st.dataframe(
                    df_all_expenses[['date', 'category', 'description', 'amount']],
                    column_config={
                        "date": st.column_config.DateColumn("Data"),
                        "amount": st.column_config.NumberColumn("Valor (€)", format="€ %.2f"),
                        "category": "Tipo",
                        "description": "Descrição"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma despesa registrada recentemente.")

# --- ESTOQUE ---
elif choice == "📦 Estoque":
    st.title("Gestão de Inventário")
    prods = api.get_products(db, cid)
    df_p = pd.DataFrame([{"Nome": p.name, "Preço": p.price_retail, "Estoque": p.stock, "SKU": p.sku} for p in prods])
    st.table(df_p)