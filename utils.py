from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

import matplotlib
import numpy as np
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


def save_table_csv(df, output_path, include_header=True):
    """保存表格副本。"""
    ensure_directory(Path(output_path).parent)
    df.to_csv(output_path, index=False, header=include_header, encoding="utf-8-sig")


def _set_sheet_cell(sheet_root, cell_ref, value):
    """向工作表指定单元格写入数值。"""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    row_number = "".join(ch for ch in cell_ref if ch.isdigit())

    sheet_data = sheet_root.find("m:sheetData", ns)
    if sheet_data is None:
        sheet_data = ET.SubElement(
            sheet_root,
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData",
        )

    row_node = None
    for row in sheet_data.findall("m:row", ns):
        if row.attrib.get("r") == row_number:
            row_node = row
            break
    if row_node is None:
        row_node = ET.SubElement(
            sheet_data,
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
    inline_string = cell_node.find("m:is", ns)
    if inline_string is not None:
        cell_node.remove(inline_string)

    value_node = cell_node.find("m:v", ns)
    if value_node is None:
        value_node = ET.SubElement(
            cell_node,
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v",
        )
    value_node.text = format_number(value)


def _first_sheet_path(zip_bytes):
    """解析 Excel 工作簿中第一个工作表的压缩包路径。"""
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    }

    workbook = ET.fromstring(zip_bytes["xl/workbook.xml"])
    rel_root = ET.fromstring(zip_bytes["xl/_rels/workbook.xml.rels"])
    rels = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rel_root.findall("p:Relationship", ns)
    }

    first_sheet = workbook.find("m:sheets", ns)[0]
    relation_id = first_sheet.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ]
    target = rels[relation_id].lstrip("/")

    if target.startswith("xl/"):
        return str(PurePosixPath(target))
    return str(PurePosixPath("xl") / PurePosixPath(target))


def _write_template_cells(template_path, output_path, cell_values):
    """在 Excel 模板第一个工作表中批量写入数值。"""
    zip_bytes = {}
    with ZipFile(template_path, "r") as zf:
        for name in zf.namelist():
            zip_bytes[name] = zf.read(name)

    sheet_path = _first_sheet_path(zip_bytes)
    sheet_root = ET.fromstring(zip_bytes[sheet_path])

    for cell_ref, value in cell_values.items():
        _set_sheet_cell(sheet_root, cell_ref, value)

    zip_bytes[sheet_path] = ET.tostring(sheet_root, encoding="utf-8", xml_declaration=True)

    output_path = Path(output_path)
    ensure_directory(output_path.parent)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        for name, content in zip_bytes.items():
            zf.writestr(name, content)


def save_result1_excel(template_path, output_path, result_df):
    """基于模板写出第一问 Excel 结果。"""
    cell_values = {}
    cols = ["B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for idx, col in enumerate(cols):
        row = result_df.iloc[idx]
        cell_values[f"{col}2"] = row["depth_m"]
        cell_values[f"{col}3"] = row["width_m"]
        if idx > 0:
            cell_values[f"{col}4"] = row["overlap_rate_pct"]

    _write_template_cells(template_path, output_path, cell_values)


def save_result2_excel(template_path, output_path, result_df):
    """基于模板写出第二问 Excel 结果。"""
    direction_order = result_df["direction_deg"].drop_duplicates().tolist()
    distance_order = result_df["distance_nm"].drop_duplicates().tolist()

    width_table = result_df.pivot(
        index="direction_deg",
        columns="distance_nm",
        values="width_m",
    ).reindex(index=direction_order, columns=distance_order)

    cols = ["C", "D", "E", "F", "G", "H", "I", "J"]
    rows = range(3, 11)
    if width_table.shape != (len(rows), len(cols)):
        raise ValueError(
            "第二问结果表应为 8×8；"
            f"当前得到 {width_table.shape[0]}×{width_table.shape[1]}。"
        )

    cell_values = {}
    for row_number, direction_deg in zip(rows, direction_order):
        for col, distance_nm in zip(cols, distance_order):
            cell_values[f"{col}{row_number}"] = width_table.loc[direction_deg, distance_nm]

    _write_template_cells(template_path, output_path, cell_values)


def _column_label_to_index(label):
    """将 Excel 列标转换为从 0 开始的列序号。"""
    value = 0
    for char in label:
        value = value * 26 + (ord(char.upper()) - ord("A") + 1)
    return value - 1


def _cell_ref_to_index(cell_ref):
    """将单元格引用转换为从 0 开始的行列序号。"""
    col_label = "".join(ch for ch in cell_ref if ch.isalpha())
    row_label = "".join(ch for ch in cell_ref if ch.isdigit())
    return int(row_label) - 1, _column_label_to_index(col_label)


def read_numeric_excel_sheet(path):
    """只读解析数值型 xlsx 工作表并返回 DataFrame。"""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    zip_bytes = {}
    with ZipFile(path, "r") as zf:
        for name in zf.namelist():
            zip_bytes[name] = zf.read(name)

    sheet_path = _first_sheet_path(zip_bytes)
    root = ET.fromstring(zip_bytes[sheet_path])
    dimension = root.find("m:dimension", ns)
    if dimension is None:
        raise ValueError("Excel 缺少 dimension 信息")

    end_ref = dimension.attrib["ref"].split(":")[-1]
    max_row, max_col = _cell_ref_to_index(end_ref)
    data = np.full((max_row + 1, max_col + 1), np.nan, dtype=float)

    for row in root.find("m:sheetData", ns).findall("m:row", ns):
        for cell in row.findall("m:c", ns):
            cell_ref = cell.attrib.get("r")
            if not cell_ref:
                continue
            value_node = cell.find("m:v", ns)
            if value_node is None or value_node.text in (None, ""):
                continue
            row_idx, col_idx = _cell_ref_to_index(cell_ref)
            data[row_idx, col_idx] = float(value_node.text)

    return pd.DataFrame(data)
