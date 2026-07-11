import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Arc
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from config import (
    ALPHA_DEG,
    FIGURE_OUTPUT_DIR,
    NAUTICAL_MILE_M,
    QUESTION3_BETA_LENGTH_NAME,
    QUESTION3_BETA_SCAN_DEG,
    QUESTION3_CENTER_DEPTH_M,
    QUESTION3_DISTRIBUTION_NAME,
    QUESTION3_EAST_BOUNDARY_NM,
    QUESTION3_LINE_PLAN_NAME,
    QUESTION3_NORTH_BOUNDARY_NM,
    QUESTION3_OPTIMAL_BETA_RAD,
    QUESTION3_OVERLAP_MAX,
    QUESTION3_OVERLAP_MIN,
    QUESTION3_OVERLAP_NAME,
    QUESTION3_REGION_EW_NM,
    QUESTION3_REGION_NS_NM,
    QUESTION3_SCENE_3D_NAME,
    QUESTION3_SECTION_NAME,
    QUESTION3_SOUTH_BOUNDARY_NM,
    QUESTION3_SUMMARY_NAME,
    QUESTION3_WEST_BOUNDARY_NM,
    TABLE_OUTPUT_DIR,
    THETA_DEG,
)
from utils import configure_matplotlib, ensure_directory, format_number, save_table_csv


def calculate_effective_angles(beta_rad):
    """计算第二问中的等效角 a、b。"""
    alpha_rad = math.radians(ALPHA_DEG)
    a_rad = math.atan(-math.tan(alpha_rad) * math.cos(beta_rad))
    b_rad = math.atan(math.tan(alpha_rad) * math.sin(beta_rad))
    return a_rad, b_rad


def calculate_seabed_depth(x_nm):
    """计算第三问海域中指定东西坐标处的水深。"""
    alpha_rad = math.radians(ALPHA_DEG)
    return QUESTION3_CENTER_DEPTH_M - x_nm * NAUTICAL_MILE_M * math.tan(alpha_rad)


def calculate_projected_half_widths(depth_m, b_rad):
    """计算测线垂直方向上深水侧和浅水侧的水平投影半宽。"""
    slope_rad = abs(b_rad)
    half_open_rad = math.radians(THETA_DEG) / 2.0

    deep_side_m = depth_m * math.sin(half_open_rad) / math.cos(half_open_rad + slope_rad) * math.cos(slope_rad)
    shallow_side_m = depth_m * math.sin(half_open_rad) / math.cos(half_open_rad - slope_rad) * math.cos(slope_rad)

    return deep_side_m / NAUTICAL_MILE_M, shallow_side_m / NAUTICAL_MILE_M


def _solve_first_line_x(b_rad):
    """求解最东侧首条测线位置。"""
    left = QUESTION3_WEST_BOUNDARY_NM
    right = QUESTION3_EAST_BOUNDARY_NM

    def func(x_nm):
        depth_m = calculate_seabed_depth(x_nm)
        _, shallow_half_nm = calculate_projected_half_widths(depth_m, b_rad)
        return x_nm + shallow_half_nm - QUESTION3_EAST_BOUNDARY_NM

    for _ in range(80):
        mid = (left + right) / 2.0
        if func(mid) > 0:
            right = mid
        else:
            left = mid
    return (left + right) / 2.0


def _solve_next_line_x(current_x_nm, b_rad, overlap_rate):
    """根据当前测线位置求解下一条更深测线的位置。"""
    current_depth_m = calculate_seabed_depth(current_x_nm)
    deep_half_nm, _ = calculate_projected_half_widths(current_depth_m, b_rad)

    def func(next_x_nm):
        next_depth_m = calculate_seabed_depth(next_x_nm)
        _, shallow_half_nm = calculate_projected_half_widths(next_depth_m, b_rad)
        spacing_nm = current_x_nm - next_x_nm
        return spacing_nm - (1.0 - overlap_rate) * (deep_half_nm + shallow_half_nm)

    right = current_x_nm - 1e-6
    left = QUESTION3_WEST_BOUNDARY_NM - 1.0
    while func(left) < 0:
        left -= 0.5

    for _ in range(100):
        mid = (left + right) / 2.0
        if func(mid) > 0:
            left = mid
        else:
            right = mid
    return (left + right) / 2.0


