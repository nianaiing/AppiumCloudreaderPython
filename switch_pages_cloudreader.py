# -*- coding: utf-8 -*-
'''
CloudReader 页面切换脚本 (Appium + UiAutomator2)

覆盖两类页面切换:
  1. 主界面顶部三个 tab (app_bar_main.xml: iv_title_one/two/three)
       1) 玩安卓 / 广场 / 问答
       2) 发现 / 体系 / 导航
       3) 开源项目 (tab 名来自 GET /tree/json, 由接口动态生成)
  2. 侧滑菜单各入口 (nav_header_main.xml), 逐个进入并校验目标 Activity, 再返回主界面
       项目主页 / 扫码下载 / 问题反馈 / 关于云阅 / 赞赏云阅 / 深色模式
       我的收藏 / 我的分享 / 积分系统  (这三项需要先登录)

用法:
  python switch_pages_cloudreader.py                 # 顶部 tab + 侧滑菜单
  python switch_pages_cloudreader.py --only tabs     # 只切顶部 tab
  python switch_pages_cloudreader.py --only drawer   # 只切侧滑菜单
'''

import time

from cloudreader_common import (
    build_parser,
    by_id,
    by_text,
    click_any,
    click_element,
    click_present,
    close_drawer,
    dismiss_startup_dialogs,
    drawer_username,
    first_displayed,
    open_drawer,
    start_driver,
    wait_activity,
    wait_main_page,
)

# 顶部 tab: (资源 id, 说明, 用来确认页面真的切过去的文案; 项目页为动态 tab, 用 tab_gank 判断)
MAIN_TABS = [
    ("iv_title_one", "玩安卓/广场/问答", "问答"),
    ("iv_title_two", "发现/体系/导航", "体系"),
    ("iv_title_three", "开源项目(动态tab)", None),
]

# 侧滑菜单: (资源 id, 名称, 目标 Activity, 是否需要登录)
# ll_nav_admire(赞赏云阅) 只在部分版本里有, 本机没有会自动跳过
DRAWER_PAGES = [
    ("ll_nav_homepage", "项目主页", "NavHomePageActivity", False),
    ("ll_nav_scan_download", "扫码下载", "NavDownloadActivity", False),
    ("ll_nav_deedback", "问题反馈", "NavDeedBackActivity", False),
    ("ll_nav_about", "关于云阅", "NavAboutActivity", False),
    ("ll_nav_admire", "赞赏云阅(3.8.3+)", "NavAdmireActivity", False),
    ("ll_nav_night_mode", "深色模式", "NavNightModeActivity", False),
    ("ll_nav_collect", "我的收藏", "MyCollectActivity", True),
    ("ll_nav_share", "我的分享", "MyShareActivity", True),
    ("ll_nav_coin", "积分系统", "MyCoinActivity", True),
]


def switch_main_tabs(driver):
    close_drawer(driver)
    print("--- 主界面顶部 tab ---")
    for res_id, name, marker in MAIN_TABS:
        click_element(driver, by_id(res_id), 10, "顶部 tab [%s]" % name)
        time.sleep(2)
        if marker:
            ok = first_displayed(driver, by_text(marker)) is not None
            detail = "tab[%s] 已可见" % marker
        else:
            ok = first_displayed(driver, by_id("tab_gank")) is not None
            detail = "项目 tab 栏已可见"
        print("  切换到 %s: %s (%s)" % (name, "OK" if ok else "未确认", detail))

    click_element(driver, by_id("iv_title_one"), 10, "回到第一个 tab")
    time.sleep(1)


def switch_inner_tabs(driver, activity):
    '''二级页面里的 TabLayout: 我的收藏(文章/网址/段子)、积分系统(我的积分/积分排行榜)'''
    tabs = ["网址", "段子"] if "MyCollect" in activity else ["积分排行榜"]
    for tab in tabs:
        if click_any(driver, [by_text(tab)], 5, "子 tab[%s]" % tab):
            time.sleep(1)
            print("    已切换子 tab:", tab)
        else:
            print("    未找到子 tab:", tab)


def switch_drawer_pages(driver, logged_in):
    print("--- 侧滑菜单页面 ---")
    for res_id, name, activity, need_login in DRAWER_PAGES:
        if need_login and not logged_in:
            print("  跳过 %s: 需要先登录 (python login_cloudreader.py)" % name)
            continue

        open_drawer(driver)
        if click_present(driver, by_id(res_id), 5, name) is None:
            print("  跳过 %s: 本机这个版本没有该入口" % name)
            continue

        current = wait_activity(driver, activity, 12)
        if current is None:
            print("  %s -> 未进入 %s, 当前页面: %s" % (name, activity, driver.current_activity))
            continue
        print("  %s -> %s" % (name, current))

        if activity in ("MyCollectActivity", "MyCoinActivity"):
            switch_inner_tabs(driver, activity)

        driver.back()
        time.sleep(1)
        if "MainActivity" not in (driver.current_activity or ""):
            driver.back()                  # 有的页面可能是 WebView 里再退一层
            time.sleep(1)
        wait_main_page(driver)
    close_drawer(driver)


def main():
    parser = build_parser("CloudReader 页面切换脚本")
    parser.add_argument("--only", choices=["all", "tabs", "drawer"], default="all", help="只跑其中一类")
    args = parser.parse_args()

    driver = start_driver(args.device, args.appium)
    try:
        dismiss_startup_dialogs(driver)
        print("已进入主界面:", wait_main_page(driver))

        username = drawer_username(driver)
        logged_in = username != "玩安卓登录"
        print("当前登录状态:", username if logged_in else "未登录")
        close_drawer(driver)

        if args.only in ("all", "tabs"):
            switch_main_tabs(driver)
        if args.only in ("all", "drawer"):
            switch_drawer_pages(driver, logged_in)

        print("=== 页面切换流程结束, 当前页面:", driver.current_activity, "===")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
