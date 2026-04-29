"""天气图表生成模块"""
import os
from datetime import datetime
from typing import List, Dict

try:
    import matplotlib
    matplotlib.use('Agg')  # 无头模式
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def generate_forecast_chart(city: str, forecast: List[Dict],
                          save_dir: str = "./weather_charts") -> str:
    """生成7天天气预报图表

    Args:
        city: 城市名
        forecast: 预报数据列表
        save_dir: 保存目录

    Returns:
        保存的文件路径
    """
    if not HAS_MATPLOTLIB:
        print("[chart] matplotlib not installed, skipping chart generation")
        return ""

    os.makedirs(save_dir, exist_ok=True)

    # 配置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 准备数据
    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in forecast]
    temp_max = [d["temp_max"] for d in forecast]
    temp_min = [d["temp_min"] for d in forecast]
    conditions = [d["condition"] for d in forecast]

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6))

    # 绑制折线
    ax.plot(dates, temp_max, 'r-o', label='High', linewidth=2, markersize=8)
    ax.plot(dates, temp_min, 'b-o', label='Low', linewidth=2, markersize=8)

    # 填充区域
    ax.fill_between(dates, temp_max, temp_min, alpha=0.2, color='orange')

    # 设置标题和标签（使用英文避免中文问题）
    ax.set_title(f'{city} 7-Day Forecast', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Temperature (C)', fontsize=12)

    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=45)

    # 添加图例
    ax.legend(loc='upper right', fontsize=10)

    # 添加网格
    ax.grid(True, linestyle='--', alpha=0.7)

    # 在每个点上标注温度
    for i, (d, max_t, min_t) in enumerate(zip(dates, temp_max, temp_min)):
        ax.annotate(f'{max_t:.0f}C', (d, max_t), textcoords="offset points",
                   xytext=(0, 10), ha='center', fontsize=9, color='red')
        ax.annotate(f'{min_t:.0f}C', (d, min_t), textcoords="offset points",
                   xytext=(0, -15), ha='center', fontsize=9, color='blue')

    # 添加天气状况标注
    for i, (d, cond) in enumerate(zip(dates, conditions)):
        ax.annotate(cond, (d, temp_min[i]), textcoords="offset points",
                   xytext=(0, -30), ha='center', fontsize=8, color='gray')

    plt.tight_layout()

    # 保存
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{city}_{today}.png"
    filepath = os.path.join(save_dir, filename)
    plt.savefig(filepath, dpi=100)
    plt.close()

    return filepath
