import hashlib
import random
import pandas as pd
from fpdf import FPDF
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models import User, Product, Sale, Expense, Company

# --- SEGURANÇA ---
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(db: Session, username, password):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password_hash == hash_password(password):
        return user
    return None

def create_initial_data(db: Session):
    if not db.query(Company).filter(Company.id == 1).first():
        master_co = Company(id=1, name="PeegFlow Master", license_key="PF-ROOT", is_active=True)
        db.add(master_co); db.commit()
        admin = User(username="admin", password_hash=hash_password("admin123"), role="superadmin", company_id=1)
        db.add(admin); db.commit()

# --- FUNÇÃO DEMO ROBUSTA (DADOS DE 30 DIAS) ---
def setup_demo_data(db: Session):
    demo_id = 99
    # Garante a empresa demo
    if not db.query(Company).filter(Company.id == demo_id).first():
        demo_co = Company(id=demo_id, name="PeegFlow Tech Store", license_key="DEMO-2026", is_active=True)
        db.add(demo_co); db.commit()
        
    # Garante produtos com SKUs e Preços coerentes com as imagens
    if not db.query(Product).filter(Product.company_id == demo_id).first():
        prods = [
            Product(name="iPhone 15 Pro", price_retail=1200.0, price_wholesale=900.0, stock=50, stock_min=5, sku="IPH-15P", company_id=demo_id),
            Product(name="MacBook M3", price_retail=1850.0, price_wholesale=1400.0, stock=20, stock_min=2, sku="MAC-M3", company_id=demo_id),
            Product(name="AirPods Max", price_retail=540.0, price_wholesale=380.0, stock=40, stock_min=5, sku="AIR-MAX", company_id=demo_id),
            Product(name="Apple Watch", price_retail=450.0, price_wholesale=310.0, stock=60, stock_min=10, sku="WATCH-S9", company_id=demo_id)
        ]
        db.add_all(prods); db.commit()

    # Limpa dados antigos para gerar novos
    db.query(Sale).filter(Sale.company_id == demo_id).delete()
    db.query(Expense).filter(Expense.company_id == demo_id).delete()

    products = db.query(Product).filter(Product.company_id == demo_id).all()
    
    # Gerar 30 dias de histórico
    for i in range(30, -1, -1):
        data_ponto = datetime.now() - timedelta(days=i)
        
        # Vendas (mais volume em dias de semana)
        num_vendas = random.randint(5, 12) if data_ponto.weekday() < 5 else random.randint(2, 5)
        for _ in range(num_vendas):
            p = random.choice(products)
            db.add(Sale(product_id=p.id, quantity=random.randint(1,2), price=p.price_retail, 
                        kind="varejo", user_id=1, company_id=demo_id, date=data_ponto))

        # Despesas Fixas e Variáveis
        if data_ponto.day == 5:
            db.add(Expense(description="Aluguel Mensal", amount=2800.0, category="Aluguel", company_id=demo_id, date=data_ponto))
        if random.random() < 0.2:
            db.add(Expense(description="Marketing/Ads", amount=random.uniform(100, 400), category="Marketing", company_id=demo_id, date=data_ponto))

    db.commit()

# --- DEMAIS FUNÇÕES ---
def get_products(db: Session, company_id: int):
    return db.query(Product).filter(Product.company_id == company_id).all()

def create_product(db: Session, data: dict, company_id: int):
    new_prod = Product(**data, company_id=company_id)
    db.add(new_prod); db.commit()

def process_sale(db: Session, product_id: int, qty: int, kind: str, user_id: int, company_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or product.stock < qty: return False, "Sem estoque"
    product.stock -= qty
    db.add(Sale(product_id=product.id, quantity=qty, price=product.price_retail, kind=kind, user_id=user_id, company_id=company_id))
    db.commit(); return True, "Venda OK"

def get_financial_data(db: Session, company_id: int, days=30):
    start = datetime.now() - timedelta(days=days)
    s_q = db.query(Sale, Product.name).join(Product).filter(Sale.company_id == company_id, Sale.date >= start).statement
    e_q = db.query(Expense).filter(Expense.company_id == company_id, Expense.date >= start).statement
    return pd.read_sql(s_q, db.bind), pd.read_sql(e_q, db.bind)

def get_daily_sales_data(db: Session, company_id: int, days=30):
    start_date = datetime.now() - timedelta(days=days)
    daily = db.query(func.date(Sale.date).label('date'), func.sum(Sale.price).label('total')).filter(Sale.company_id == company_id, Sale.date >= start_date).group_by(func.date(Sale.date)).all()
    return pd.DataFrame(daily, columns=['date', 'total'])

def generate_financial_pdf(df_v, df_e, period, company):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Relatório Financeiro - {company}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, f"Período: {period}", ln=True)
    pdf.cell(0, 10, f"Receitas: € {df_v['price'].sum():,.2f}", ln=True)
    pdf.cell(0, 10, f"Despesas: € {df_e['amount'].sum():,.2f}", ln=True)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Lucro: € {df_v['price'].sum() - df_e['amount'].sum():,.2f}", ln=True)
    return bytes(pdf.output(dest='S'))

# Adicione isso no services.py
def get_financial_by_range(db: Session, company_id: int, start_date: datetime, end_date: datetime):
    # Garante que pegamos até o ultimo segundo do dia final
    if end_date.hour == 0 and end_date.minute == 0:
        end_date = end_date.replace(hour=23, minute=59, second=59)
    
    s_q = db.query(
        Sale.date,
        Sale.quantity,
        Sale.price,
        Product.name.label("product_name")
    ).join(Product).filter(
        Sale.company_id == company_id, 
        Sale.date >= start_date, 
        Sale.date <= end_date
    ).statement
    
    e_q = db.query(
        Expense.date,
        Expense.description,
        Expense.category,
        Expense.amount
    ).filter(
        Expense.company_id == company_id, 
        Expense.date >= start_date, 
        Expense.date <= end_date
    ).statement
            
    try:
        df_sales = pd.read_sql(s_q, db.bind)
        df_expenses = pd.read_sql(e_q, db.bind)
    except Exception:
        df_sales = pd.DataFrame(columns=['date', 'quantity', 'price', 'product_name'])
        df_expenses = pd.DataFrame(columns=['date', 'description', 'category', 'amount'])
    
    return df_sales, df_expenses

# --- services.py (Adicione estas funções no final) ---

def register_product(db: Session, company_id: int, name: str, price_retail: float, price_wholesale: float, stock_min: int, sku: str):
    """Cadastra um novo produto"""
    new_prod = Product(
        name=name,
        price_retail=price_retail,
        price_wholesale=price_wholesale,
        stock=0, # Começa com 0, exige reposição inicial
        stock_min=stock_min,
        sku=sku,
        company_id=company_id
    )
    db.add(new_prod)
    db.commit()
    return True

def restock_product(db: Session, company_id: int, product_id: int, qty: int, cost_unit: float):
    """
    Repõe o estoque e gera uma despesa financeira automaticamente.
    Registra data, quantidade e valor unitário (via Despesa).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return False

    # 1. Atualiza a quantidade no estoque
    product.stock += qty
    
    # 2. Registra o custo dessa reposição no financeiro
    total_cost = qty * cost_unit
    desc = f"Reposição Estoque: {product.name} ({qty}x €{cost_unit:.2f})"
    
    new_expense = Expense(
        description=desc,
        amount=total_cost,
        category="Custo de Mercadoria (CMV)", # Categoria específica para estoque
        company_id=company_id,
        date=datetime.now()
    )
    db.add(new_expense)
    db.commit()
    return True

