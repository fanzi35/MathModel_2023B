"""
文件名：question4.py
用于存放问题四主代码
"""
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import (
    FIGURE_OUTPUT_DIR,
    NAUTICAL_MILE_M,
    QUESTION4_CONTOUR_NAME,
    QUESTION4_LINE_SAMPLE_COUNT,
    QUESTION4_MAX_GAP_FIX_ITER,
    QUESTION4_MAX_ORIENTATION_STD_DEG,
    QUESTION4_MAX_PLANE_RMSE_M,
    QUESTION4_MIN_REGION_COLS,
    QUESTION4_MIN_REGION_ROWS,
    QUESTION4_RAW_DATA_PATH,
    QUESTION4_REGION_SUMMARY_NAME,
    QUESTION4_REGION_PREFIX,
    QUESTION4_REGIONS_OVERVIEW_NAME,
    QUESTION4_OVERALL_SUMMARY_NAME,
    QUESTION4_TARGET_OVERLAP,
    TABLE_OUTPUT_DIR,
    THETA_DEG,
)
from utils import configure_matplotlib, ensure_directory, format_number, read_numeric_excel_sheet, save_table_csv


def load_question4_grid():
    """读取第四问原始网格数据。"""
    raw_df = read_numeric_excel_sheet(QUESTION4_RAW_DATA_PATH)
    x_nm = raw_df.iloc[1, 2:].astype(float).to_numpy()
    y_nm = raw_df.iloc[2:, 1].astype(float).to_numpy()
    depth_m = raw_df.iloc[2:, 2:].astype(float).to_numpy()
    return x_nm, y_nm, depth_m


def compute_orientation_field(x_nm, y_nm, depth_m):
    """计算坡向角场。"""
    dx = float(x_nm[1] - x_nm[0])
    dy = float(y_nm[1] - y_nm[0])
    grad_y, grad_x = np.gradient(depth_m, dy, dx)
    orientation_rad = np.mod(np.arctan2(grad_y, grad_x), np.pi)
    return grad_x, grad_y, orientation_rad


def _orientation_std_deg(angles_rad):
    """计算模 pi 意义下的方向离散度。"""
    values = angles_rad[np.isfinite(angles_rad)]
    if values.size == 0:
        return 90.0
    doubled = 2.0 * values
    mean_cos = np.mean(np.cos(doubled))
    mean_sin = np.mean(np.sin(doubled))
    resultant = np.hypot(mean_cos, mean_sin)
    if resultant < 1e-12:
        return 90.0
    return math.degrees(0.5 * math.sqrt(max(-2.0 * math.log(resultant), 0.0)))


def fit_plane_to_region(x_nm, y_nm, depth_m, row_start, row_end, col_start, col_end):
    """对子区域做局部平面拟合。"""
    x_sub = x_nm[col_start:col_end]
    y_sub = y_nm[row_start:row_end]
    z_sub = depth_m[row_start:row_end, col_start:col_end]
    xx, yy = np.meshgrid(x_sub, y_sub)
    a = np.column_stack([np.ones(xx.size), xx.ravel(), yy.ravel()])
    beta0, beta1, beta2 = np.linalg.lstsq(a, z_sub.ravel(), rcond=None)[0]
    pred = (a @ np.array([beta0, beta1, beta2])).reshape(z_sub.shape)
    rmse = float(np.sqrt(np.mean((pred - z_sub) ** 2)))

    gradient_nm = np.array([beta1, beta2], dtype=float)
    gradient_norm_nm = float(np.hypot(beta1, beta2))
    if gradient_norm_nm < 1e-12:
        deep_unit = np.array([1.0, 0.0])
    else:
        deep_unit = gradient_nm / gradient_norm_nm
    line_unit = np.array([-deep_unit[1], deep_unit[0]])

    slope_m_per_m = gradient_norm_nm / NAUTICAL_MILE_M
    alpha_rad = math.atan(slope_m_per_m)

    return {
        "beta0": float(beta0),
        "beta1": float(beta1),
        "beta2": float(beta2),
        "rmse_m": rmse,
        "alpha_rad": alpha_rad,
        "deep_unit": deep_unit,
        "line_unit": line_unit,
    }


