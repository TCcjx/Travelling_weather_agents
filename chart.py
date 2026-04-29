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
    fig, ax = plt.subplots(figsize=(12, 7), facecolor='#f8f9fa')
    ax.set_facecolor('#ffffff')

    # 绑制折线 - 使用渐变配色
    line_high, = ax.plot(dates, temp_max, color='#e74c3c', linewidth=2.5,
                          marker='o', markersize=10, markerfacecolor='#ffffff',
                          markeredgewidth=2, markeredgecolor='#e74c3c',
                          label='High Temp', zorder=3)
    line_low, = ax.plot(dates, temp_min, color='#3498db', linewidth=2.5,
                         marker='o', markersize=10, markerfacecolor='#ffffff',
                         markeredgewidth=2, markeredgecolor='#3498db',
                         label='Low Temp', zorder=3)

    # 填充区域 - 渐变效果
    ax.fill_between(dates, temp_max, temp_min, alpha=0.3, color='#fab1a0',
                     zorder=2)

    # 设置标题和标签
    ax.set_title(f'{city} 7-Day Weather Forecast', fontsize=18, fontweight='bold',
                 color='#2c3e50', pad=20)
    ax.set_xlabel('Date', fontsize=13, color='#34495e', labelpad=10)
    ax.set_ylabel('Temperature (°C)', fontsize=13, color='#34495e', labelpad=10)

    # 格式化x轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=45, ha='right', fontsize=11, color='#34495e')
    plt.yticks(fontsize=11, color='#34495e')

    # 添加图例 - 样式优化
    legend = ax.legend(loc='upper left', fontsize=11, framealpha=0.9,
                       edgecolor='#bdc3c7', facecolor='#ffffff')

    # 添加网格 - 更柔和
    ax.grid(True, linestyle='--', alpha=0.4, color='#bdc3c7', zorder=1)

    # 设置边框
    for spine in ax.spines.values():
        spine.set_color('#bdc3c7')
        spine.set_linewidth(1)

    # 在每个点上标注温度
    for d, max_t, min_t in zip(dates, temp_max, temp_min):
        ax.annotate(f'{max_t:.0f}°', (d, max_t), textcoords="offset points",
                   xytext=(0, 12), ha='center', fontsize=10, fontweight='bold',
                   color='#c0392b')
        ax.annotate(f'{min_t:.0f}°', (d, min_t), textcoords="offset points",
                   xytext=(0, -18), ha='center', fontsize=10, fontweight='bold',
                   color='#2980b9')

    # 添加天气状况标注
    for d, cond, min_t in zip(dates, conditions, temp_min):
        ax.annotate(cond, (d, min_t), textcoords="offset points",
                   xytext=(0, -35), ha='center', fontsize=9, color='#7f8c8d',
                   style='italic')

    # 设置y轴范围，留出标注空间
    y_min = min(temp_min) - 8
    y_max = max(temp_max) + 8
    ax.set_ylim(y_min, y_max)

    plt.tight_layout()

    # 保存
    today = datetime.now().strftime("%Y%m%d")
    filename = f"{city}_{today}.png"
    filepath = os.path.join(save_dir, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight',
                facecolor='#f8f9fa', edgecolor='none')
    plt.close()

    return filepath
