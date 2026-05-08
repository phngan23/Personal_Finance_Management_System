# ============================================================
# FILE: app/reports.py
# PURPOSE: Generate matplotlib charts from DB data
# Each function returns a matplotlib Figure object,
# which main.py embeds into the CustomTkinter UI.
# ============================================================

import matplotlib
matplotlib.use('TkAgg')          # Use TkAgg backend for CustomTkinter compatibility
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.figure import Figure
import numpy as np

from models import get_monthly_summary, get_category_spending, get_balance_trend


def format_vnd(value, _=None):
    """Format axis tick labels as Vietnamese Dong (e.g., 15,000,000)."""
    if value >= 1_000_000:
        return f'{value/1_000_000:.0f}M'
    return f'{value:,.0f}'


def create_income_expense_chart(user_id, months=6) -> Figure:
    """
    Bar chart: Compare monthly income vs expenses for the last N months.

    Design decisions:
    - Side-by-side bars (not stacked) for easy comparison
    - Green for income, red for expenses (universal financial color coding)
    - Y-axis formatted in millions VND to avoid clutter
    """
    data = get_monthly_summary(user_id, months)

    # Reverse so oldest month is on the left
    data = list(reversed(data))

    if not data:
        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, color='gray')
        return fig

    months_labels = [row['MonthYear'] for row in data]
    income_vals   = [float(row['TotalIncome'])   for row in data]
    expense_vals  = [float(row['TotalExpenses']) for row in data]

    x = np.arange(len(months_labels))
    bar_width = 0.35

    fig = Figure(figsize=(9, 5), dpi=100)
    ax = fig.add_subplot(111)

    bars1 = ax.bar(x - bar_width/2, income_vals,  bar_width, label='Income',   color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + bar_width/2, expense_vals, bar_width, label='Expenses', color='#e74c3c', alpha=0.8)

    # Add value labels on top of each bar
    for bar in bars1 + bars2:
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                format_vnd(height),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=8
            )

    ax.set_title('Monthly Income vs Expenses', fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Month', fontsize=13)
    ax.set_ylabel('Amount (VND)', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(months_labels, rotation=20, fontsize=13, ha='right')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(format_vnd))
    ax.legend(fontsize=13)
    ax.grid(axis='y', alpha=0.2)
    ax.margins(x=0.15)
    
    # Tooltip ẩn (sẽ được điều khiển bởi main.py)
    annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)
    
    fig.tight_layout()

    return fig


def create_category_pie_chart(user_id, month_year) -> Figure:
    """
    Pie chart: Spending distribution by category for a given month.

    Design decisions:
    - Explode the largest slice slightly to highlight it
    - Show both percentage and absolute amount in legend
    - Use a colorblind-friendly palette
    """
    data = get_category_spending(user_id, month_year)

    fig = Figure(figsize=(8, 5), dpi=100)
    ax = fig.add_subplot(111)

    if not data:
        ax.text(0.5, 0.5, f'No expenses recorded for {month_year}',
                ha='center', va='center', transform=ax.transAxes,
                fontsize=13, color='gray')
        return fig

    labels = [row['CategoryName'] for row in data]
    sizes  = [float(row['TotalSpent']) for row in data]

    # Explode the biggest slice
    max_idx = sizes.index(max(sizes))
    explode = [0.05 if i == max_idx else 0 for i in range(len(sizes))]

    #colors = plt.cm.Set3.colors[:len(labels)]
    colors = plt.cm.Pastel1.colors[:len(labels)]

    wedges, texts, autotexts = ax.pie(
        sizes,
        explode=explode,
        labels=None,                  # we use legend instead of inline labels
        colors=colors,
        autopct='%1.1f%%',
        startangle=140,
        pctdistance=0.75,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
    )

    # Chỉnh cỡ chữ phần trăm bên trong pie
    for autotext in autotexts:
        autotext.set_fontsize(14)
        autotext.set_fontweight('bold')

    # Build legend with amount info
    legend_labels = [
        f"{label}: {amount/1_000_000:.2f}M VND"
        for label, amount in zip(labels, sizes)
    ]
    ax.legend(wedges, legend_labels, title='Categories',
              loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), fontsize=12, title_fontsize=13)

    ax.set_title(f'Spending by Category — {month_year}',
                 fontsize=18, fontweight='bold', pad=20)
    
    annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    annot.set_visible(False)

    fig.tight_layout()

    return fig


def create_balance_trend_chart(user_id) -> Figure:
    """
    Line chart: Running balance trend over time.

    Design decisions:
    - Use cumulative sum to show trajectory
    - Shade the area under the line for visual impact
    - Mark each data point with a dot
    """
    data = get_balance_trend(user_id)

    fig = Figure(figsize=(9, 5), dpi=100)
    ax = fig.add_subplot(111)

    if not data:
        ax.text(0.5, 0.5, 'No transaction history available',
                ha='center', va='center', transform=ax.transAxes,
                fontsize=15, color='gray')
        return fig

    months  = [row['MonthYear'] for row in data]
    monthly = [float(row['MonthlyNet']) for row in data]

    # Cumulative running balance (starting from 0 relative baseline)
    running = np.cumsum(monthly)

    ax.plot(months, running, 'o-', color='#3498db', linewidth=3,
            markersize=10, markerfacecolor='white', markeredgewidth=2)

    # Shade positive/negative regions
    ax.fill_between(months, running, alpha=0.1, color='#3498db')

    # Add zero line for reference
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    ax.margins(x=0.2)

    # Annotate last point
    ax.annotate(
        format_vnd(running[-1]),
        xy=(months[-1], running[-1]),
        xytext=(-10, 15), textcoords='offset points',
        ha='right', fontsize=13, fontweight='bold', color='#2980b9'
    )

    ax.set_title('Net Balance Trend Over Time', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Month', fontsize=11)
    ax.set_ylabel('Cumulative Net (VND)', fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(format_vnd))
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=30, ha='right')
    annot = ax.annotate("", xy=(0,0), xytext=(15,15), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    annot.set_visible(False)
    ax.grid(alpha=0.2)
    fig.tight_layout()

    return fig


def save_chart(figure: Figure, filename: str):
    """Save a chart to PNG file. Call from UI if user wants to export."""
    figure.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"[REPORT] Chart saved to {filename}")