def _region_summary(x_nm, y_nm, depth_m, orientation_rad, row_start, row_end, col_start, col_end):
    """汇总单个候选区域的拟合信息。"""
    plane = fit_plane_to_region(x_nm, y_nm, depth_m, row_start, row_end, col_start, col_end)
    angle_std_deg = _orientation_std_deg(orientation_rad[row_start:row_end, col_start:col_end])
    return {
        "row_start": row_start,
        "row_end": row_end,
        "col_start": col_start,
        "col_end": col_end,
        "row_count": row_end - row_start,
        "col_count": col_end - col_start,
        "orientation_std_deg": angle_std_deg,
        **plane,
    }


def _split_score(region_a, region_b):
    """对子区域划分质量打分，分数越小越好。"""
    size_a = region_a["row_count"] * region_a["col_count"]
    size_b = region_b["row_count"] * region_b["col_count"]
    size_total = size_a + size_b
    score_a = region_a["orientation_std_deg"] + 2.0 * region_a["rmse_m"]
    score_b = region_b["orientation_std_deg"] + 2.0 * region_b["rmse_m"]
    return (score_a * size_a + score_b * size_b) / size_total


def partition_question4_regions(x_nm, y_nm, depth_m):
    """按等深线近似平行的原则自适应分区。"""
    _, _, orientation_rad = compute_orientation_field(x_nm, y_nm, depth_m)
    regions = []

    def recurse(row_start, row_end, col_start, col_end):
        region = _region_summary(x_nm, y_nm, depth_m, orientation_rad, row_start, row_end, col_start, col_end)

        can_split_row = region["row_count"] >= 2 * QUESTION4_MIN_REGION_ROWS
        can_split_col = region["col_count"] >= 2 * QUESTION4_MIN_REGION_COLS
        good_enough = (
            region["orientation_std_deg"] <= QUESTION4_MAX_ORIENTATION_STD_DEG
            and region["rmse_m"] <= QUESTION4_MAX_PLANE_RMSE_M
        )

        if good_enough or (not can_split_row and not can_split_col):
            regions.append(region)
            return

        candidates = []
        if can_split_row:
            row_mid = (row_start + row_end) // 2
            top_region = _region_summary(x_nm, y_nm, depth_m, orientation_rad, row_start, row_mid, col_start, col_end)
            bottom_region = _region_summary(x_nm, y_nm, depth_m, orientation_rad, row_mid, row_end, col_start, col_end)
            candidates.append(("row", row_mid, _split_score(top_region, bottom_region)))
        if can_split_col:
            col_mid = (col_start + col_end) // 2
            left_region = _region_summary(x_nm, y_nm, depth_m, orientation_rad, row_start, row_end, col_start, col_mid)
            right_region = _region_summary(x_nm, y_nm, depth_m, orientation_rad, row_start, row_end, col_mid, col_end)
            candidates.append(("col", col_mid, _split_score(left_region, right_region)))

        if not candidates:
            regions.append(region)
            return

        split_axis, split_index, _ = min(candidates, key=lambda item: item[2])
        if split_axis == "row":
            recurse(row_start, split_index, col_start, col_end)
            recurse(split_index, row_end, col_start, col_end)
        else:
            recurse(row_start, row_end, col_start, split_index)
            recurse(row_start, row_end, split_index, col_end)

    recurse(0, len(y_nm), 0, len(x_nm))
    for idx, region in enumerate(regions, start=1):
        region["id"] = idx
        region["x_center_nm"] = float(np.mean(x_nm[region["col_start"]:region["col_end"]]))
        region["y_center_nm"] = float(np.mean(y_nm[region["row_start"]:region["row_end"]]))
    return regions


def _plane_depth_at_u(region, u_value):
    """计算局部平面在指定法向坐标处的深度。"""
    x_center = region["x_center_nm"]
    y_center = region["y_center_nm"]
    u_center = x_center * region["deep_unit"][0] + y_center * region["deep_unit"][1]
    depth_center = region["beta0"] + region["beta1"] * x_center + region["beta2"] * y_center
    gradient_norm_nm = math.hypot(region["beta1"], region["beta2"])
    return depth_center + gradient_norm_nm * (u_value - u_center)