def _build_line_df_from_positions(x_positions_nm, b_rad):
    """由测线位置构造结果表。"""
    rows = []
    for index, x_nm in enumerate(x_positions_nm, start=1):
        depth_m = calculate_seabed_depth(x_nm)
        deep_half_nm, shallow_half_nm = calculate_projected_half_widths(depth_m, b_rad)
        rows.append(
            {
                "line_id": index,
                "x_nm": x_nm,
                "depth_m": depth_m,
                "deep_half_nm": deep_half_nm,
                "shallow_half_nm": shallow_half_nm,
                "west_cover_nm": x_nm - deep_half_nm,
                "east_cover_nm": x_nm + shallow_half_nm,
                "south_y_nm": QUESTION3_SOUTH_BOUNDARY_NM,
                "north_y_nm": QUESTION3_NORTH_BOUNDARY_NM,
                "line_length_nm": QUESTION3_REGION_NS_NM,
                "spacing_to_previous_nm": np.nan,
                "overlap_rate_pct": np.nan,
            }
        )

    line_df = pd.DataFrame(rows)
    for i in range(1, len(line_df)):
        spacing_nm = line_df.loc[i - 1, "x_nm"] - line_df.loc[i, "x_nm"]
        width_sum_nm = line_df.loc[i - 1, "deep_half_nm"] + line_df.loc[i, "shallow_half_nm"]
        overlap_rate = 1.0 - spacing_nm / width_sum_nm
        line_df.loc[i, "spacing_to_previous_nm"] = spacing_nm
        line_df.loc[i, "overlap_rate_pct"] = overlap_rate * 100.0

    return line_df


def _generate_line_positions_for_overlap(overlap_rate, line_count=None):
    """在给定重叠率下生成测线位置。"""
    _, b_rad = calculate_effective_angles(QUESTION3_OPTIMAL_BETA_RAD)
    positions = [_solve_first_line_x(b_rad)]

    if line_count is None:
        while True:
            line_df = _build_line_df_from_positions(positions, b_rad)
            if line_df.iloc[-1]["west_cover_nm"] <= QUESTION3_WEST_BOUNDARY_NM:
                return positions, line_df, b_rad
            positions.append(_solve_next_line_x(positions[-1], b_rad, overlap_rate))

    while len(positions) < line_count:
        positions.append(_solve_next_line_x(positions[-1], b_rad, overlap_rate))

    return positions, _build_line_df_from_positions(positions, b_rad), b_rad


def _search_uniform_overlap_for_fixed_count(line_count):
    """在固定测线条数下搜索恰好覆盖西边界的统一重叠率。"""
    low = QUESTION3_OVERLAP_MIN
    high = QUESTION3_OVERLAP_MAX

    _, line_df_low, b_rad = _generate_line_positions_for_overlap(low, line_count)
    residual_low = line_df_low.iloc[-1]["west_cover_nm"] - QUESTION3_WEST_BOUNDARY_NM
    _, line_df_high, _ = _generate_line_positions_for_overlap(high, line_count)
    residual_high = line_df_high.iloc[-1]["west_cover_nm"] - QUESTION3_WEST_BOUNDARY_NM

    if residual_low * residual_high > 0:
        return low, line_df_low, b_rad

    for _ in range(80):
        mid = (low + high) / 2.0
        _, line_df_mid, _ = _generate_line_positions_for_overlap(mid, line_count)
        residual_mid = line_df_mid.iloc[-1]["west_cover_nm"] - QUESTION3_WEST_BOUNDARY_NM
        if residual_mid <= 0:
            low = mid
            line_df_low = line_df_mid
        else:
            high = mid
            line_df_high = line_df_mid

    final_overlap = (low + high) / 2.0
    _, final_df, _ = _generate_line_positions_for_overlap(final_overlap, line_count)
    return final_overlap, final_df, b_rad


