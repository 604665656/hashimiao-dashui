# -*- coding: utf-8 -*-
"""大水计算器 · 合并版 上架产物静态校验（只读，不改动源文件）。

用法： python tools/verify.py [入口 HTML 路径]
特别固化了 3 处 fetch 的边界，防止后续版本误引入默认外联。
"""
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "index.html")
EXPECT_SHA16 = "73e9b02f488b8fe1"
EXPECT_BYTES = 892131


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    raw = open(p, "rb").read()
    h = raw.decode("utf-8", "replace")
    sha = hashlib.sha256(raw).hexdigest()
    m = re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I)
    title = m.group(1).strip() if m else ""

    checks = [
        ("体积 < 1MiB 硬闸门", len(raw) < 1048576),
        ("体积 = 892131 B", len(raw) == EXPECT_BYTES),
        ("SHA256 前 16 位 = 73e9b02f488b8fe1", sha[:16] == EXPECT_SHA16),
        ("标题含「大水计算器 · 合并版」", "大水计算器" in title and "合并版" in title),
        ("无 script[src]", len(re.findall(r"<script[^>]*\bsrc=", h, re.I)) == 0),
        ("无 link stylesheet", len(re.findall(r"<link[^>]*stylesheet", h, re.I)) == 0),
        ("无 http(s) src/href", len(re.findall(r'(?:src|href)\s*=\s*["\']https?://', h, re.I)) == 0),
        ("script 标签配对 (3 段)", h.count("<script") == h.count("</script>") == 3),
        ("style 标签配对", h.count("<style") == h.count("</style>")),
        ("内嵌素材 62 处 data:image", h.count("data:image") == 62),
        ("fetch 恰好 3 处", h.count("fetch(") == 3),
        ("零 XMLHttpRequest", h.count("XMLHttpRequest") == 0),
        ("唯一外部域名 Open-Meteo", h.count("api.open-meteo.com") == 1),
        ("天气请求带超时降级", "AbortController" in h and "（离线，手动设定）" in h),
        ("在线模型默认不启用", "endpoint:''" in h.replace(" ", "") and "key:''" in h.replace(" ", "")),
        ("在线模型需显式 endpoint+key", "cfg.endpoint&&cfg.key" in h.replace(" ", "")),
        ("fetch(png) 为本地分享卡", "fetch(png)" in h.replace(" ", "")),
        ("桌宠存档 dashui.pet.v1", "dashui.pet.v1" in h),
        ("AVG 旧档合并 dashui.avg.v1", "dashui.avg.v1" in h),
        ("Toy SDK 能力探测", "available()" in h),
        ("Toy 云档分片 ds_meta", "ds_meta" in h),
        ("Toy 分数榜 rank.submit", "rank.submit" in h),
        ("SDK 未就绪静默降级", "degraded" in h),
        ("虚拟形象可切换", "虚拟形象" in h),
        ("Canvas 成绩卡", h.count("getContext") >= 2),
        ("HTML 闭合", "</html>" in h.lower()),
    ]

    print("校验目标:", p)
    print("体积 %d B / sha256 %s / title %s" % (len(raw), sha[:16], title))
    print("-" * 60)
    for name, ok in checks:
        print(("  PASS  " if ok else "  FAIL  ") + name)
    bad = [n for n, ok in checks if not ok]
    print("-" * 60)
    print("%d/%d PASS" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