def _projected_half_widths_nm(depth_m, alpha_rad):
    """计算沿坡向两侧的水平投影半宽。"""
    half_open = math.radians(THETA_DEG) / 2.0
    deep_half_m = depth_m * math.sin(half_open) / math.cos(half_open + alpha_rad) * math.cos(alpha_rad)
    shallow_half_m = depth_m * math.sin(half_open) / math.cos(half_open - alpha_rad) * math.cos(alpha_rad)
    return deep_half_m / NAUTICAL_MILE_M, shallow_half_m / NAUTICAL_MILE_M


def _region_u_bounds(region, x_nm, y_nm):
    """计算区域在局部法向坐标下的范围。"""
    x0 = x_nm[region["col_start"]]
    x1 = x_nm[region["col_end"] - 1]
    y0 = y_nm[region["row_start"]]
    y1 = y_nm[region["row_end"] - 1]
    corners = np.array([[x0, y0], [x0, y1], [x1, y0], [x1, y1]])
    projections = corners @ region["deep_unit"]
    return float(np.min(projections)), float(np.max(projections))


def _line_segment_in_region(region, u_value, x_nm, y_nm):
    """求局部测线在子区域矩形边界内的线段。"""
    x0 = x_nm[region["col_start"]]
    x1 = x_nm[region["col_end"] - 1]
    y0 = y_nm[region["row_start"]]
    y1 = y_nm[region["row_end"] - 1]

    center = np.array([region["x_center_nm"], region["y_center_nm"]], dtype=float)
    u_center = float(center @ region["deep_unit"])
    point = center + (u_value - u_center) * region["deep_unit"]
    direction = region["line_unit"]

    low = -1e9
    high = 1e9
    for p0, direct, lower, upper in [
        (point[0], direction[0], x0, x1),
        (point[1], direction[1], y0, y1),
    ]:
        if abs(direct) < 1e-12:
            if p0 < lower or p0 > upper:
                return None
            continue
        s1 = (lower - p0) / direct
        s2 = (upper - p0) / direct
        low = max(low, min(s1, s2))
        high = min(high, max(s1, s2))

    if low > high:
        return None

    start = point + low * direction
    end = point + high * direction
    return start, end


def _bilinear_interpolate(x_nm, y_nm, depth_m, x_query, y_query):
    """双线性插值计算深度。"""
    x_query = float(np.clip(x_query, x_nm[0], x_nm[-1]))
    y_query = float(np.clip(y_query, y_nm[0], y_nm[-1]))
    i = int(np.clip(np.searchsorted(x_nm, x_query) - 1, 0, len(x_nm) - 2))
    j = int(np.clip(np.searchsorted(y_nm, y_query) - 1, 0, len(y_nm) - 2))

    x0, x1 = x_nm[i], x_nm[i + 1]
    y0, y1 = y_nm[j], y_nm[j + 1]
    q11 = depth_m[j, i]
    q21 = depth_m[j, i + 1]
    q12 = depth_m[j + 1, i]
    q22 = depth_m[j + 1, i + 1]

    tx = 0.0 if x1 == x0 else (x_query - x0) / (x1 - x0)
    ty = 0.0 if y1 == y0 else (y_query - y0) / (y1 - y0)
    return (
        q11 * (1 - tx) * (1 - ty)
        + q21 * tx * (1 - ty)
        + q12 * (1 - tx) * ty
        + q22 * tx * ty
    )


def _conservative_depth_for_line(region, u_value, x_nm, y_nm, depth_m):
    """取测线在线段上的最小深度，作为保守覆盖宽度依据。"""
    segment = _line_segment_in_region(region, u_value, x_nm, y_nm)
    if segment is None:
        return float(_plane_depth_at_u(region, u_value))
    start, end = segment
    sample_values = []
    for ratio in np.linspace(0.0, 1.0, QUESTION4_LINE_SAMPLE_COUNT):
        point = start + ratio * (end - start)
        sample_values.append(_bilinear_interpolate(x_nm, y_nm, depth_m, point[0], point[1]))
    return float(np.min(sample_values))


