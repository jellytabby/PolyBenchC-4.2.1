import sys
from pathlib import Path

import regex

if len(sys.argv) != 2:
    print("Usage: python3 split_kernel.py path/to/foo.c")
    sys.exit(1)

bench_file = Path(sys.argv[1])
bench_name = bench_file.stem.replace("-", "_")  # e.g. "foo"
text = bench_file.read_text()

combined = regex.compile(
    r"(static\s+void\s+kernel_%s\s*)(?>(?<args>\(([^\(\)]+|(?&args))*\)))\s*(?>(?<body>{([^{}]+|(?&body))*}))"
    % regex.escape(bench_name)
)  # let the record state that i built this cursed expression myself, chatgpt could never

m = combined.search(text)
if not m:
    print("Could not find `static void kernel_%s(…)` in %s" % (bench_name, bench_file))
    sys.exit(1)

kernel_def = m.group()

driver_text = text[: m.start()] + text[m.end() :]

kernel_c = f"""
/* Auto‐extracted kernel for {bench_name} */

#include <polybench.h>
#include "{bench_name}.h"   /* for DATA_TYPE, NI, NJ, NK, etc. */

{kernel_def.removeprefix("static")}
"""

hdr_proto = regex.search(
    r"(void\s+kernel_%s\s*)(?>(?<args>\(([^\(\)]+|(?&args))*\)))"
    % regex.escape(bench_name),
    kernel_def,
)
if not hdr_proto:
    print("Failed to extract prototype from kernel_def")
    sys.exit(1)

kernel_h = f"""
#ifndef {bench_name.upper()}_KERNEL_H
#define {bench_name.upper()}_KERNEL_H

#include <polybench.h>
#include "{bench_name}.h"

{hdr_proto.group()};  /* prototype */

#endif /* {bench_name.upper()}_KERNEL_H */
"""

driver_text = (
    "extern void __mc_profiling_begin(void);\nextern void __mc_profiling_end(void);"
    + driver_text
)

driver_text = driver_text.replace(
    f'#include "{bench_name}.h"',
    f'#include "{bench_name}.h"\n#include "{bench_name}_module.h"',
)

driver_text = driver_text.replace(
    "polybench_start_instruments;", "__mc_profiling_begin();"
)
driver_text = driver_text.replace(
    "polybench_stop_instruments;", "__mc_profiling_end();"
)

# 5) Write new files
new_parent_dir = bench_file.parent
kernel_c_path = new_parent_dir / f"{bench_name}_module.c"
kernel_h_path = new_parent_dir / f"{bench_name}_module.h"
driver_path = new_parent_dir / f"{bench_name}_main.c"

kernel_c_path.write_text(kernel_c.strip() + "\n")
kernel_h_path.write_text(kernel_h.strip() + "\n")
driver_path.write_text(driver_text)  # overwrite original .c with “driver only”

print(f"Extracted kernel → {kernel_c_path} and \nheader → {kernel_h_path}")
