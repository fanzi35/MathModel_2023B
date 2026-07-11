from pathlib import Path
import math


# 第一问公共参数
THETA_DEG = 120.0
ALPHA_DEG = 1.5
CENTER_DEPTH = 70.0
LINE_SPACING_M = 200.0
DISTANCES_M = [-800, -600, -400, -200, 0, 200, 400, 600, 800]

# 截面示意图使用两条测线
SECTION_SAMPLE_INDEX = [4, 5]

# 第二问公共参数
QUESTION2_CENTER_DEPTH = 120.0
NAUTICAL_MILE_M = 1852.0
QUESTION2_DISTANCES_NM = [0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1]
QUESTION2_DIRECTIONS_DEG = [0, 45, 90, 135, 180, 225, 270, 315]

# 相对路径配置
TEMPLATE_RESULT1 = Path("docs") / "reference_formats" / "result1.xlsx"
TEMPLATE_RESULT2 = Path("docs") / "reference_formats" / "result2.xlsx"
TABLE_OUTPUT_DIR = Path("outputs") / "tables"
FIGURE_OUTPUT_DIR = Path("outputs") / "figures"

# 第一问输出文件名
RESULT1_XLSX_NAME = "question1_result.xlsx"
RESULT1_TABLE_NAME = "question1_result_table.csv"
SECTION_FIGURE_NAME = "question1_section_diagram.png"
DEPTH_FIGURE_NAME = "question1_depth_curve.png"
WIDTH_OVERLAP_FIGURE_NAME = "question1_width_overlap_curve.png"

# 第二问输出文件名
RESULT2_XLSX_NAME = "question2_result.xlsx"
RESULT2_TABLE_NAME = "question2_result_table.csv"
QUESTION2_WIDTH_HEATMAP_NAME = "question2_width_heatmap.png"
QUESTION2_WIDTH_CURVE_NAME = "question2_width_curve.png"

# 第三问公共参数
QUESTION3_CENTER_DEPTH_M = 110.0
QUESTION3_REGION_EW_NM = 4.0
QUESTION3_REGION_NS_NM = 2.0
QUESTION3_EAST_BOUNDARY_NM = QUESTION3_REGION_EW_NM / 2.0
QUESTION3_WEST_BOUNDARY_NM = -QUESTION3_REGION_EW_NM / 2.0
QUESTION3_NORTH_BOUNDARY_NM = QUESTION3_REGION_NS_NM / 2.0
QUESTION3_SOUTH_BOUNDARY_NM = -QUESTION3_REGION_NS_NM / 2.0
QUESTION3_OVERLAP_MIN = 0.10
QUESTION3_OVERLAP_MAX = 0.20
QUESTION3_OPTIMAL_BETA_RAD = math.pi / 2
QUESTION3_BETA_SCAN_DEG = list(range(0, 181, 2))

# 第三问输出文件名
QUESTION3_SUMMARY_NAME = "question3_summary.csv"
QUESTION3_LINE_PLAN_NAME = "question3_line_plan.csv"
QUESTION3_SCENE_3D_NAME = "question3_scene_3d.png"
QUESTION3_SECTION_NAME = "question3_section_beta_90.png"
QUESTION3_DISTRIBUTION_NAME = "question3_line_distribution.png"
QUESTION3_OVERLAP_NAME = "question3_overlap_curve.png"
QUESTION3_BETA_LENGTH_NAME = "question3_beta_length_curve.png"

# 第四问公共参数
QUESTION4_RAW_DATA_PATH = Path("data") / "raw" / "question4_raw_data.xlsx"
QUESTION4_MIN_REGION_ROWS = 32
QUESTION4_MIN_REGION_COLS = 28
QUESTION4_MAX_ORIENTATION_STD_DEG = 8.0
QUESTION4_MAX_PLANE_RMSE_M = 1.2
QUESTION4_TARGET_OVERLAP = 0.10
QUESTION4_LINE_SAMPLE_COUNT = 60
QUESTION4_MAX_GAP_FIX_ITER = 20

# 第四问输出文件名
QUESTION4_CONTOUR_NAME = "question4_contours_partitions.png"
QUESTION4_REGIONS_OVERVIEW_NAME = "question4_regions_overview.png"
QUESTION4_REGION_PREFIX = "question4_region_"
QUESTION4_REGION_SUMMARY_NAME = "question4_region_summary.csv"
QUESTION4_OVERALL_SUMMARY_NAME = "question4_overall_summary.csv"
