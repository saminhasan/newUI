import os
import json
import struct
import zlib
import numpy as np
from collections import defaultdict
from tkinter import filedialog
from parser import Parser
import pandas as pd


def flatten_dict(d, parent_key="", sep="."):
    """Recursively flatten nested dicts into a flat dict with dotted keys."""
    items = []
    for k, v in d.items():
        new_key = f"{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def process_frames(frames, outfile="frames.xlsx"):
    """
    Process a list of frames into an Excel file.
    - FEEDBACK frames → split by axisId (sheet per axis).
    - Other frames → sheet per msg_id.
    - Dicts are flattened so no nested blobs.
    """
    # Collect frames into buckets by sheet name
    buckets = {}

    for frame in frames:
        msg_id = frame.get("msg_id", "UNKNOWN")
        payload = frame.get("payload", {})

        # Decide sheet name
        if msg_id == "FEEDBACK":
            axis_id = payload.get("axisId", "unknown")
            sheet_name = f"axis_{axis_id}"
        else:
            sheet_name = msg_id

        # Flatten everything for consistent tabular format
        flat = flatten_dict(frame)

        if sheet_name not in buckets:
            buckets[sheet_name] = []
        buckets[sheet_name].append(flat)

    # Write each bucket into Excel
    with pd.ExcelWriter(outfile, engine="xlsxwriter") as writer:
        for sheet_name, rows in buckets.items():
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Excel limit 31 chars

    print(f"Saved {len(buckets)} sheets to {outfile}")


def main():

    # ---- Select file ----
    file_path = filedialog.askopenfilename(title="Select File", filetypes=[("All Files", "*.*")])
    if not file_path:
        print("No file selected.")
        return
    filename = os.path.splitext(os.path.basename(file_path))[0]
    print(f"Processing: {os.path.basename(file_path)}")

    # ---- Read all bytes ----
    with open(file_path, "rb") as file:
        data = bytearray(file.read())
    parser = Parser()
    parser.parse(data)

    # for frame in parser.frames:
    #     print("-" * 20)
    #     print(frame)
    #     print("-" * 20)
    process_frames(parser.frames, outfile=f"{filename}.xlsx")


if __name__ == "__main__":
    main()
