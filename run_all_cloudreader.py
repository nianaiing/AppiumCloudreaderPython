# -*- coding: utf-8 -*-
'''
CloudReader 用例总入口: 依次执行各个脚本, 单个用例失败不影响后面的

默认顺序:
  1. login_cloudreader.py          登录 / 退出
  2. search_cloudreader.py         搜索查询
  3. switch_subtabs_cloudreader.py 二级菜单(tab)切换
  4. switch_pages_cloudreader.py   侧滑菜单 + 顶部 tab 切换

默认跳过(会在汇总里标成 SKIP):
  collect_cloudreader.py           收藏: App 侧"我的收藏"页首次进入不加载数据, 已知问题
  api_cloudreader.py               纯接口调试: 需要外网, 用 --with-api 打开

用法:
  python run_all_cloudreader.py                       # 跑 1~4, 收藏标为跳过
  python run_all_cloudreader.py --dry-run             # 只看会跑哪些用例, 不启动 App
  python run_all_cloudreader.py --with-collect        # 把收藏用例也一起跑
  python run_all_cloudreader.py --with-api            # 加上纯接口脚本(需要外网)
  python run_all_cloudreader.py --only search,login   # 只跑指定用例(用脚本名前缀)
  python run_all_cloudreader.py --skip search         # 跳过指定用例
  python run_all_cloudreader.py --case-timeout 240    # 单个用例最多跑 240s, 超时就跳过继续

每个用例都是独立的子进程: 某个用例失败(非 0 退出码)只记一笔 FAIL, 不会中断后面
的用例, 最后打印 PASS/FAIL/SKIP 汇总。
'''

import argparse
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")   # 控制台中文输出
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# run: 默认是否执行; needs_device: 是否接受 -d 设备参数(Appium 用例才需要)
CASES = [
    {"script": "login_cloudreader.py", "desc": "登录 / 退出", "run": True, "needs_device": True, "args": []},
    {"script": "search_cloudreader.py", "desc": "搜索查询", "run": True, "needs_device": True, "args": ["-k", "Android"]},
    {"script": "switch_subtabs_cloudreader.py", "desc": "二级菜单(tab)切换", "run": True, "needs_device": True, "args": []},
    {"script": "switch_pages_cloudreader.py", "desc": "侧滑菜单 + 顶部 tab 切换", "run": True, "needs_device": True, "args": []},
    {"script": "collect_cloudreader.py", "desc": "收藏(App 侧'我的收藏'页已知问题, 默认跳过)",
     "run": False, "needs_device": True, "args": []},
    {"script": "api_cloudreader.py", "desc": "接口调试(需要外网, 默认跳过)",
     "run": False, "needs_device": False, "args": []},
]


def stem(script):
    return os.path.splitext(script)[0]


def python_exe(args):
    '''默认用当前解释器; 也可以显式指定(比如项目里的 venv)'''
    if getattr(args, "python", None):
        return args.python
    venv = os.path.join(HERE, "venv", "Scripts", "python.exe")   # Windows
    if os.path.isfile(venv):
        return venv
    return sys.executable


def build_command(case, args):
    command = [python_exe(args), os.path.join(HERE, case["script"])] + case["args"]
    if case["needs_device"]:
        command += ["-d", args.device, "-u", args.username, "-p", args.password]
    return command


def main():
    parser = argparse.ArgumentParser(description="CloudReader 用例总入口")
    parser.add_argument("-d", "--device", default="emulator-5556", help="设备名/udid")
    parser.add_argument("-u", "--username", default="test00300", help="玩安卓账号")
    parser.add_argument("-p", "--password", default="123456", help="玩安卓密码")
    parser.add_argument("--only", default="", help="只跑指定用例, 逗号分隔(脚本名前缀即可)")
    parser.add_argument("--skip", default="", help="跳过指定用例, 逗号分隔")
    parser.add_argument("--with-collect", action="store_true", help="连收藏用例一起跑(App 侧已知问题)")
    parser.add_argument("--with-api", action="store_true", help="加上纯接口脚本(需要外网)")
    parser.add_argument("--python", default="", help="指定解释器(默认: 本目录 venv 里的 python, 没有就用当前解释器)")
    parser.add_argument("--case-timeout", type=int, default=300,
                        help="单个用例最长执行秒数, 超时杀掉该用例并记 FAIL, 继续跑后面的(0=不限制)")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要执行的用例和命令, 不真正执行")
    args = parser.parse_args()

    only = [item.strip() for item in args.only.split(",") if item.strip()]
    skip = [item.strip() for item in args.skip.split(",") if item.strip()]

    selected = []
    for case in CASES:
        name = stem(case["script"])
        if only and not any(name.startswith(item) for item in only):
            continue
        if any(name.startswith(item) for item in skip):
            continue
        if not only:
            # 默认只跑 run=True 的; --with-xxx 用来把默认跳过的那些放进来
            enabled = case["run"] or args.with_collect
            if name == "api_cloudreader" and args.with_api:
                enabled = True
            if not enabled:
                continue
        selected.append(case)

    print("=== CloudReader 用例总入口 ===")
    print("设备:", args.device, "| 账号:", args.username, "| 用例数:", len(selected))
    print("解释器:", python_exe(args))
    if args.dry_run:
        for index, case in enumerate(selected, 1):
            print("  [%d] %-30s %s" % (index, case["script"], case["desc"]))
            print("      命令: %s" % " ".join(build_command(case, args)))
        for case in CASES:
            if case not in selected:
                print("  [SKIP] %-27s %s" % (case["script"], case["desc"]))
        return 0

    results = []

    for index, case in enumerate(selected, 1):
        name = stem(case["script"])
        print("\n>>> [%d/%d] %s (%s)" % (index, len(selected), case["desc"], case["script"]))
        started = time.time()
        try:
            code = subprocess.run(build_command(case, args), cwd=HERE,
                                  timeout=args.case_timeout or None).returncode
        except subprocess.TimeoutExpired:
            code = 124
            print("!!! %s 超过 %ss 还没结束, 已终止该用例, 继续跑后面的" % (name, args.case_timeout))
        used = time.time() - started
        results.append((name, code, used))
        print("<<< [%d/%d] %s 结束, 退出码 %s, 用时 %.1fs" % (index, len(selected), name, code, used))

    skipped = [case for case in CASES if case not in selected]
    print("\n========== 汇总 ==========")
    for name, code, used in results:
        print("[%s] %-28s %6.1fs" % ("PASS" if code == 0 else "FAIL", name, used))
    for case in skipped:
        print("[SKIP] %-28s %s" % (stem(case["script"]), case["desc"]))

    failed = [name for name, code, _ in results if code != 0]
    print("通过 %d 个, 失败 %d 个%s" % (len(results) - len(failed), len(failed),
                                    (", 失败用例: " + ", ".join(failed)) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
