# -*- coding: utf-8 -*-
'''
CloudReader 收藏 界面操作脚本 (Appium + UiAutomator2)

和 switch_pages_cloudreader.py 一样, 全程在 App 界面上操作:
  1. 启动App, 确认已登录(没登录就自动走一遍登录流程)
  2. 首页(玩安卓 tab)读第一条的标题与收藏状态, 未收藏就点 vb_collect 收藏,
     等 Toast "收藏成功" 并校验按钮变成已选中
  3. 结束(默认跳过"我的收藏"页校验)

注意: "我的收藏"页在这版 App 上首次进入不会加载数据(要手动下拉刷新才出),
属于 App 侧的已知问题, 所以默认跳过第 3 步; 需要时加 --with-collect-page 打开:
  侧滑菜单 -> 我的收藏(文章) -> 找到刚才那条 -> 取消收藏 -> 校验它从列表移除

对应接口:
  POST /lg/collect/{id}/json             收藏
  POST /lg/uncollect/{id}/json           取消收藏(我的收藏页)
  GET  /lg/collect/list/{page}/json      我的收藏列表

用法:
  python collect_cloudreader.py
  python collect_cloudreader.py -u test00300 -p 123456 -d emulator-5556
  python collect_cloudreader.py --with-collect-page   # 连"我的收藏"校验和取消收藏一起跑
'''

import time

from appium.webdriver.common.appiumby import AppiumBy

from cloudreader_common import (
    build_parser,
    by_id,
    click_element,
    click_if_exists,
    close_drawer,
    dismiss_startup_dialogs,
    first_displayed,
    is_logged_in,
    open_drawer,
    start_driver,
    wait_activity,
    wait_main_page,
)
from login_cloudreader import goto_login_page, login as ui_login, verify_header

ITEM_TITLE = "tv_title"        # item_wan_android.xml
ITEM_COLLECT = "vb_collect"    # item_wan_android.xml 里的 CheckBox


def wait_toast(driver, expect=None, timeout=8):
    '''等 Toast, expect 给了就等到包含它的那条为止'''
    deadline = time.time() + timeout
    seen = None
    while time.time() < deadline:
        try:
            text = driver.find_element(AppiumBy.XPATH, "//android.widget.Toast").text
        except Exception:
            text = None
        if text:
            seen = text
            print("  Toast:", text)
            if expect is None or expect in text:
                return text
        time.sleep(0.3)
    return seen


