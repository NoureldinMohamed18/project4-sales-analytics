-- كل استعلام بيبدأ بسطر "-- name: <اسم>" ، والـ API بيقرأ الملف ده مباشرة.
-- شغّلهم يدوياً من أي SQLite client لو عايز تجرّب.

-- name: branch_rank_per_month
-- RANK() + PARTITION BY: ترتيب الفروع جوه كل شهر لوحده
WITH monthly AS (
    SELECT strftime('%Y-%m', order_date) AS month,
           branch,
           ROUND(SUM(total_amount), 2)   AS revenue
    FROM sales
    GROUP BY month, branch
)
SELECT month, branch, revenue,
       RANK() OVER (PARTITION BY month ORDER BY revenue DESC) AS rank_in_month
FROM monthly
ORDER BY month, rank_in_month;

-- name: running_total
-- SUM() OVER: إجمالي تراكمي بمرور الشهور
WITH monthly AS (
    SELECT strftime('%Y-%m', order_date) AS month,
           ROUND(SUM(total_amount), 2)   AS revenue
    FROM sales
    GROUP BY month
)
SELECT month, revenue,
       ROUND(SUM(revenue) OVER (ORDER BY month
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS cumulative_revenue
FROM monthly
ORDER BY month;

-- name: mom_growth
-- LAG(): قيمة الشهر اللي قبله، ومنها نسبة النمو
WITH monthly AS (
    SELECT strftime('%Y-%m', order_date) AS month,
           ROUND(SUM(total_amount), 2)   AS revenue
    FROM sales
    GROUP BY month
),
with_prev AS (
    SELECT month, revenue,
           LAG(revenue) OVER (ORDER BY month) AS prev_revenue
    FROM monthly
)
SELECT month, revenue, prev_revenue,
       ROUND((revenue - prev_revenue) * 100.0 / prev_revenue, 1) AS growth_pct
FROM with_prev
ORDER BY month;

-- name: top_product_per_category
-- ROW_NUMBER(): أول منتج بس في كل تصنيف
WITH per_product AS (
    SELECT category, product, ROUND(SUM(total_amount), 2) AS revenue
    FROM sales
    GROUP BY category, product
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rn
    FROM per_product
)
SELECT category, product, revenue
FROM ranked
WHERE rn = 1
ORDER BY revenue DESC;

-- name: customer_quartiles
-- NTILE(4): نقسم العملاء 4 شرايح حسب الإنفاق (1 = أعلى 25%)
WITH per_customer AS (
    SELECT customer_id, ROUND(SUM(total_amount), 2) AS revenue
    FROM sales
    GROUP BY customer_id
),
bucketed AS (
    SELECT customer_id, revenue,
           NTILE(4) OVER (ORDER BY revenue DESC) AS quartile
    FROM per_customer
)
SELECT quartile,
       COUNT(*)                   AS customers,
       ROUND(SUM(revenue), 2)     AS revenue,
       ROUND(AVG(revenue), 2)     AS avg_revenue
FROM bucketed
GROUP BY quartile
ORDER BY quartile;
