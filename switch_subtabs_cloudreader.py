# -*- coding: utf-8 -*-
'''
CloudReader 二级菜单(tab)覆盖测试 (Appium + UiAutomator2)

覆盖的菜单结构(括号里是源码位置):
  最左 icon iv_title_one    (WanFragment.java:31)       玩安卓 / 广场 / 问答
  中间 icon iv_title_two    (WanCenterFragment.kt:26)   发现 / 体系 / 导航
  最右 icon iv_title_three  (WanProjectFragment.kt)     项目, 二级 tab 名由 GET /tree/json
                                                        动态生成, 脚本运行时现场读取;
                                                        tab 栏可横向滚动, 点不到会自动左滑再试

每个二级 tab 点完后做两项校验:
  1. TabLayout 里该 tab 的 selected 状态(真机层级里选中项是 selected="true")
  2. 该页列表控件是否展示(fragment_wan_android -> xrv_wan, fragment_square/fragment_android
     -> xrv_android, fragment_wan_find -> rv_wxarticle, fragment_navi -> xrv_navi)

结束打印覆盖率汇总: OK / WARN(点了但没确认到) / FAIL(点不到) / SKIP,
有 FAIL(或 --strict 下的 WARN)时退出码为 1。

用法:
  python switch_subtabs_cloudreader.py              # 三个 icon 全跑
  python switch_subtabs_cloudreader.py --tops 1     # 只跑 玩安卓/广场/问答
  python switch_subtabs_cloudreader.py --tops 1,2   # 跑前两个 icon
  python switch_subtabs_cloudreader.py --strict     # WARN 也算失败
  python switch_subtabs_cloudreader.py -d emulator-5556
'''

import sys
import time

from appium.webdriver.common.appiumby import AppiumBy

from cloudreader_common import (
    build_parser,
    by_desc,
    by_id,
    click_any,
    click_element,
    dismiss_startup_dialogs,
    first_displayed,
    start_driver,
    wait_main_page,
)

# key: --tops 里用; subs: (二级 tab 名, 该页用来确认的列表控件 id); None 表示动态读取
TOP_TABS = [
    {
        "key": "1",
        "icon": "iv_title_one",
        "name": "玩安卓(最左 icon)",
        "subs": [("玩安卓", "xrv_wan"), ("广场", "xrv_android"), ("问答", "xrv_android")],
    },
    {
        "key": "2",
        "icon": "iv_title_two",
        "name": "发现(中间 icon)",
        "subs": [("发现", "rv_wxarticle"), ("体系", "xrv_wan"), ("导航", "xrv_navi")],
    },
    {
        "key": "3",
        "icon": "iv_title_three",
        "name": "项目(最右 icon)",
        "subs": None,
    },
]

TAB_BAR = "tab_gank"                 # fragment_content.xml 里的 TabLayout
SELECTED_TAB = "//android.widget.TextView[@text='{0}'][@selected='true']"

RESULTS = []                         # (icon 名, tab 名, OK/WARN/FAIL/SKIP, 说明)


def record(icon, tab, status, detail=""):
    RESULTS.append((icon, tab, status, detail))
    print("  二级 tab[%s]: %s%s" % (tab, status, (" (" + detail + ")") if detail else ""))


def tab_selected(driver, title):
    '''真机层级里选中的 tab 会是 selected="true"'''
    return first_displayed(driver, (AppiumBy.XPATH, SELECTED_TAB.format(title))) is not None


def tab_locators(title):
    return [
        by_desc(title),
        (AppiumBy.XPATH, "//*[@content-desc='{0}']".format(title)),
        (AppiumBy.XPATH, "//android.widget.TextView[@text='{0}']".format(title)),
    ]


def swipe_tab_bar(driver):
    '''项目页的 tab 栏可以横向滚动, 用来把后面的 tab 滑进屏幕'''
    tab_bar = first_displayed(driver, by_id(TAB_BAR))
    if tab_bar is None:
        return False
    rect = tab_bar.rect
    if rect.get("width", 0) < 10:
        return False
    y = rect["y"] + rect["height"] // 2
    driver.swipe(rect["x"] + int(rect["width"] * 0.85), y,
                 rect["x"] + int(rect["width"] * 0.15), y, 400)
    return True