def solve_question3():
    """求解第三问最优布线。"""
    beta_rad = QUESTION3_OPTIMAL_BETA_RAD
    overlap_rate = QUESTION3_OVERLAP_MIN
    _, line_df, b_rad = _generate_line_positions_for_overlap(overlap_rate)
    line_count = len(line_df)

    total_length_nm = line_count * QUESTION3_REGION_NS_NM
    overlap_values = line_df["overlap_rate_pct"].dropna()

    return {
        "beta_rad": beta_rad,
        "beta_deg": math.degrees(beta_rad),
        "a_rad": calculate_effective_angles(beta_rad)[0],
        "b_rad": b_rad,
        "uniform_overlap_rate": overlap_rate,
        "line_count": line_count,
        "total_length_nm": total_length_nm,
        "line_df": line_df,
        "min_overlap_pct": float(overlap_values.min()),
        "max_overlap_pct": float(overlap_values.max()),
    }


def _line_segment_in_rectangle(beta_rad, offset_nm=0.0):
    """求解给定方向与偏移的无限直线在矩形内的线段。"""
    t_x = math.cos(beta_rad)
    t_y = math.sin(beta_rad)
    n_x = -math.sin(beta_rad)
    n_y = math.cos(beta_rad)
    x0 = offset_nm * n_x
    y0 = offset_nm * n_y

    s_low = -1e9
    s_high = 1e9

    for p0, direction, lower, upper in [
        (x0, t_x, QUESTION3_WEST_BOUNDARY_NM, QUESTION3_EAST_BOUNDARY_NM),
        (y0, t_y, QUESTION3_SOUTH_BOUNDARY_NM, QUESTION3_NORTH_BOUNDARY_NM),
    ]:
        if abs(direction) < 1e-12:
            if p0 < lower or p0 > upper:
                return None
            continue
        s1 = (lower - p0) / direction
        s2 = (upper - p0) / direction
        s_low = max(s_low, min(s1, s2))
        s_high = min(s_high, max(s1, s2))

    if s_low > s_high:
        return None

    start = (x0 + s_low * t_x, y0 + s_low * t_y)
    end = (x0 + s_high * t_x, y0 + s_high * t_y)
    length_nm = s_high - s_low
    return start, end, length_nm


def _projection_span_on_normal(beta_rad):
    """计算矩形海域在法向上的投影宽度。"""
    n_x = -math.sin(beta_rad)
    n_y = math.cos(beta_rad)
    corners = [
        (QUESTION3_WEST_BOUNDARY_NM, QUESTION3_SOUTH_BOUNDARY_NM),
        (QUESTION3_WEST_BOUNDARY_NM, QUESTION3_NORTH_BOUNDARY_NM),
        (QUESTION3_EAST_BOUNDARY_NM, QUESTION3_SOUTH_BOUNDARY_NM),
        (QUESTION3_EAST_BOUNDARY_NM, QUESTION3_NORTH_BOUNDARY_NM),
    ]
    projections = [x * n_x + y * n_y for x, y in corners]
    return max(projections) - min(projections)


def build_beta_scan_dataframe():
    """构造不同 beta 下总测线长度变化表。"""
    rows = []
    for beta_deg in QUESTION3_BETA_SCAN_DEG:
        beta_rad = math.radians(beta_deg)
        _, b_rad = calculate_effective_angles(beta_rad)
        segment = _line_segment_in_rectangle(beta_rad, 0.0)
        if segment is None:
            continue
        (x1, _), (x2, _), center_length_nm = segment
        shallowest_x_nm = max(x1, x2)
        shallowest_depth_m = max(5.0, calculate_seabed_depth(shallowest_x_nm))

        deep_half_nm, shallow_half_nm = calculate_projected_half_widths(shallowest_depth_m, b_rad)
        spacing_nm = (1.0 - QUESTION3_OVERLAP_MIN) * (deep_half_nm + shallow_half_nm)
        span_nm = _projection_span_on_normal(beta_rad)
        line_count = max(1, int(math.ceil(span_nm / max(spacing_nm, 1e-6))))
        total_length_nm = line_count * center_length_nm

        rows.append(
            {
                "beta_deg": beta_deg,
                "beta_rad": beta_rad,
                "center_line_length_nm": center_length_nm,
                "normal_span_nm": span_nm,
                "spacing_nm": spacing_nm,
                "line_count": line_count,
                "total_length_nm": total_length_nm,
            }
        )

    return pd.DataFrame(rows)


