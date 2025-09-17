Import("env")  # type: ignore
import os, re, subprocess, pathlib

ANGLE_RE = re.compile(r'^\s*#\s*include\s*<([^">]+)>\s*$')


def collect_angle_includes(roots):
    seen = set()
    for root in roots:
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if fn.endswith((".h", ".hpp", ".hh", ".ipp", ".c", ".cc", ".cpp", ".cxx")):
                    path = os.path.join(dirpath, fn)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                m = ANGLE_RE.match(line)
                                if m:
                                    seen.add(m.group(1))
                    except Exception:
                        pass
    return sorted(seen)


def preprocess(target, source, env):
    build_dir = env.subst("$BUILD_DIR")
    src_dir = env.subst("$PROJECT_SRC_DIR")
    include_dir = env.subst("$PROJECT_INCLUDE_DIR")
    out_file = os.path.join(build_dir, "mega.cpp")

    # pick entry
    entry = os.path.join(src_dir, "main.cpp")
    if not os.path.exists(entry):
        for dirpath, _, files in os.walk(src_dir):
            for fn in files:
                if fn.endswith(".cpp"):
                    entry = os.path.join(dirpath, fn)
                    break

    cxx = env.subst("$CXX")

    # 1) scan project for angle-bracket includes and stub them
    shim_dir = os.path.join(build_dir, "shim_includes")
    os.makedirs(shim_dir, exist_ok=True)

    angle_headers = collect_angle_includes([src_dir, include_dir])
    for hdr in angle_headers:
        p = pathlib.Path(shim_dir) / hdr
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(f"// stub: keep <{hdr}> unexpanded\n#pragma once\n")

    # 2) include only: shim + your project dirs
    inc_flags = []
    for d in (shim_dir, src_dir, include_dir):
        if d and os.path.isdir(d):
            inc_flags += ["-I", d]

    # 3) preprocess in C++ mode, expand locals only
    cmd = [cxx, "-E", "-P", "-nostdinc++"] + inc_flags + ["-o", out_file, entry]

    print("[Preprocess] Locals-only flatten:", entry, "->", out_file)
    print("[Preprocess] Stubbed angle-includes count:", len(angle_headers))
    # Uncomment to see the list
    # for h in angle_headers: print("   <", h, ">")

    try:
        subprocess.run(cmd, check=True, shell=False)
    except subprocess.CalledProcessError as e:
        print("[Preprocess] ERROR:", e)


env.AddPreAction("buildprog", preprocess)  # type: ignore
