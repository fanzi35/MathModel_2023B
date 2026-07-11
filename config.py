from pathlib import Path


# 第一问公共参数
THETA_DEG = 120.0
ALPHA_DEG = 1.5
CENTER_DEPTH = 70.0
LINE_SPACING_M = 200.0
DISTANCES_M = [-800, -600, -400, -200, 0, 200, 400, 600, 800]

# 截面示意图使用两条测线
SECTION_SAMPLE_INDEX = [4, 5]

# 相对路径配置
TEMPLATE_RESULT1 = Path("docs") / "reference_formats" / "result1.xlsx"
TABLE_OUTPUT_DIR = Path("outputs") / "tables"
FIGURE_OUTPUT_DIR = Path("outputs") / "figures"

# 输出文件名
RESULT1_XLSX_NAME = "question1_result.xlsx"
RESULT1_TABLE_NAME = "question1_result_table.csv"
SECTION_FIGURE_NAME = "question1_section_diagram.png"
DEPTH_FIGURE_NAME = "question1_depth_curve.png"
WIDTH_OVERLAP_FIGURE_NAME = "question1_width_overlap_curve.png"
