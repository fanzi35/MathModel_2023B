import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Arc

from config import (
    ALPHA_DEG,
    CENTER_DEPTH,
    DEPTH_FIGURE_NAME,
    DISTANCES_M,
    FIGURE_OUTPUT_DIR,
    LINE_SPACING_M,
    RESULT1_TABLE_NAME,
    RESULT1_XLSX_NAME,
    SECTION_FIGURE_NAME,
    SECTION_SAMPLE_INDEX,
    TABLE_OUTPUT_DIR,
    TEMPLATE_RESULT1,
    THETA_DEG,
    WIDTH_OVERLAP_FIGURE_NAME,
)
from utils import configure_matplotlib, ensure_directory, format_number, save_result1_excel, save_table_csv


def calculate_question1_results():
    """计算第一问各测线的水深、覆盖宽度和重叠率。"""
    alpha = np.deg2rad(ALPHA_DEG)
    theta = np.deg2rad(THETA_DEG)
    beta = theta / 2.0

    distance_m = np.asarray(DISTANCES_M, dtype=float)

    # 横坐标越大，海水越浅
    depth_m = CENTER_DEPTH - distance_m * np.tan(alpha)

    # 老师图中的 W1、W2 为沿坡面两侧宽度
    left_width_m = depth_m * np.sin(beta) / np.cos(beta + alpha)
    right_width_m = depth_m * np.sin(beta) / np.cos(beta - alpha)
    width_m = left_width_m + right_width_m

    overlap_rate = np.full(distance_m.shape, np.nan, dtype=float)
    overlap_length_m = np.full(distance_m.shape, np.nan, dtype=float)
    overlap_length_m[1:] = (right_width_m[:-1] + left_width_m[1:]) * np.cos(alpha) - LINE_SPACING_M
    overlap_rate[1:] = 1.0 - LINE_SPACING_M / (
        (right_width_m[:-1] + left_width_m[1:]) * np.cos(alpha)
    )

    return pd.DataFrame(
        {
            "distance_m": distance_m,
            "depth_m": depth_m,
            "left_width_m": left_width_m,
            "right_width_m": right_width_m,
            "width_m": width_m,
            "overlap_length_m": overlap_length_m,
            "overlap_rate": overlap_rate,
            "overlap_rate_pct": overlap_rate * 100.0,
        }
    )


def get_section_angle_labels():
    """返回截面示意图中的角度与变量标注。"""
    return {
        "spacing": r"$d$",
        "left_depth": r"$D_i$",
        "right_depth": r"$D_j$",
        "left_width": r"$W_i$",
        "right_width": r"$W_j$",
        "overlap": r"$L$",
        "slope_angle": r"$\alpha$",
        "apex_angle": r"$\theta$",
        "left_bottom_angle": r"$\frac{\pi-\theta}{2}-\alpha$",
        "right_bottom_angle": r"$\frac{\pi-\theta}{2}+\alpha$",
    }


def build_result_table(result_df):
    """生成结果表格副本。"""
    columns = ["指标"] + [str(int(v)) for v in result_df["distance_m"].tolist()]
    rows = [
        ["海水深度/m"] + [format_number(v) for v in result_df["depth_m"].tolist()],
        ["覆盖宽度/m"] + [format_number(v) for v in result_df["width_m"].tolist()],
        ["与前一条测线的重叠率/%", "——"]
        + [format_number(v) for v in result_df["overlap_rate_pct"].iloc[1:].tolist()],
    ]
    return pd.DataFrame(rows, columns=columns)


def _seabed_depth(x_coord, alpha_rad):
    """计算坡面上指定横坐标处的水深。"""
    return CENTER_DEPTH - x_coord * np.tan(alpha_rad)


