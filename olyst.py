import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load hidden environment variables from the .env file
load_dotenv()

def extract_data():
    print("Starting data extraction (CSV)...")
    df_customers = pd.read_csv('data/olist_customers_dataset.csv')
    df_products = pd.read_csv('data/olist_products_dataset.csv')
    df_orders = pd.read_csv('data/olist_orders_dataset.csv')
    df_itens = pd.read_csv('data/olist_order_items_dataset.csv')
    df_reviews = pd.read_csv('data/olist_order_reviews_dataset.csv')
    df_sellers = pd.read_csv('data/olist_sellers_dataset.csv')

    return df_customers, df_products, df_orders, df_itens, df_reviews, df_sellers

def transform_data(df_customers, df_products, df_orders, df_itens, df_reviews, df_sellers):
    print("Applying business rules and cleaning data...")
    df_reviews['review_answer_timestamp'] = pd.to_datetime(df_reviews['review_answer_timestamp'])
    df_reviews = df_reviews.sort_values(by='review_answer_timestamp')
    
    # Basic Dimensions
    dim_reviews = df_reviews.drop_duplicates(subset=['order_id'], keep='last').copy()
    dim_reviews = dim_reviews[['review_id', 'order_id', 'review_score']].copy()

    dim_sellers = df_sellers[['seller_id','seller_state','seller_city']].copy()
    dim_sellers.drop_duplicates(subset=['seller_id'], inplace=True)
    
    dim_customer = df_customers[['customer_id','customer_city','customer_state']].copy()
    dim_customer.drop_duplicates(subset=['customer_id'], inplace=True)

    # Products Dimension Treatment
    dim_products = df_products[['product_id', 'product_category_name', 'product_weight_g', 
                                'product_length_cm', 'product_height_cm', 'product_width_cm']].copy()

    dim_products['product_category_name'] = dim_products['product_category_name'].fillna('Outros')
    dim_products['product_category_name'] = dim_products['product_category_name'].str.replace('_', ' ').str.title()
    
    category_counts = dim_products['product_category_name'].value_counts()
    cutoff_limit = category_counts.quantile(0.10)
    rare_categories = category_counts[category_counts < cutoff_limit].index
    dim_products.loc[dim_products['product_category_name'].isin(rare_categories), 'product_category_name'] = 'Outros'

    measurement_columns = ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']
    for measure in measurement_columns:
        dim_products[measure] = dim_products[measure].fillna(
            dim_products.groupby('product_category_name')[measure].transform('mean')
        ).fillna(0)
        
    dim_products['volume_cm3'] = (dim_products['product_length_cm'] * 
                                  dim_products['product_height_cm'] * 
                                  dim_products['product_width_cm'])

    dim_product_final = dim_products.copy()
    dim_product_final.drop(columns=['product_length_cm','product_height_cm','product_width_cm'], inplace=True)

    # Fact Table
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
    
    dim_reviews = dim_reviews[dim_reviews['order_id'].isin(facts_orders['order_id'])]
    
    return dim_reviews, dim_customer, dim_product_final, dim_sellers, facts_orders

def load_data(dim_reviews, dim_customer, dim_product_final, dim_sellers, facts_orders):
    print("Connecting to PostgreSQL and loading data...")
    
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("CRITICAL ERROR: Credentials not found. Please check your .env file.")
        return

    try:
        engine = create_engine(db_url)
        
        # 1. Drop the view first to unlock the facts_orders table
        with engine.begin() as conn:
            conn.execute(text("DROP VIEW IF EXISTS vw_kpis_vendedores CASCADE;"))
            
        # 2. Replace the existing tables with the new data
        dim_reviews.to_sql('dim_reviews', con=engine, if_exists='replace', index=False)
        dim_customer.to_sql('dim_customer', con=engine, if_exists='replace', index=False)
        dim_product_final.to_sql('dim_products', con=engine, if_exists='replace', index=False)
        dim_sellers.to_sql('dim_sellers', con=engine, if_exists='replace', index=False)
        facts_orders.to_sql('facts_orders', con=engine, if_exists='replace', index=False)
        
        # 3. Python automatically recreates the View with the updated data
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE OR REPLACE VIEW vw_kpis_vendedores AS
                SELECT 
                    seller_id,
                    COUNT(DISTINCT order_id) AS total_pedidos,
                    SUM(price) AS faturamento_total,
                    AVG(review_score) AS avaliacao_media
                FROM facts_orders
                GROUP BY seller_id;
            """))
            
        print("ETL successfully completed! Views recreated. Data is in PostgreSQL ready for Power BI.")
    except Exception as e:
        print(f"Error loading data into the database: {e}")

# Script Orchestrator
if __name__ == '__main__':
    dfs = extract_data()
    dim_reviews, dim_customer, dim_product_final, dim_sellers, facts_orders = transform_data(*dfs)
    load_data(dim_reviews, dim_customer, dim_product_final, dim_sellers, facts_orders)

# Orquestrador do Script
if __name__ == '__main__':
    dfs = extract_data()
    dim_customer, dim_product_final, dim_sellers, facts_orders = transform_data(*dfs)
    load_data(dim_customer, dim_product_final, dim_sellers, facts_orders)