def _generate_region_lines(region, x_nm, y_nm, depth_m):
    """按局部平面近似生成区域测线，并用保守深度修正。"""
    u_min, u_max = _region_u_bounds(region, x_nm, y_nm)
    alpha_rad = region["alpha_rad"]

    def solve_first_u():
        left = u_min
        right = u_max
        for _ in range(60):
            mid = (left + right) / 2.0
            depth_mid = _plane_depth_at_u(region, mid)
            _, shallow_half = _projected_half_widths_nm(depth_mid, alpha_rad)
            if mid - shallow_half > u_min:
                right = mid
            else:
                left = mid
        return (left + right) / 2.0

    def solve_next_u(current_u):
        current_depth = _plane_depth_at_u(region, current_u)
        deep_half, _ = _projected_half_widths_nm(current_depth, alpha_rad)
        left = current_u
        right = u_max + 1.0
        for _ in range(80):
            mid = (left + right) / 2.0
            next_depth = _plane_depth_at_u(region, mid)
            _, shallow_half = _projected_half_widths_nm(next_depth, alpha_rad)
            spacing = mid - current_u
            residual = spacing - (1.0 - QUESTION4_TARGET_OVERLAP) * (deep_half + shallow_half)
            if residual > 0:
                right = mid
            else:
                left = mid
        return (left + right) / 2.0

    u_positions = [solve_first_u()]
    while True:
        conservative_depth = _conservative_depth_for_line(region, u_positions[-1], x_nm, y_nm, depth_m)
        deep_half, _ = _projected_half_widths_nm(conservative_depth, alpha_rad)
        if u_positions[-1] + deep_half >= u_max:
            break
        u_positions.append(solve_next_u(u_positions[-1]))

    for _ in range(QUESTION4_MAX_GAP_FIX_ITER):
        coverage_mask, _, line_records = _evaluate_region_coverage(region, x_nm, y_nm, depth_m, u_positions)
        if bool(np.all(coverage_mask)):
            return u_positions, line_records, coverage_mask
        u_grid = _region_grid_projection(region, x_nm, y_nm)
        uncovered_u = u_grid[~coverage_mask]
        if uncovered_u.size == 0:
            return u_positions, line_records, coverage_mask
        u_positions.append(float(np.min(uncovered_u)))
        u_positions = sorted(u_positions)

    coverage_mask, _, line_records = _evaluate_region_coverage(region, x_nm, y_nm, depth_m, u_positions)
    return u_positions, line_records, coverage_mask


def _region_grid_projection(region, x_nm, y_nm):
    """计算区域内每个网格点在局部法向上的投影。"""
    x_sub = x_nm[region["col_start"]:region["col_end"]]
    y_sub = y_nm[region["row_start"]:region["row_end"]]
    xx, yy = np.meshgrid(x_sub, y_sub)
    return xx * region["deep_unit"][0] + yy * region["deep_unit"][1]


def _evaluate_region_coverage(region, x_nm, y_nm, depth_m, u_positions):
    """计算区域覆盖结果与相邻重叠率。"""
    alpha_rad = region["alpha_rad"]
    u_grid = _region_grid_projection(region, x_nm, y_nm)
    cover_count = np.zeros_like(u_grid, dtype=int)
    line_records = []

    for idx, u_value in enumerate(u_positions, start=1):
        depth_value = _conservative_depth_for_line(region, u_value, x_nm, y_nm, depth_m)
        deep_half, shallow_half = _projected_half_widths_nm(depth_value, alpha_rad)
        segment = _line_segment_in_region(region, u_value, x_nm, y_nm)
        line_length_nm = 0.0 if segment is None else float(np.linalg.norm(segment[1] - segment[0]))
        lower = u_value - shallow_half
        upper = u_value + deep_half
        mask = (u_grid >= lower) & (u_grid <= upper)
        cover_count += mask.astype(int)
        line_records.append(
            {
                "line_id": idx,
                "u_nm": u_value,
                "depth_m": depth_value,
                "shallow_half_nm": shallow_half,
                "deep_half_nm": deep_half,
                "line_length_nm": line_length_nm,
            }
        )

    line_df = pd.DataFrame(line_records)
    if len(line_df) > 1:
        overlaps = [np.nan]
        for idx in range(1, len(line_df)):
            spacing = line_df.loc[idx, "u_nm"] - line_df.loc[idx - 1, "u_nm"]
            width_sum = line_df.loc[idx - 1, "deep_half_nm"] + line_df.loc[idx, "shallow_half_nm"]
            overlaps.append((1.0 - spacing / width_sum) * 100.0)
        line_df["overlap_rate_pct"] = overlaps
    else:
        line_df["overlap_rate_pct"] = np.nan

    return cover_count > 0, cover_count, line_df


