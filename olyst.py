import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carrega as variáveis de ambiente ocultas do arquivo .env
load_dotenv()

def extract_data():
    print("Iniciando extração dos dados (CSV)...")
    df_customers = pd.read_csv('data/olist_customers_dataset.csv')
    df_products = pd.read_csv('data/olist_products_dataset.csv')
    df_orders = pd.read_csv('data/olist_orders_dataset.csv')
    df_itens = pd.read_csv('data/olist_order_items_dataset.csv')
    df_reviews = pd.read_csv('data/olist_order_reviews_dataset.csv')
    df_sellers = pd.read_csv('data/olist_sellers_dataset.csv')
    
    return df_customers, df_products, df_orders, df_itens, df_reviews, df_sellers

def transform_data(df_customers, df_products, df_orders, df_itens, df_reviews, df_sellers):
    print("Aplicando regras de negócio e limpando dados...")
    
    # Dimensões Básicas
    dim_reviews = df_reviews[['review_id','order_id','review_score']].copy()
    dim_sellers = df_sellers[['seller_id','seller_state','seller_city']].copy()
    dim_sellers.drop_duplicates(subset=['seller_id'], inplace=True)
    
    dim_customer = df_customers[['customer_id','customer_city','customer_state']].copy()
    dim_customer.drop_duplicates(subset=['customer_id'], inplace=True)

    # Tratamento da Dimensão Produtos
    dim_products = df_products[['product_id', 'product_category_name', 'product_weight_g', 
                                'product_length_cm', 'product_height_cm', 'product_width_cm']].copy()

    dim_products['product_category_name'] = dim_products['product_category_name'].fillna('Outros')
    dim_products['product_category_name'] = dim_products['product_category_name'].str.replace('_', ' ').str.title()
    
    contagem_categorias = dim_products['product_category_name'].value_counts()
    limite_corte = contagem_categorias.quantile(0.10)
    poucos_na_categoria = contagem_categorias[contagem_categorias < limite_corte].index
    dim_products.loc[dim_products['product_category_name'].isin(poucos_na_categoria), 'product_category_name'] = 'Outros'

    colunas_medidas = ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']
    for medidas in colunas_medidas:
        dim_products[medidas] = dim_products[medidas].fillna(
            dim_products.groupby('product_category_name')[medidas].transform('mean')
        ).fillna(0)
        
    dim_products['volume_cm3'] = (dim_products['product_length_cm'] * 
                                  dim_products['product_height_cm'] * 
                                  dim_products['product_width_cm'])

    dim_product_final = dim_products.copy()
    dim_product_final.drop(columns=['product_length_cm','product_height_cm','product_width_cm'], inplace=True)

    # Tabela Fato
    df_reviews_media = df_reviews.groupby('order_id')['review_score'].mean().reset_index()
    facts_orders = pd.merge(df_itens, df_orders, on='order_id', how='inner').merge(df_reviews_media, on='order_id', how='left')

    facts_orders = facts_orders[[
        'order_id', 'customer_id', 'seller_id', 'product_id', 'price', 'freight_value',
        'order_status', 'order_purchase_timestamp', 'order_approved_at', 
        'order_delivered_carrier_date', 'order_delivered_customer_date',
        'order_estimated_delivery_date', 'review_score'
    ]].copy()

    facts_orders['order_purchase_timestamp'] = pd.to_datetime(facts_orders['order_purchase_timestamp'])
    facts_orders['order_delivered_customer_date'] = pd.to_datetime(facts_orders['order_delivered_customer_date'])
    
    facts_orders['days_to_deliver'] = (facts_orders['order_delivered_customer_date'] - facts_orders['order_purchase_timestamp']).dt.days

    facts_orders['order_situation'] = facts_orders['order_status'].apply(
        lambda x: 'Delivered' if x == 'delivered' else ('Canceled' if x == 'canceled' else 'Ongoing')
    )
    
    return dim_customer, dim_product_final, dim_sellers, facts_orders

def load_data(dim_customer, dim_product_final, dim_sellers, facts_orders):
    print("Conectando ao PostgreSQL e carregando dados...")
    
    url_banco = os.getenv('DATABASE_URL')
    
    if not url_banco:
        print("ERRO CRÍTICO: Credenciais não encontradas. Verifique o arquivo .env")
        return

    try:
        engine = create_engine(url_banco)
        dim_customer.to_sql('dim_customer', con=engine, if_exists='replace', index=False)
        dim_product_final.to_sql('dim_products', con=engine, if_exists='replace', index=False)
        dim_sellers.to_sql('dim_sellers', con=engine, if_exists='replace', index=False)
        facts_orders.to_sql('facts_orders', con=engine, if_exists='replace', index=False)
        print("ETL concluído com sucesso! Os dados estão no PostgreSQL prontos para o Power BI.")
    except Exception as e:
        print(f"Erro ao enviar para o banco de dados: {e}")

# Orquestrador do Script
if __name__ == '__main__':
    dfs = extract_data()
    dim_customer, dim_product_final, dim_sellers, facts_orders = transform_data(*dfs)
    load_data(dim_customer, dim_product_final, dim_sellers, facts_orders)