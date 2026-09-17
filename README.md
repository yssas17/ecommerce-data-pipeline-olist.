# Olist E-commerce: Data Pipeline & Analytics

This is a hands-on project focused on data engineering and business intelligence. The objective was to build an end-to-end pipeline using the Olist public e-commerce database to diagnose logistical bottlenecks and correlate this data with end-customer satisfaction.

## Technologies Used
* **Python (Pandas):** Data cleaning, null value handling, and application of business rules.
* **PostgreSQL:** Relational modeling storage (Star Schema).
* **Power BI & DAX:** Data visualization, UI/UX, and metrics (SLA calculation, scatter matrix, etc.).

## Architecture
Instead of importing CSV files directly into Power BI, I structured the project to simulate a real corporate environment:
1. The `olyst.py` script extracts the raw data.
2. Pandas handles the heavy processing (treatment of long-tail categories, imputing package volumes, and stripping residual time from date columns).
3. The transformed data is sent to a Data Warehouse in PostgreSQL via SQLAlchemy.
4. **The Python script automatically orchestrates the database by executing SQL statements to recreate analytical Views (e.g., `vw_kpis_vendedores`), optimizing the data for BI consumption.**
5. Power BI consumes the structured tables and views, ensuring data integrity and enabling the use of a custom `dCalendar` (Date dimension).

## Key Analytical Insights
* **Logistics Cost vs. Satisfaction:** Cross-referencing the data proved that when the delivery time exceeds the 15 to 20-day mark, the customer's rating drops rapidly into the critical zone (below 3.0). This creates an opportunity to set up automated alerts when a package's transit time reaches 70% of the stipulated SLA.
* **Geographical Isolation:** The dashboard highlights that the São Paulo axis dominates sales volume due to an attractive shipping rate (~R$ 15). Consumers in more distant states abandon purchases due to high freight costs, suggesting the need for advanced distribution centers (Hubs) in other regions.
* **Seller Quality (Scatter Matrix):** I created a matrix crossing total revenue and the average rating for each seller. This helps the marketplace algorithm penalize slow sellers in the storefront and prioritize partners who deliver a good experience.
* **Margin Optimization via Freight:** Category analysis revealed that bulky items consume up to 40% of the product's value just in transport, strangling profit margins. This indicates that free shipping campaigns should focus on small, high-ticket products, limiting large deliveries to regional radii.
* **Seasonality Collapse:** The revenue history shows that major sales peaks, like Black Friday, coincide with the worst drops in customer satisfaction (down to the 3.7 range). This demonstrates the urgency of enforcing a logistics capacity ceiling, limiting sales for sellers with a history of delays.
* **Hidden Dispatch Bottleneck:** The logistics flow pointed out that sellers spend an average of 3 days just to dispatch the order, consuming 25% of the customer's total wait time. This suggests the creation of a "24h Shipping" badge, which would organically reduce the platform's overall timeframe without extra costs.

**Sales Overview and Distribution by State**
![Vendas](d3e0b644-c888-4db0-99d6-92a1e650c1a8.png)
![Estados](55283645-fa6d-498a-abc1-40a012a1ec3b.png)

**Delivery SLA Analysis and Seller Performance**
![Reviews](f7989ee2-274f-4d5b-a04f-e83a3c72e5e3.png)
![Vendedores](e714714b-8a3b-4574-bd81-d58e4bfeb916.png)