def solve_question4():
    """求解第四问的分区与局部布线方案。"""
    x_nm, y_nm, depth_m = load_question4_grid()
    regions = partition_question4_regions(x_nm, y_nm, depth_m)

    region_solutions = []
    total_line_count = 0
    uncovered_total = 0
    over20_line_pairs = 0
    total_line_length_nm = 0.0
    over20_line_length_nm = 0.0
    region_metrics = []

    for region in regions:
        u_positions, line_df, coverage_mask = _generate_region_lines(region, x_nm, y_nm, depth_m)
        uncovered_count = int((~coverage_mask).sum())
        uncovered_total += uncovered_count
        total_line_count += len(line_df)
        over20_line_pairs += int((line_df["overlap_rate_pct"].fillna(0) > 20.0).sum())
        region_total_length_nm = float(line_df["line_length_nm"].sum())
        region_over20_length_nm = float(line_df.loc[line_df["overlap_rate_pct"] > 20.0, "line_length_nm"].sum())
        total_line_length_nm += region_total_length_nm
        over20_line_length_nm += region_over20_length_nm
        valid_overlap = line_df["overlap_rate_pct"].dropna()
        region_metrics.append(
            {
                "region_id": region["id"],
                "region_line_count": int(len(line_df)),
                "region_total_length_nm": region_total_length_nm,
                "region_min_overlap_pct": float(valid_overlap.min()) if not valid_overlap.empty else np.nan,
                "region_mean_overlap_pct": float(valid_overlap.mean()) if not valid_overlap.empty else np.nan,
                "region_max_overlap_pct": float(valid_overlap.max()) if not valid_overlap.empty else np.nan,
                "region_over20_length_nm": region_over20_length_nm,
                "region_uncovered_cell_count": uncovered_count,
            }
        )
        region_solutions.append(
            {
                **region,
                "u_positions": u_positions,
                "line_df": line_df,
                "coverage_mask": coverage_mask,
                "uncovered_cell_count": uncovered_count,
            }
        )

    region_metrics_df = pd.DataFrame(region_metrics)
    return {
        "x_nm": x_nm,
        "y_nm": y_nm,
        "depth_m": depth_m,
        "regions": region_solutions,
        "region_count": len(region_solutions),
        "line_count": total_line_count,
        "total_line_length_nm": total_line_length_nm,
        "uncovered_cell_count": uncovered_total,
        "over20_line_pair_count": over20_line_pairs,
        "over20_line_length_nm": over20_line_length_nm,
        "region_metrics_df": region_metrics_df,
    }


def build_question4_region_summary_table(result):
    """生成第四问分区汇总表。"""
    df = result["region_metrics_df"].copy()
    return pd.DataFrame(
        {
            "分区编号": df["region_id"].astype(int),
            "测线条数": df["region_line_count"].astype(int),
            "测线总长/海里": [format_number(v, 4) for v in df["region_total_length_nm"]],
            "最小重叠率/%": [format_number(v) if pd.notna(v) else "" for v in df["region_min_overlap_pct"]],
            "平均重叠率/%": [format_number(v) if pd.notna(v) else "" for v in df["region_mean_overlap_pct"]],
            "最大重叠率/%": [format_number(v) if pd.notna(v) else "" for v in df["region_max_overlap_pct"]],
            "重叠率超过20%的测线长度/海里": [format_number(v, 4) for v in df["region_over20_length_nm"]],
            "漏测网格数": df["region_uncovered_cell_count"].astype(int),
        }
    )


def build_question4_overall_summary_table(result):
    """生成第四问总体汇总表。"""
    rows = [
        ["总分区数", str(int(result["region_count"]))],
        ["总测线条数", str(int(result["line_count"]))],
        ["总测线总长/海里", format_number(result["total_line_length_nm"], 4)],
        ["重叠率超过20%的测线长度/海里", format_number(result["over20_line_length_nm"], 4)],
        ["漏测网格数", str(int(result["uncovered_cell_count"]))],
    ]
    return pd.DataFrame(rows, columns=["指标", "结果"])


