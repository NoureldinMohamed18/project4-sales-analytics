from src import analytics
from src.dashboard import build_figures, create_app
from src.report import build_report


def test_report_creates_non_empty_pngs(db, tmp_path):
    files = build_report(db, tmp_path / "out")
    assert len(files) == 3
    for f in files:
        assert f.exists() and f.stat().st_size > 5_000


def test_dashboard_figures_are_built(db):
    figs = build_figures(analytics.load_sales(db))
    assert len(figs) == 3 and all(len(f.data) >= 1 for f in figs)


def test_dashboard_callback_handles_filters_and_empty_range(db):
    app = create_app(db)
    kpis, *figs = app._update("Cairo", "2024-01-01", "2024-12-31")
    assert len(kpis) == 4 and len(figs) == 3
    kpis, *figs = app._update("All", "2999-01-01", "2999-12-31")   # فاضي: مايقعش
    assert len(kpis) == 4