def build_section_geometry(result_df):
    """构造两测线截面示意图所需几何信息。"""
    alpha = np.deg2rad(ALPHA_DEG)
    labels = get_section_angle_labels()

    lines = []
    for idx, name in zip(SECTION_SAMPLE_INDEX, ["i", "j"]):
        row = result_df.iloc[idx]
        apex_x = float(row["distance_m"])
        apex_y = 0.0
        left_x = apex_x - row["left_width_m"] * np.cos(alpha)
        right_x = apex_x + row["right_width_m"] * np.cos(alpha)
        left_y = _seabed_depth(left_x, alpha)
        center_y = float(row["depth_m"])
        right_y = _seabed_depth(right_x, alpha)
        lines.append(
            {
                "name": name,
                "apex": (apex_x, apex_y),
                "left_foot": (left_x, left_y),
                "center_foot": (apex_x, center_y),
                "right_foot": (right_x, right_y),
            }
        )

    left_line, right_line = lines
    overlap_start = right_line["left_foot"][0]
    overlap_end = left_line["right_foot"][0]
    overlap_mid_x = (overlap_start + overlap_end) / 2.0
    overlap_mid_y = _seabed_depth(overlap_mid_x, alpha)

    left_base_x = left_line["left_foot"][0] - 90
    right_base_x = right_line["right_foot"][0] + 110
    base_y = left_line["left_foot"][1]
    right_base_y = _seabed_depth(right_base_x, alpha)

    return {
        "labels": labels,
        "alpha_rad": alpha,
        "lines": lines,
        "points": {
            "A": left_line["left_foot"],
            "B": left_line["center_foot"],
            "C": (overlap_mid_x, overlap_mid_y),
        },
        "overlap": {
            "start": (overlap_start, _seabed_depth(overlap_start, alpha)),
            "end": (overlap_end, _seabed_depth(overlap_end, alpha)),
            "mid": (overlap_mid_x, overlap_mid_y),
        },
        "spacing": {
            "left_top": left_line["apex"],
            "right_top": right_line["apex"],
        },
        "baseline": {
            "left_start": (left_base_x, base_y),
            "left_end": (left_line["left_foot"][0], base_y),
            "right_end": (right_base_x, right_base_y),
        },
    }


def _draw_angle_arc(ax, center, width, height, theta1, theta2, color="black", lw=1.2):
    """绘制角标圆弧。"""
    arc = Arc(center, width=width, height=height, angle=0, theta1=theta1, theta2=theta2, linewidth=lw, color=color)
    ax.add_patch(arc)


def create_section_figure(result_df):
    """创建第一问两测线截面示意图。"""
    configure_matplotlib()
    geometry = build_section_geometry(result_df)
    labels = geometry["labels"]
    alpha = geometry["alpha_rad"]
    left_line, right_line = geometry["lines"]
    point_a = geometry["points"]["A"]
    point_b = geometry["points"]["B"]
    point_c = geometry["points"]["C"]
    overlap = geometry["overlap"]
    baseline = geometry["baseline"]

    fig, ax = plt.subplots(figsize=(10.5, 4.8))

    # 海坡与底边
    seabed_x = np.linspace(baseline["left_start"][0], baseline["right_end"][0], 300)
    seabed_y = _seabed_depth(seabed_x, alpha)
    ax.plot(seabed_x, seabed_y, color="#666666", linewidth=2.0)
    ax.plot(
        [baseline["left_start"][0], baseline["left_end"][0]],
        [baseline["left_start"][1], baseline["left_end"][1]],
        color="#666666",
        linewidth=1.5,
    )

    # 两条测线
    for line in (left_line, right_line):
        ax.plot(
            [line["apex"][0], line["left_foot"][0]],
            [line["apex"][1], line["left_foot"][1]],
            color="#444444",
            linewidth=1.7,
        )
        ax.plot(
            [line["apex"][0], line["right_foot"][0]],
            [line["apex"][1], line["right_foot"][1]],
            color="#444444",
            linewidth=1.7,
        )
        ax.plot(
            [line["apex"][0], line["center_foot"][0]],
            [line["apex"][1], line["center_foot"][1]],
            linestyle="--",
            color="#777777",
            linewidth=1.4,
        )

    # 顶部间距 d
    top_y = -7
    left_top = geometry["spacing"]["left_top"]
    right_top = geometry["spacing"]["right_top"]
    ax.plot([left_top[0], left_top[0]], [top_y + 2.5, 3], color="#555555", linewidth=1.2)
    ax.plot([right_top[0], right_top[0]], [top_y + 2.5, 3], color="#555555", linewidth=1.2)
    ax.annotate(
        "",
        xy=(right_top[0], top_y),
        xytext=(left_top[0], top_y),
        arrowprops={"arrowstyle": "<->", "linewidth": 1.2, "color": "#555555"},
    )
    ax.text((left_top[0] + right_top[0]) / 2, top_y - 3.5, labels["spacing"], fontsize=13, ha="center")

    # 变量标注
    ax.text(left_line["apex"][0] + 9, left_line["center_foot"][1] * 0.48, labels["left_depth"], fontsize=13)
    ax.text(right_line["apex"][0] + 9, right_line["center_foot"][1] * 0.52, labels["right_depth"], fontsize=13)
    ax.text(
        (left_line["left_foot"][0] + left_line["right_foot"][0]) / 2,
        left_line["center_foot"][1] + 7.5,
        labels["left_width"],
        fontsize=13,
        ha="center",
    )
    ax.text(
        (right_line["left_foot"][0] + right_line["right_foot"][0]) / 2,
        right_line["center_foot"][1] + 7.5,
        labels["right_width"],
        fontsize=13,
        ha="center",
    )

    # A、B、C 点
    ax.text(point_a[0] - 8, point_a[1] - 2.5, "A", fontsize=12)
    ax.text(point_b[0] + 6, point_b[1] + 1.5, "B", fontsize=12)
    ax.text(point_c[0] + 5, point_c[1] - 2.5, "C", fontsize=12)

    # 重叠段
    ax.plot(
        [overlap["start"][0], overlap["end"][0]],
        [overlap["start"][1], overlap["end"][1]],
        color="#d62728",
        linewidth=3.0,
    )
    ax.text(overlap["mid"][0] + 10, overlap["mid"][1] + 5.5, labels["overlap"], color="#d62728", fontsize=13)

    # 左下角 alpha
    slope_center = (point_a[0] + 24, point_a[1])
    _draw_angle_arc(ax, slope_center, 38, 18, 0, ALPHA_DEG)
    ax.text(slope_center[0] + 14, slope_center[1] - 2.5, labels["slope_angle"], fontsize=13)

    # 左测线顶角 theta
    apex_center = left_line["apex"]
    _draw_angle_arc(ax, apex_center, 48, 24, 90 - THETA_DEG / 2.0, 90 + THETA_DEG / 2.0)
    ax.text(apex_center[0] - 6, 17, labels["apex_angle"], fontsize=13)

    # 左下角入射角
    _draw_angle_arc(ax, point_a, 56, 28, 360 - ALPHA_DEG, 360 - ALPHA_DEG + (180 - THETA_DEG) / 2.0)
    ax.text(point_a[0] + 52, point_a[1] - 5.0, labels["left_bottom_angle"], fontsize=12)

    # 中间右下角入射角
    right_bottom = right_line["left_foot"]
    _draw_angle_arc(
        ax,
        right_bottom,
        50,
        24,
        180 - (180 - THETA_DEG) / 2.0 - ALPHA_DEG,
        180 - ALPHA_DEG,
    )
    ax.text(right_bottom[0] - 18, right_bottom[1] - 9.0, labels["right_bottom_angle"], fontsize=12)

    ax.set_xlim(baseline["left_start"][0] - 25, baseline["right_end"][0] + 35)
    ax.set_ylim(-16, seabed_y.max() + 16)
    ax.invert_yaxis()
    ax.axis("off")
    fig.tight_layout()
    return fig, ax