def plot_question4_contours(result, output_path):
    """绘制整体等深线与分区编号图。"""
    configure_matplotlib()
    x_nm = result["x_nm"]
    y_nm = result["y_nm"]
    depth_m = result["depth_m"]
    fig, ax = plt.subplots(figsize=(8.2, 9.0))
    levels = np.linspace(float(np.nanmin(depth_m)), float(np.nanmax(depth_m)), 18)
    contour = ax.contour(x_nm, y_nm, depth_m, levels=levels, colors="black", linewidths=0.9)
    ax.contourf(x_nm, y_nm, depth_m, levels=levels, cmap="viridis", alpha=0.78)
    ax.clabel(contour, inline=True, fontsize=7, fmt="%.1f")

    for region in result["regions"]:
        ax.text(
            region["x_center_nm"],
            region["y_center_nm"],
            str(region["id"]),
            fontsize=9,
            ha="center",
            va="center",
            color="white",
            bbox={"facecolor": "black", "alpha": 0.35, "pad": 0.3, "edgecolor": "none"},
        )

    ax.set_xlabel("东西方向 / 海里")
    ax.set_ylabel("南北方向 / 海里")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def _plot_region_panel(ax, region, x_nm, y_nm, depth_m):
    """绘制单个分区放大图。"""
    x_sub = x_nm[region["col_start"]:region["col_end"]]
    y_sub = y_nm[region["row_start"]:region["row_end"]]
    z_sub = depth_m[region["row_start"]:region["row_end"], region["col_start"]:region["col_end"]]
    levels = np.linspace(float(np.nanmin(z_sub)), float(np.nanmax(z_sub)), 10)
    contour = ax.contour(x_sub, y_sub, z_sub, levels=levels, colors="black", linewidths=0.9)
    ax.contourf(x_sub, y_sub, z_sub, levels=levels, cmap="viridis", alpha=0.78)
    ax.clabel(contour, inline=True, fontsize=6, fmt="%.1f")
    ax.text(
        region["x_center_nm"],
        region["y_center_nm"],
        str(region["id"]),
        fontsize=9,
        ha="center",
        va="center",
        color="white",
        bbox={"facecolor": "black", "alpha": 0.35, "pad": 0.3, "edgecolor": "none"},
    )
    ax.quiver(
        region["x_center_nm"],
        region["y_center_nm"],
        region["line_unit"][0] * 0.25,
        region["line_unit"][1] * 0.25,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="#d62728",
        width=0.004,
    )
    ax.set_xlabel("东西方向 / 海里")
    ax.set_ylabel("南北方向 / 海里")


def plot_question4_regions(result, overview_path):
    """绘制所有分区的放大图，并单独保存每个分区图。"""
    configure_matplotlib()
    x_nm = result["x_nm"]
    y_nm = result["y_nm"]
    depth_m = result["depth_m"]
    regions = result["regions"]

    cols = 3
    rows = int(math.ceil(len(regions) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.2, rows * 3.8))
    axes = np.atleast_1d(axes).ravel()

    for ax, region in zip(axes, regions):
        _plot_region_panel(ax, region, x_nm, y_nm, depth_m)
    for ax in axes[len(regions):]:
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(overview_path, dpi=220)
    plt.close(fig)

    for region in regions:
        fig_single, ax_single = plt.subplots(figsize=(5.0, 4.2))
        _plot_region_panel(ax_single, region, x_nm, y_nm, depth_m)
        fig_single.tight_layout()
        region_path = FIGURE_OUTPUT_DIR / f"{QUESTION4_REGION_PREFIX}{region['id']:02d}.png"
        fig_single.savefig(region_path, dpi=220)
        plt.close(fig_single)


def run_question4():
    """执行第四问并输出图像。"""
    ensure_directory(TABLE_OUTPUT_DIR)
    ensure_directory(FIGURE_OUTPUT_DIR)
    result = solve_question4()
    region_summary_df = build_question4_region_summary_table(result)
    overall_summary_df = build_question4_overall_summary_table(result)
    save_table_csv(region_summary_df, TABLE_OUTPUT_DIR / QUESTION4_REGION_SUMMARY_NAME)
    save_table_csv(overall_summary_df, TABLE_OUTPUT_DIR / QUESTION4_OVERALL_SUMMARY_NAME)
    plot_question4_contours(result, FIGURE_OUTPUT_DIR / QUESTION4_CONTOUR_NAME)
    plot_question4_regions(result, FIGURE_OUTPUT_DIR / QUESTION4_REGIONS_OVERVIEW_NAME)
    return result


if __name__ == "__main__":
    run_question4()