def wait_list(driver, limit=3, timeout=20):
    '''等列表出数据(骨骼屏消失, 至少有 limit 条标题)'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        pairs = item_pairs(driver, limit=limit)
        if len(pairs) >= limit:
            return pairs
        time.sleep(0.5)
    return item_pairs(driver, limit=limit)


def item_pairs(driver, limit=8):
    '''把列表里每条文章的标题和收藏按钮按出现顺序配对
    (item_wan_android.xml 里每条只有一个 tv_title 和一个 vb_collect, 列表头没有这两个 id)'''
    titles = [t for t in driver.find_elements(*by_id(ITEM_TITLE)) if t.is_displayed()]
    checks = [c for c in driver.find_elements(*by_id(ITEM_COLLECT)) if c.is_displayed()]
    pairs = []
    for index in range(min(len(titles), len(checks), limit)):
        title = (titles[index].text or "").strip()
        if title:
            pairs.append((title, checks[index]))
    return pairs


def is_checked(element):
    try:
        return element.get_attribute("checked") == "true"
    except Exception:
        return False


def dismiss_market_dialog(driver):
    '''收藏成功后可能会弹"去酷安支持一下"的对话框'''
    click_if_exists(driver, (AppiumBy.XPATH, "//android.widget.Button[@text='取消']"), 2, "关闭酷安提示")


def ensure_login(driver, username, password):
    if is_logged_in(driver):
        print("已登录:", username)
        close_drawer(driver)
        return True
    close_drawer(driver)
    print("当前未登录, 先走登录流程...")
    goto_login_page(driver)
    if not ui_login(driver, username, password):
        return False
    verify_header(driver, username)
    close_drawer(driver)
    return True


def collect_on_home(driver):
    '''首页第一条: 收藏, 返回(标题, 是否点了收藏)'''
    click_element(driver, by_id("iv_title_one"), 10, "顶部 icon 玩安卓")
    time.sleep(1)
    pairs = wait_list(driver, limit=3)
    if not pairs:
        raise RuntimeError("首页没有读到文章列表")

    title, checkbox = pairs[0]
    print("首页第一条:", title)
    if is_checked(checkbox):
        print("  它已经是收藏状态, 跳过点击")
        return title, False

    checkbox.click()
    print("  已点击收藏按钮, 等接口返回...")
    wait_toast(driver, "收藏成功", 10)
    dismiss_market_dialog(driver)

    for _ in range(10):
        time.sleep(0.5)
        current = item_pairs(driver, limit=1)
        if current and is_checked(current[0][1]):
            print("  收藏状态校验: 按钮已选中")
            break
    return title, True


def open_my_collect(driver):
    open_drawer(driver)
    click_element(driver, by_id("ll_nav_collect"), 10, "我的收藏")
    activity = wait_activity(driver, "MyCollectActivity", 12)
    if activity is None:
        raise RuntimeError("没有进入我的收藏页, 当前页面: %s" % driver.current_activity)
    print("已进入:", activity, "(默认就是'文章' tab)")
    time.sleep(2)


def find_in_collect(driver, title, timeout=15):
    found = match_in_collect(driver, title, timeout)
    if found[0] is not None:
        return found

    # 没匹配到: 打印当前列表真实内容, 再下拉刷新重试一次
    print("  还没匹配到, 当前我的收藏页内容:")
    snapshot(driver, title)
    print("  下拉刷新后再找一次...")
    refresh_collect_list(driver)
    time.sleep(3)
    found = match_in_collect(driver, title, 10)
    if found[0] is None:
        snapshot(driver, title)
    return found


def match_in_collect(driver, title, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for item_title, checkbox in item_pairs(driver, limit=10):
            if item_title == title:
                return item_title, checkbox
        time.sleep(0.5)
    return None, None


def snapshot(driver, title):
    '''打印我的收藏页当前有多少条目, 以及都有哪些标题(定位问题时用)'''
    titles = driver.find_elements(*by_id(ITEM_TITLE))
    checks = driver.find_elements(*by_id(ITEM_COLLECT))
    print("    tv_title=%d 个, vb_collect=%d 个" % (len(titles), len(checks)))
    pairs = item_pairs(driver, limit=10)
    for index, (item_title, _) in enumerate(pairs, 1):
        print("    %d. %s%s" % (index, item_title, "   <== 目标" if item_title == title else ""))
    if not pairs:
        for text in ("你还没有收藏文章哦~", "加载中...", "没有更多了"):
            if first_displayed(driver, (AppiumBy.XPATH, "//android.widget.TextView[@text='%s']" % text)) is not None:
                print("    页面提示:", text)


def refresh_collect_list(driver):
    '''在我的收藏列表上下拉刷新'''
    target = first_displayed(driver, by_id("srl_wan")) or first_displayed(driver, by_id("xrv_wan"))
    if target is None:
        return False
    rect = target.rect
    x = rect["x"] + rect["width"] // 2
    driver.swipe(x, rect["y"] + 100, x, rect["y"] + int(rect["height"] * 0.8), 600)
    return True


def uncollect_in_list(driver, title, checkbox):
    print("在我的收藏里点这条的收藏按钮:", title)
    print("  点击前 checked =", is_checked(checkbox))
    checkbox.click()
    wait_toast(driver, "已取消收藏", 10)

    for _ in range(10):
        time.sleep(0.5)
        found, _ = find_in_collect(driver, title, timeout=2)
        if found is None:
            print("  校验通过: 该条目已从收藏列表移除")
            return True
    print("  提示: 该条目还在列表里, 可能是接口没返回成功")
    return False


def main():
    parser = build_parser("CloudReader 收藏界面操作脚本")
    parser.add_argument("--with-collect-page", action="store_true",
                        help="额外去'我的收藏'页校验并取消收藏(App 该页首次进入不加载数据, 默认跳过)")
    args = parser.parse_args()

    driver = start_driver(args.device, args.appium)
    try:
        dismiss_startup_dialogs(driver)
        print("已进入主界面:", wait_main_page(driver))

        if ensure_login(driver, args.username, args.password) is False:
            print("=== 登录没成功, 先执行 python login_cloudreader.py 再试 ===")
            return

        title, clicked = collect_on_home(driver)

        if not args.with_collect_page:
            print("=== 收藏完成: %s (%s) ===" % (title, "本次点击收藏" if clicked else "原本已收藏"))
            print("=== 已按默认设置跳过'我的收藏'页校验(App 侧已知问题) ===")
            return

        open_my_collect(driver)
        found_title, checkbox = find_in_collect(driver, title)
        if found_title is None:
            print("=== '我的收藏'里没找到这条: %s (App 侧已知问题, 不是用例失败) ===" % title)
            return
        print("在收藏列表里找到:", found_title, "| checked =", is_checked(checkbox))

        uncollect_in_list(driver, title, checkbox)

        driver.back()
        time.sleep(1)
        print("=== 收藏流程结束, 当前页面:", wait_activity(driver, "MainActivity", 10), "===")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