def plot_section_diagram(result_df, output_path):
    """保存第一问截面示意图。"""
    fig, _ = create_section_figure(result_df)
    fig.savefig(output_path, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def plot_depth_curve(result_df, output_path):
    """绘制水深随测线位置变化图。"""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(result_df["distance_m"], result_df["depth_m"], marker="o", color="#4c78a8")
    ax.set_xlabel("测线距中心点处的距离 / m")
    ax.set_ylabel("海水深度 / m")
    ax.invert_yaxis()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_width_overlap_curve(result_df, output_path):
    """绘制覆盖宽度和重叠率变化图。"""
    configure_matplotlib()
    fig, axes = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

    axes[0].plot(result_df["distance_m"], result_df["width_m"], marker="o", color="#f58518")
    axes[0].set_ylabel("覆盖宽度 W / m")
    axes[0].grid(alpha=0.25)

    valid_df = result_df.dropna(subset=["overlap_rate_pct"])
    axes[1].plot(valid_df["distance_m"], valid_df["overlap_rate_pct"], marker="o", color="#54a24b")
    axes[1].set_xlabel("测线距中心点处的距离 / m")
    axes[1].set_ylabel("重叠率 η / %")
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def run_question1():
    """执行第一问并输出结果文件。"""
    ensure_directory(TABLE_OUTPUT_DIR)
    ensure_directory(FIGURE_OUTPUT_DIR)

    result_df = calculate_question1_results()
    table_df = build_result_table(result_df)

    save_result1_excel(TEMPLATE_RESULT1, TABLE_OUTPUT_DIR / RESULT1_XLSX_NAME, result_df)
    save_table_csv(table_df, TABLE_OUTPUT_DIR / RESULT1_TABLE_NAME)

    plot_section_diagram(result_df, FIGURE_OUTPUT_DIR / SECTION_FIGURE_NAME)
    plot_depth_curve(result_df, FIGURE_OUTPUT_DIR / DEPTH_FIGURE_NAME)
    plot_width_overlap_curve(result_df, FIGURE_OUTPUT_DIR / WIDTH_OVERLAP_FIGURE_NAME)

    return result_df, table_df


if __name__ == "__main__":
    run_question1()
