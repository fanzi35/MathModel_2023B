from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

import matplotlib
import pandas as pd


def ensure_directory(path):
    """确保目录存在。"""
    Path(path).mkdir(parents=True, exist_ok=True)


def configure_matplotlib():
    """设置中文字体与负号显示。"""
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["mathtext.fontset"] = "stix"


def format_number(value, digits=2):
    """将数值格式化为固定小数位。"""
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def save_table_csv(df, output_path):
    """保存表格副本。"""
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


def _set_sheet_cell(sheet_root, cell_ref, value):
    """向工作表指定单元格写入数值。"""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    row_number = "".join(ch for ch in cell_ref if ch.isdigit())

    row_node = None
    for row in sheet_root.find("m:sheetData", ns).findall("m:row", ns):
        if row.attrib.get("r") == row_number:
            row_node = row
            break
    if row_node is None:
        row_node = ET.SubElement(
            sheet_root.find("m:sheetData", ns),
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row",
            {"r": row_number},
        )

    cell_node = None
    for cell in row_node.findall("m:c", ns):
        if cell.attrib.get("r") == cell_ref:
            cell_node = cell
            break
    if cell_node is None:
        cell_node = ET.SubElement(
            row_node,
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c",
            {"r": cell_ref},
        )

    cell_node.attrib.pop("t", None)
    value_node = cell_node.find("m:v", ns)
    if value_node is None:
        value_node = ET.SubElement(
            cell_node,
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v",
        )
    value_node.text = format_number(value)


def save_result1_excel(template_path, output_path, result_df):
    """基于模板写出第一问 Excel 结果。"""
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    zip_bytes = {}
    with ZipFile(template_path, "r") as zf:
        for name in zf.namelist():
            zip_bytes[name] = zf.read(name)

    workbook = ET.fromstring(zip_bytes["xl/workbook.xml"])
    rel_root = ET.fromstring(zip_bytes["xl/_rels/workbook.xml.rels"])
    rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root}
    first_sheet = workbook.find("m:sheets", ns)[0]
    rid = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
    sheet_path = "xl/" + rels[rid]
    sheet_root = ET.fromstring(zip_bytes[sheet_path])

    cols = ["B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for idx, col in enumerate(cols):
        row = result_df.iloc[idx]
        _set_sheet_cell(sheet_root, f"{col}2", row["depth_m"])
        _set_sheet_cell(sheet_root, f"{col}3", row["width_m"])
        if idx > 0:
            _set_sheet_cell(sheet_root, f"{col}4", row["overlap_rate_pct"])

    zip_bytes[sheet_path] = ET.tostring(sheet_root, encoding="utf-8", xml_declaration=True)

    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        for name, content in zip_bytes.items():
            zf.writestr(name, content)
