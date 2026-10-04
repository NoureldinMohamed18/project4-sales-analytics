from pathlib import Path

import matplotlib
matplotlib.use("Agg")                       # من غير نافذة: يشتغل على أي سيرفر
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from src import analytics

sns.set_theme(style="whitegrid")
MILLIONS = FuncFormatter(lambda v, _: f"{v / 1e6:.1f}M")


def build_report(db_path=analytics.DB_PATH, out_dir="reports"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = analytics.load_sales(db_path)
    files = []

    # 1) الإيراد الشهري
    m = analytics.monthly_sales(df)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sns.lineplot(data=m, x="month", y="revenue", marker="o", ax=ax)
    ax.set_title("Monthly revenue")
    ax.set_xlabel("")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(MILLIONS)
    ax.tick_params(axis="x", rotation=60)
    ax.set_xticks(ax.get_xticks()[::2])
    fig.tight_layout()
    files.append(out / "monthly_revenue.png")
    fig.savefig(files[-1], dpi=130)
    plt.close(fig)

    # 2) الإيراد لكل فرع
    b = analytics.by_branch(df)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(data=b, x="branch", y="revenue", hue="branch", legend=False, ax=ax)
    ax.set_title("Revenue by branch")
    ax.set_xlabel("")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(MILLIONS)
    fig.tight_layout()
    files.append(out / "revenue_by_branch.png")
    fig.savefig(files[-1], dpi=130)
    plt.close(fig)

    # 3) تصنيف × فرع (بالملايين)
    pivot = analytics.category_by_branch(df) / 1e6
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Blues", ax=ax,
                cbar_kws={"label": "Revenue (millions)"})
    ax.set_title("Revenue by category and branch (millions)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    files.append(out / "category_branch_heatmap.png")
    fig.savefig(files[-1], dpi=130)
    plt.close(fig)

    return files


if __name__ == "__main__":
    for f in build_report():
        print("saved", f)
