#!/usr/bin/env python3
"""无头浏览器渲染 Web 前端并截图（供 UI 视觉检查）。

用法:
    # 1. 启动服务: uv run python3 examples/web/server.py --port 8000
    # 2. 截图（需 playwright + chromium）:
    LD_LIBRARY_PATH=~/pw-libs .venv/bin/python3 examples/web/screenshot_ui.py \
        --state done --out /tmp/sherpa_ui.png

--state: idle 页面初始 | processing 回放中 | done 处理完成（默认）
"""
from __future__ import annotations

import argparse
import time

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description="渲染 Web 前端并截图")
    parser.add_argument("--url", default="http://127.0.0.1:8000/")
    parser.add_argument("--out", default="/tmp/sherpa_ui.png")
    parser.add_argument("--state", choices=["idle", "processing", "done"], default="done")
    args = parser.parse_args()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))

        page.goto(args.url, wait_until="networkidle")
        # 等待 vue 挂载（连接状态从"未连接"变化）
        page.wait_for_function(
            "!!document.querySelector('.status') && document.querySelector('.status').textContent !== '未连接'", timeout=15000
        )

        if args.state in ("processing", "done"):
            # 加载 demo 音频
            page.select_option("#demoFile", index=0)
            page.click("text=加载")
            page.wait_for_function(
                "!!document.querySelector('.src-bar .hint') && document.querySelector('.src-bar .hint').textContent.includes('s')",
                timeout=15000,
            )
            # 流式 ASR + 启动
            page.select_option("#asrMode", "streaming")
            page.select_option("#speed", "0")  # 最快
            page.click("#startBtn")
            page.wait_for_function(
                "!!document.querySelector('.status') && document.querySelector('.status').textContent.includes('处理')",
                timeout=10000,
            )
            if args.state == "done":
                page.wait_for_function(
                    "!!document.querySelector('.status') && document.querySelector('.status').textContent.includes('完成')",
                    timeout=120000,
                )
            else:
                time.sleep(3)  # 抓取处理中状态

        time.sleep(1)
        page.screenshot(path=args.out)
        print(f"截图已保存: {args.out}")
        if js_errors:
            print("JS 错误:")
            for e in js_errors:
                print("  ", e)
        browser.close()


if __name__ == "__main__":
    main()
