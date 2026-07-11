import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import (
    ALPHA_DEG,
    FIGURE_OUTPUT_DIR,
    NAUTICAL_MILE_M,
    QUESTION2_CENTER_DEPTH,
    QUESTION2_DIRECTIONS_DEG,
    QUESTION2_DISTANCES_NM,
    QUESTION2_WIDTH_CURVE_NAME,
    QUESTION2_WIDTH_HEATMAP_NAME,
    RESULT2_TABLE_NAME,
    RESULT2_XLSX_NAME,
    TABLE_OUTPUT_DIR,
    TEMPLATE_RESULT2,
    THETA_DEG,
)
from utils import (
    configure_matplotlib,
    ensure_directory,
    format_number,
    save_result2_excel,
    save_table_csv,
)


def calculate_question2_results():
    """计算不同测线方向和距中心距离下的水深、等效坡度与覆盖宽度。"""
    alpha = np.deg2rad(ALPHA_DEG)
    theta = np.deg2rad(THETA_DEG)
    half_theta = theta / 2.0

    direction_deg = np.asarray(QUESTION2_DIRECTIONS_DEG, dtype=float)
    distance_nm = np.asarray(QUESTION2_DISTANCES_NM, dtype=float)
    direction_rad = np.deg2rad(direction_deg)
    distance_m = distance_nm * NAUTICAL_MILE_M

    # 行对应测线方向，列对应测量船距海域中心的距离
    beta_grid, distance_grid_m = np.meshgrid(direction_rad, distance_m, indexing="ij")
    direction_grid_deg, distance_grid_nm = np.meshgrid(direction_deg, distance_nm, indexing="ij")

    # 测线横断面内的等效坡度：tan(alpha_perp)=tan(alpha)sin(beta)
    effective_slope_rad = np.arctan(np.tan(alpha) * np.sin(beta_grid))

    # 0°正方向规定为由中心指向深水侧，因此沿 0°方向移动时水深增加
    depth_m = QUESTION2_CENTER_DEPTH + distance_grid_m * np.tan(alpha) * np.cos(beta_grid)
    if np.any(depth_m <= 0):
        min_depth = float(depth_m.min())
        raise ValueError(f"存在非正水深，最小水深为 {min_depth:.2f} m，请检查方向约定或参数。")

    # 直接调用第一问的几何关系：仅将 alpha 替换为 alpha_perp，D 替换为当前位置水深
    left_width_m = (
        depth_m
        * np.sin(half_theta)
        / np.cos(half_theta + effective_slope_rad)
    )
    right_width_m = (
        depth_m
        * np.sin(half_theta)
        / np.cos(half_theta - effective_slope_rad)
    )
    width_m = left_width_m + right_width_m

    return pd.DataFrame(
        {
            "direction_deg": direction_grid_deg.ravel(),
            "distance_nm": distance_grid_nm.ravel(),
            "distance_m": distance_grid_m.ravel(),
            "depth_m": depth_m.ravel(),
            "effective_slope_deg": np.rad2deg(effective_slope_rad).ravel(),
            "left_width_m": left_width_m.ravel(),
            "right_width_m": right_width_m.ravel(),
            "width_m": width_m.ravel(),
        }
    )


def build_result_table(result_df):
    """按题目表 2 的形式生成 8×8 覆盖宽度表。"""
    direction_order = result_df["direction_deg"].drop_duplicates().tolist()
    distance_order = result_df["distance_nm"].drop_duplicates().tolist()

    width_table = result_df.pivot(
        index="direction_deg",
        columns="distance_nm",
        values="width_m",
    ).reindex(index=direction_order, columns=distance_order)

    columns = ["测线方向夹角/°"] + [format_number(value, digits=1) for value in distance_order]
    rows = []
    for direction_deg in direction_order:
        rows.append(
            [format_number(direction_deg, digits=0)]
            + [format_number(value) for value in width_table.loc[direction_deg].tolist()]
        )

    return pd.DataFrame(rows, columns=columns)


def _build_width_matrix(result_df):
    """构造绘图使用的方向×距离覆盖宽度矩阵。"""
    direction_order = result_df["direction_deg"].drop_duplicates().tolist()
    distance_order = result_df["distance_nm"].drop_duplicates().tolist()
    width_table = result_df.pivot(
        index="direction_deg",
        columns="distance_nm",
        values="width_m",
    ).reindex(index=direction_order, columns=distance_order)
    return direction_order, distance_order, width_table


def plot_width_heatmap(result_df, output_path):
    """绘制覆盖宽度随方向角和距离变化的热力图。"""
    configure_matplotlib()
    direction_order, distance_order, width_table = _build_width_matrix(result_df)

    fig, ax = plt.subplots(figsize=(9.0, 5.5))
    image = ax.imshow(width_table.to_numpy(), aspect="auto", origin="upper")

    ax.set_xticks(np.arange(len(distance_order)))
    ax.set_xticklabels([format_number(value, digits=1) for value in distance_order])
    ax.set_yticks(np.arange(len(direction_order)))
    ax.set_yticklabels([format_number(value, digits=0) for value in direction_order])
    ax.set_xlabel("测量船距海域中心点的距离 / 海里")
    ax.set_ylabel("测线方向夹角 β / °")

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("覆盖宽度 W / m")

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def plot_width_curves(result_df, output_path):
    """绘制各测线方向下覆盖宽度随距离的变化曲线。"""
    configure_matplotlib()
    direction_order, distance_order, width_table = _build_width_matrix(result_df)

    fig, ax = plt.subplots(figsize=(9.0, 5.5))
    for direction_deg in direction_order:
        ax.plot(
            distance_order,
            width_table.loc[direction_deg].to_numpy(),
            marker="o",
            label=fr"$\beta={direction_deg:.0f}^\circ$",
        )

    ax.set_xlabel("测量船距海域中心点的距离 / 海里")
    ax.set_ylabel("覆盖宽度 W / m")
    ax.grid(alpha=0.25)
    ax.legend(ncol=2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def run_question2():
    """执行第二问并输出 Excel、CSV 和结果图。"""
    ensure_directory(TABLE_OUTPUT_DIR)
    ensure_directory(FIGURE_OUTPUT_DIR)

    result_df = calculate_question2_results()
    table_df = build_result_table(result_df)

    save_result2_excel(TEMPLATE_RESULT2, TABLE_OUTPUT_DIR / RESULT2_XLSX_NAME, result_df)
    save_table_csv(table_df, TABLE_OUTPUT_DIR / RESULT2_TABLE_NAME)

    plot_width_heatmap(result_df, FIGURE_OUTPUT_DIR / QUESTION2_WIDTH_HEATMAP_NAME)
    plot_width_curves(result_df, FIGURE_OUTPUT_DIR / QUESTION2_WIDTH_CURVE_NAME)

    return result_df, table_df


if __name__ == "__main__":
    run_question2()