def build_summary_table(result):
    """生成第三问汇总表。"""
    summary_rows = [
        ["最优方向/度", format_number(result["beta_deg"])],
        ["最优方向/弧度", format_number(result["beta_rad"], digits=4)],
        ["统一重叠率/%", format_number(result["uniform_overlap_rate"] * 100.0)],
        ["测线条数", str(int(result["line_count"]))],
        ["总测线长度/海里", format_number(result["total_length_nm"])],
        ["最小重叠率/%", format_number(result["min_overlap_pct"])],
        ["最大重叠率/%", format_number(result["max_overlap_pct"])],
    ]
    return pd.DataFrame(summary_rows, columns=["指标", "结果"])


def build_line_plan_table(line_df):
    """生成第三问测线布置表。"""
    plan_df = pd.DataFrame(
        {
            "测线编号": line_df["line_id"].astype(int),
            "测线位置x/海里": [format_number(v, 4) for v in line_df["x_nm"]],
            "所在水深/米": [format_number(v) for v in line_df["depth_m"]],
            "深水侧覆盖半宽/海里": [format_number(v, 4) for v in line_df["deep_half_nm"]],
            "浅水侧覆盖半宽/海里": [format_number(v, 4) for v in line_df["shallow_half_nm"]],
            "与前一条间距/海里": [""] + [format_number(v, 4) for v in line_df["spacing_to_previous_nm"].iloc[1:]],
            "与前一条重叠率/%": [""] + [format_number(v) for v in line_df["overlap_rate_pct"].iloc[1:]],
        }
    )
    return plan_df


