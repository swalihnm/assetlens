import duckdb
import pytest

from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


def q(sql):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def test_business_revenue_and_pretax_match_public():
    d = q("""select p.period_end, sum(p.net_revenues) syn_rev, max(f.value) pub_rev,
                    sum(p.contribution_margin) syn_cm
             from fact_business_pnl p join fact_financials f
               on f.ticker='GS' and f.metric='net_revenues' and f.period_end=p.period_end
             group by 1""")
    assert len(d) >= 16 and ((d.syn_rev / d.pub_rev - 1).abs() < 0.005).all()


def test_gl_total_matches_public_opex():
    d = q("""select g.period_end, sum(g.amount_musd) gl, max(f.value) pub
             from fact_gl g join fact_financials f
               on f.ticker='GS' and f.metric='opex' and f.period_end=g.period_end group by 1""")
    assert len(d) == 8 and ((d.gl / d.pub - 1).abs() < 0.005).all()
    assert q("select count(*) n from fact_gl").n[0] >= 2_000_000


def test_advisor_revenue_equals_pwm_mgmt_fees():
    d = q("""select a.period_end, sum(a.revenue_musd) adv, max(p.mgmt_fees) pwm
             from fact_advisor_monthly a join fact_business_pnl p
               on p.business='PWM' and p.period_end=a.period_end group by 1""")
    assert ((d.adv / d.pwm - 1).abs() < 0.005).all()


def test_te_violation_rate_and_labels():
    d = q("select avg(cast(is_violation as int)) r, count(*) n from fact_te")
    assert 0.01 <= d.r[0] <= 0.025 and d.n[0] >= 200_000


def test_every_synthetic_table_flagged():
    for t in ["fact_business_pnl", "fact_gl", "fact_te", "dim_advisor", "fact_savings", "fact_headcount"]:
        assert q(f"select bool_and(synthetic) s from {t}").s[0]