def click_sub_tab(driver, title):
    '''点二级 tab: 先在当前屏找, 找不到就把 tab 栏往左滑一次再找'''
    if click_any(driver, tab_locators(title), 4, "二级 tab[%s]" % title) is not None:
        return True
    if swipe_tab_bar(driver):
        time.sleep(1)
        return click_any(driver, tab_locators(title), 4, "二级 tab[%s]" % title) is not None
    return False


def read_tab_titles(driver, limit=12):
    '''读取当前页 TabLayout 里的 tab 文案(项目页的 tab 名来自接口)'''
    tab_bar = first_displayed(driver, by_id(TAB_BAR))
    if tab_bar is None:
        return []
    titles = []
    for node in tab_bar.find_elements(AppiumBy.XPATH, ".//android.widget.TextView[@text]"):
        value = (node.text or "").strip()
        if value and value not in titles:
            titles.append(value)
    return titles[:limit]


def marker_visible(driver, res_id):
    if not res_id:
        return None
    return first_displayed(driver, by_id(res_id)) is not None


def icon_selected(driver, icon_id):
    '''顶部 icon 自身也有选中态(MainActivity.setCurrentItem 里设置的)'''
    element = first_displayed(driver, by_id(icon_id))
    if element is None:
        return None
    try:
        return element.get_attribute("selected") == "true"
    except Exception:
        return None


def check_sub_tabs(driver, top_tab):
    print("--- %s (%s) ---" % (top_tab["name"], top_tab["icon"]))
    click_element(driver, by_id(top_tab["icon"]), 10, "顶部 icon %s" % top_tab["name"])
    time.sleep(2)
    print("  顶部 icon 选中状态:", icon_selected(driver, top_tab["icon"]))

    subs = top_tab["subs"]
    if subs is None:
        subs = [(title, None) for title in read_tab_titles(driver)]
        if subs:
            print("  动态读取到二级 tab:", " / ".join(title for title, _ in subs))
        else:
            print("  动态读取二级 tab 失败(可能是网络问题)")
            record(top_tab["name"], "(tab名未读取到)", "FAIL", "GET /tree/json 没返回或 TabLayout 为空")
            return

    for title, marker in subs:
        if not click_sub_tab(driver, title):
            record(top_tab["name"], title, "FAIL", "点不到(已尝试左滑 tab 栏)")
            continue
        time.sleep(1.5)
        selected = tab_selected(driver, title)
        detail = "selected=%s" % selected
        if marker:
            detail += ", %s displayed=%s" % (marker, marker_visible(driver, marker))
        record(top_tab["name"], title, "OK" if selected else "WARN", detail)


def print_summary(strict=False):
    total = len(RESULTS)
    failed = [item for item in RESULTS if item[2] == "FAIL"]
    warned = [item for item in RESULTS if item[2] == "WARN"]
    print("\n========== 二级菜单覆盖汇总 ==========")
    for icon, tab, status, detail in RESULTS:
        print("[%s] %-18s %s" % (status, icon, tab))
    print("覆盖 %d 个二级 tab: OK %d, WARN %d, FAIL %d"
          % (total, total - len(failed) - len(warned), len(warned), len(failed)))
    if failed:
        print("点不到的: " + ", ".join(tab for _, tab, status, _ in failed if status == "FAIL"))
    return 1 if (failed or (strict and warned)) else 0


def main():
    parser = build_parser("CloudReader 二级菜单(tab)切换测试")
    parser.add_argument("--tops", default="1,2,3", help="要测试的顶部 icon, 逗号分隔(1=玩安卓 2=发现 3=项目)")
    parser.add_argument("--strict", action="store_true", help="WARN(点了但没确认到)也算失败")
    args = parser.parse_args()

    wanted = {item.strip() for item in args.tops.split(",") if item.strip()}
    driver = start_driver(args.device, args.appium)
    try:
        dismiss_startup_dialogs(driver)
        print("已进入主界面:", wait_main_page(driver))
        for top_tab in TOP_TABS:
            if top_tab["key"] in wanted:
                check_sub_tabs(driver, top_tab)
        click_element(driver, by_id("iv_title_one"), 10, "回到第一个 icon")
        print("=== 二级菜单切换测试结束 ===")
        return print_summary(args.strict)
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())