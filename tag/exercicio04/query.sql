-- Query para trazer informações de crescimento das transações dos últimos 6 meses
-- ordenadas por mês e categoria, conforme especificações do framework TAG.

SELECT 
    TO_CHAR(created_at, 'YYYY-MM') AS mes,
    category AS categoria,
    COUNT(*) AS quantidade_transacoes,
    (SUM(amount_cents) / 100.0)::NUMERIC(15, 2) AS volume_total_reais
FROM 
    transactions
WHERE 
    status = 'completed'
    AND category IN ('subscription', 'one_time', 'refund', 'credit_adjustment')
    AND created_at >= '2026-04-24'::date - INTERVAL '6 months'
    AND created_at < '2026-04-25'::date
GROUP BY 
    TO_CHAR(created_at, 'YYYY-MM'),
    category
ORDER BY 
    mes ASC,
    categoria ASC;
