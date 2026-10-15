# -*- coding: utf-8 -*-
'''
CloudReader 搜索查询脚本 (Appium + UiAutomator2)

对应接口:
  GET  /hotkey/json                 热门搜索词
  POST /article/query/{page}/json   搜索文章, 表单字段 k

流程:
  启动App -> 主界面工具栏 [搜索] -> 读取热门搜索标签 -> 输入关键词并回车
  -> 等待结果列表 -> 打印前 N 条标题 -> 打开第一条进入详情 -> 返回主界面

用法:
  python search_cloudreader.py -k Android -n 5
  python search_cloudreader.py -k "Kotlin" -d emulator-5556
'''

import time

from appium.webdriver.common.appiumby import AppiumBy

from cloudreader_common import (
    build_parser,
    by_desc,
    by_id,
    child_texts,
    click_any,
    click_element,
    dismiss_startup_dialogs,
    find_all_texts,
    start_driver,
    wait_activity,
    wait_main_page,
    wait_visible,
)

RESULT_TITLE = "tv_title"        # item_category_article.xml 里的标题
HOT_TAG_LAYOUT = "tfl_search"    # activity_search.xml 里的 "热门搜索" FlowLayout

# 工具栏搜索入口: res/menu/main.xml -> action_search, 标题即 content-desc
SEARCH_ENTRY = [
    by_desc("搜索"),
    (AppiumBy.XPATH, "//*[@content-desc='搜索']"),
    (AppiumBy.XPATH, "//android.widget.ImageView[@content-desc='搜索']"),
]


def main():
    parser = build_parser("CloudReader 搜索查询脚本")
    parser.add_argument("-k", "--keyword", default="Android", help="搜索关键词")
    parser.add_argument("-n", "--limit", type=int, default=5, help="读取结果条数")
    args = parser.parse_args()

    driver = start_driver(args.device, args.appium)
    try:
        dismiss_startup_dialogs(driver)
        print("已进入主界面:", wait_main_page(driver))

        if click_any(driver, SEARCH_ENTRY, 10, "工具栏[搜索]") is None:
            raise RuntimeError("没有找到工具栏的搜索按钮")
        if wait_activity(driver, "SearchActivity", 10) is None:
            raise RuntimeError("点击后未进入搜索页, 当前页面: %s" % driver.current_activity)
        print("已进入搜索页:", driver.current_activity)

        tags = child_texts(driver, by_id(HOT_TAG_LAYOUT), limit=8)
        print("热门搜索:", " / ".join(tags) if tags else "(未加载, 可能是网络问题)")

        keyword_input = wait_visible(driver, by_id("et_content"))
        keyword_input.click()
        keyword_input.send_keys(args.keyword)
        print("已输入关键词:", args.keyword)
        driver.press_keycode(66)        # KEYCODE_ENTER -> IME_ACTION_SEARCH
        try:
            driver.hide_keyboard()
        except Exception:
            pass

        wait_visible(driver, by_id("recyclerView"), 20)
        time.sleep(2)
        titles = find_all_texts(driver, by_id(RESULT_TITLE), limit=args.limit)
        if not titles:
            print("=== 没有搜索到结果, 关键词:", args.keyword, "===")
            return
        print("搜索结果 %d 条:" % len(titles))
        for index, title in enumerate(titles, 1):
            print("  %d. %s" % (index, title))

        click_element(driver, by_id(RESULT_TITLE), 10, "第一条结果")
        if wait_activity(driver, "WebViewActivity", 15) is None:
            print("点击后当前页面:", driver.current_activity, "(详情页未打开)")
        else:
            print("已打开详情页:", driver.current_activity)
            print("  页面标题:", wait_visible(driver, by_id("tv_gun_title"), 10).text)

        driver.back()                          # 详情 -> 搜索结果
        wait_activity(driver, "SearchActivity", 10)
        driver.back()                          # 搜索结果 -> 搜索标签页(SearchActivity.onBackPressed)
        time.sleep(1)
        if "SearchActivity" in (driver.current_activity or ""):
            driver.back()                      # 搜索页 -> 主界面
        print("=== 查询流程结束, 当前页面:", wait_activity(driver, "MainActivity", 10), "===")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
