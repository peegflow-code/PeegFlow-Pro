# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# --- TABELA DE EMPRESAS (CLIENTES DO SEU SAAS) ---
class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    license_key = Column(String)  # Chave de ativação da licença
    is_active = Column(Boolean, default=True) # Controle de bloqueio/pagamento
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos: Uma empresa tem muitos usuários, produtos, etc.
    users = relationship("User", back_populates="company")
    products = relationship("Product", back_populates="company")
    expenses = relationship("Expense", back_populates="company")

# --- TABELA DE USUÁRIOS ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="user") # superadmin, admin, user
    
    # Vínculo obrigatório com a empresa
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")

# --- TABELA DE PRODUTOS ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True)
    name = Column(String)
    category = Column(String, default="Geral")
    price_retail = Column(Float)   # Preço Varejo
    price_wholesale = Column(Float) # Preço Atacado
    stock = Column(Integer, default=0)
    stock_min = Column(Integer, default=5)
    
    # Multi-tenancy: O produto pertence a uma empresa específica
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="products")

# --- TABELA DE VENDAS ---
class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(Float) # Preço praticado no momento da venda
    kind = Column(String) # 'varejo' ou 'atacado'
    date = Column(DateTime, default=datetime.now)
    
    # Rastreabilidade
    user_id = Column(Integer, ForeignKey("users.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))

# --- TABELA DE DESPESAS (Para o Financeiro) ---
class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    amount = Column(Float)
    category = Column(String)
    date = Column(DateTime, default=datetime.now)
    
    # Vínculo com a empresa
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="expenses")