def plot_scene_3d(output_path):
    """绘制第三问三维场景示意图。"""
    configure_matplotlib()
    fig = plt.figure(figsize=(8.5, 6.2))
    ax = fig.add_subplot(111, projection="3d")

    x_vals = np.linspace(QUESTION3_WEST_BOUNDARY_NM, QUESTION3_EAST_BOUNDARY_NM, 30)
    y_vals = np.linspace(QUESTION3_SOUTH_BOUNDARY_NM, QUESTION3_NORTH_BOUNDARY_NM, 20)
    xx, yy = np.meshgrid(x_vals, y_vals)
    zz = -(
        QUESTION3_CENTER_DEPTH_M
        - xx * NAUTICAL_MILE_M * math.tan(math.radians(ALPHA_DEG))
    )

    ax.plot_surface(xx, yy, zz, cmap="Blues", alpha=0.85, linewidth=0)
    ax.quiver(
        0.0,
        0.0,
        -QUESTION3_CENTER_DEPTH_M + 3.0,
        0.0,
        0.85,
        0.0,
        color="#d62728",
        linewidth=2.0,
        arrow_length_ratio=0.12,
    )
    ax.text(0.08, 0.88, -QUESTION3_CENTER_DEPTH_M + 4.0, r"最优方向 $\beta=\pi/2$", color="#d62728", fontsize=12)

    ax.set_xlabel("东西方向 / 海里")
    ax.set_ylabel("南北方向 / 海里")
    ax.set_zlabel("高程 / 米")
    ax.view_init(elev=24, azim=-58)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_section_beta_90(line_df, output_path):
    """绘制 beta=pi/2 时的二维几何示意图。"""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    sample_df = line_df.iloc[:2].copy()
    spacing_ratio = sample_df.iloc[0]["x_nm"] - sample_df.iloc[1]["x_nm"]
    spacing_ratio = max(spacing_ratio / 0.05, 0.75)
    left_apex_x = 0.40
    right_apex_x = left_apex_x - 0.10 * spacing_ratio

    slope_x = np.linspace(0.08, 0.92, 200)
    slope_y = 0.72 - 0.32 * (slope_x - 0.08)
    ax.plot(slope_x, slope_y, color="#666666", linewidth=2.2)

    line_specs = [
        {"apex": (left_apex_x, 0.26), "color": "#4c78a8", "label": r"$D_1$"},
        {"apex": (right_apex_x, 0.26), "color": "#f58518", "label": r"$D_2$"},
    ]

    for spec in line_specs:
        apex_x, apex_y = spec["apex"]
        center_y = 0.72 - 0.32 * (apex_x - 0.08)
        left_foot = (apex_x - 0.03, center_y + 0.02)
        right_foot = (apex_x + 0.03, center_y - 0.02)
        ax.plot([apex_x, left_foot[0]], [apex_y, left_foot[1]], color=spec["color"], linewidth=2.0)
        ax.plot([apex_x, right_foot[0]], [apex_y, right_foot[1]], color=spec["color"], linewidth=2.0)
        ax.plot([apex_x, apex_x], [apex_y, center_y], linestyle="--", color=spec["color"], linewidth=1.6)
        ax.text(apex_x + 0.02, (apex_y + center_y) / 2, spec["label"], color=spec["color"], fontsize=12)

    ax.annotate(
        "",
        xy=(right_apex_x, 0.14),
        xytext=(left_apex_x, 0.14),
        arrowprops={"arrowstyle": "<->", "linewidth": 1.2, "color": "#555555"},
    )
    ax.text((left_apex_x + right_apex_x) / 2, 0.10, r"$d$", fontsize=13, ha="center")

    alpha_arc = Arc((0.18, 0.69), width=0.12, height=0.08, angle=0, theta1=0, theta2=ALPHA_DEG, linewidth=1.2)
    theta_arc = Arc((left_apex_x, 0.26), width=0.10, height=0.08, angle=0, theta1=90 - THETA_DEG / 2, theta2=90 + THETA_DEG / 2, linewidth=1.2)
    ax.add_patch(alpha_arc)
    ax.add_patch(theta_arc)
    ax.text(0.23, 0.66, r"$\alpha$", fontsize=12)
    ax.text(left_apex_x - 0.01, 0.34, r"$\theta$", fontsize=12)

    ax.set_xlim(0.05, 0.95)
    ax.set_ylim(0.92, 0.02)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def plot_line_distribution(line_df, output_path):
    """绘制测线在垂直方向上的分布曲线。"""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.plot(line_df["line_id"], line_df["x_nm"], marker="o", color="#4c78a8")
    ax.set_xlabel("测线编号")
    ax.set_ylabel("测线位置 x / 海里")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_overlap_curve(line_df, output_path):
    """绘制相邻测线重叠率曲线。"""
    configure_matplotlib()
    valid_df = line_df.dropna(subset=["overlap_rate_pct"])
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.plot(valid_df["line_id"], valid_df["overlap_rate_pct"], marker="o", color="#54a24b")
    ax.axhline(10.0, color="#999999", linestyle="--", linewidth=1.0)
    ax.axhline(20.0, color="#999999", linestyle="--", linewidth=1.0)
    ax.set_xlabel("测线编号")
    ax.set_ylabel("重叠率 / %")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_beta_length_curve(beta_df, output_path):
    """绘制不同 beta 下总测线长度变化图。"""
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.plot(beta_df["beta_deg"], beta_df["total_length_nm"], color="#f58518")
    ax.axvline(90.0, color="#999999", linestyle="--", linewidth=1.0)
    ax.set_xlabel(r"$\beta$ / 度")
    ax.set_ylabel("总测线长度 / 海里")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def run_question3():
    """执行第三问并输出结果。"""
    ensure_directory(TABLE_OUTPUT_DIR)
    ensure_directory(FIGURE_OUTPUT_DIR)

    result = solve_question3()
    beta_df = build_beta_scan_dataframe()
    summary_df = build_summary_table(result)
    plan_df = build_line_plan_table(result["line_df"])

    save_table_csv(summary_df, TABLE_OUTPUT_DIR / QUESTION3_SUMMARY_NAME)
    save_table_csv(plan_df, TABLE_OUTPUT_DIR / QUESTION3_LINE_PLAN_NAME)

    plot_scene_3d(FIGURE_OUTPUT_DIR / QUESTION3_SCENE_3D_NAME)
    plot_section_beta_90(result["line_df"], FIGURE_OUTPUT_DIR / QUESTION3_SECTION_NAME)
    plot_line_distribution(result["line_df"], FIGURE_OUTPUT_DIR / QUESTION3_DISTRIBUTION_NAME)
    plot_overlap_curve(result["line_df"], FIGURE_OUTPUT_DIR / QUESTION3_OVERLAP_NAME)
    plot_beta_length_curve(beta_df, FIGURE_OUTPUT_DIR / QUESTION3_BETA_LENGTH_NAME)

    return result, summary_df, plan_df, beta_df


if __name__ == "__main__":
    run_question3()
