import os
import sys
import math
import pandas as pd
from pyproj import CRS, Transformer

def usage():
    print("用法: python make_ref_images_from_gps.py /path/to/gps_raw.csv")
    print("  - CSV 需要至少包含列: GPSLatitude, GPSLongitude, GPSAltitude")
    print("  - 会在同目录生成 <csv_basename>_ref_images.txt")
    sys.exit(1)

def auto_choose_utm_epsg(latitudes, longitudes):
    """
    根据经纬度自动选择 UTM EPSG:
      - 先取所有点的平均经纬度 (lat0, lon0)
      - 计算 UTM 带号 zone = floor((lon0 + 180)/6) + 1  (1..60)
      - 北半球: EPSG = 32600 + zone
      - 南半球: EPSG = 32700 + zone
    """
    if len(latitudes) == 0 or len(longitudes) == 0:
        raise RuntimeError("没有经纬度数据，无法自动选择 UTM EPSG")

    lat0 = float(sum(latitudes) / len(latitudes))
    lon0 = float(sum(longitudes) / len(longitudes))

    zone = int(math.floor((lon0 + 180.0) / 6.0) + 1)
    zone = max(1, min(zone, 60))  # 安全限制在 [1, 60]

    if lat0 >= 0:
        epsg = 32600 + zone  # 北半球
        hemisphere = "N"
    else:
        epsg = 32700 + zone  # 南半球
        hemisphere = "S"

    print(f"[INFO] 平均经纬度: lat={lat0:.6f}, lon={lon0:.6f}")
    print(f"[INFO] 自动选择 UTM Zone: {zone}{hemisphere}, EPSG:{epsg}")
    return epsg, zone, hemisphere

def main():
    if len(sys.argv) != 2:
        usage()

    csv_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(csv_path):
        print(f"[ERROR] 找不到文件: {csv_path}")
        usage()

    # 输出路径: 与输入 CSV 同目录, 文件名 = <basename>_ref_images.txt
    csv_dir = os.path.dirname(csv_path)
    csv_base = os.path.splitext(os.path.basename(csv_path))[0]
    out_path = os.path.join(csv_dir, f"{csv_base}_ref_images.txt")

    print(f"[INFO] 读取 CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    required_cols = {"GPSLatitude", "GPSLongitude", "GPSAltitude"}
    if not required_cols.issubset(df.columns):
        raise RuntimeError(
            f"CSV 缺少必要列 {required_cols}，实际列: {list(df.columns)}\n"
            "请确保 exiftool 命令包含: -GPSLatitude -GPSLongitude -GPSAltitude"
        )

    lats = df["GPSLatitude"].tolist()
    lons = df["GPSLongitude"].tolist()

    # 自动选 UTM EPSG
    epsg_utm, zone, hemi = auto_choose_utm_epsg(lats, lons)

    crs_wgs84 = CRS.from_epsg(4326)
    crs_utm = CRS.from_epsg(epsg_utm)
    transformer = Transformer.from_crs(crs_wgs84, crs_utm, always_xy=True)

    # 经纬度 -> UTM
    xs, ys = transformer.transform(df["GPSLongitude"].values, df["GPSLatitude"].values)
    zs = df["GPSAltitude"].values

    df["X"] = xs
    df["Y"] = ys
    df["Z"] = zs

    # 写 ref_images 文件 (IMAGE_NAME X Y Z)
    # 优先使用 FileName 列，否则退回到 SourceFile 的 basename
    print(f"[INFO] 写出 ref_images 文件: {out_path}")
    with open(out_path, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            name = None
            if "FileName" in df.columns and isinstance(row.get("FileName"), str):
                name = row["FileName"].strip()
            if not name:
                src = str(row.get("SourceFile", "")).strip()
                name = os.path.basename(src)
            if not name:
                continue  # 实在没有名字就跳过

            x, y, z = row["X"], row["Y"], row["Z"]
            f.write(f"{name} {x:.6f} {y:.6f} {z:.6f}\n")

    print("[INFO] 完成。请在 COLMAP model_aligner 中使用该文件作为 --ref_images_path")
    print(f"       UTM Zone: {zone}{hemi}, EPSG:{epsg_utm}")

if __name__ == "__main__":
    main()