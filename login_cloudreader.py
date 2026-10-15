# -*- coding: utf-8 -*-
'''
CloudReader 登录 / 退出脚本 (Appium + UiAutomator2)

对应 App 内走的接口:
  POST /user/login         登录: 登录页 activity_login.xml -> [登陆]
  GET  /user/logout/json   退出: 侧滑菜单 -> 账号登录 -> 退出玩安卓（用户名）

流程:
  启动App -> 侧滑菜单看头部用户名(已登录则先退出)
  -> 点头部 "玩安卓登录" 进入登录页 -> 填写账号密码 -> 点击 [登陆]
  -> 回到主界面, 核对侧滑菜单头部用户名 / 积分等级

用法:
  python login_cloudreader.py                   # 先退出再登录, 可反复执行
  python login_cloudreader.py --logout-only     # 只做退出
  python login_cloudreader.py -u test00300 -p 123456 -d emulator-5556
'''

import time

from cloudreader_common import (
    LOGIN_PLACEHOLDER,
    build_parser,
    by_id,
    by_text,
    click_button,
    click_element,
    dismiss_startup_dialogs,
    drawer_username,
    fill_login_form,
    open_drawer,
    start_driver,
    toast_text,
    wait_activity,
    wait_activity_gone,
    wait_main_page,
)


def logout(driver):
    '''侧滑菜单 -> 账号登录 -> 退出玩安卓（用户名）'''
    username = drawer_username(driver)
    if username == LOGIN_PLACEHOLDER:
        print("当前未登录, 跳过退出")
        return True

    click_element(driver, by_id("ll_nav_login"), 10, "账号登录")
    option = "退出玩安卓（%s）" % username
    click_element(driver, by_text(option), 10, option)

    for _ in range(10):
        time.sleep(1)
        if drawer_username(driver) == LOGIN_PLACEHOLDER:
            print("已退出玩安卓账号")
            return True
    print("退出未确认, 头部用户名仍是:", drawer_username(driver))
    return False


def goto_login_page(driver):
    '''侧滑菜单 -> 头部 "玩安卓登录"; 未登录时会直接进入 LoginActivity'''
    open_drawer(driver)
    click_element(driver, by_id("ll_info"), 10, "头部[玩安卓登录]")

    activity = driver.current_activity or ""
    if "MyCoinActivity" in activity:
        raise RuntimeError("当前仍是登录状态(点头部进入了积分页), 请先执行退出")
    if wait_activity(driver, "LoginActivity", 10) is None:
        raise RuntimeError("点击登录入口后未进入登录页, 当前页面: %s" % activity)
    print("已进入登录页:", driver.current_activity)


def login(driver, username, password):
    '''填写账号密码并点击 [登陆], 返回是否成功离开登录页'''
    fill_login_form(driver, username, password)
    click_button(driver, "登陆")
    print("已点击 [登陆], 等待服务端返回...")

    if wait_activity_gone(driver, "LoginActivity", 20) is None:
        print("=== 登录失败, 仍停留在登录页 ===")
        message = toast_text(driver, 5)
        print("服务端提示:", message if message else "(未捕获到Toast, 请手动截图确认)")
        return False

    print("已回到:", driver.current_activity)
    return True


def verify_header(driver, username):
    '''登录成功后会请求 /lg/coin/userinfo/json 刷新侧滑菜单头部'''
    for _ in range(10):
        time.sleep(1)
        current = drawer_username(driver)
        if current == username:
            print("=== 登录成功: 头部用户名 =", current, "===")
            return True
    print("=== 已离开登录页, 但头部用户名仍为:", drawer_username(driver), "===")
    return False


def main():
    parser = build_parser("CloudReader 登录/退出脚本")
    parser.add_argument("--logout-only", action="store_true", help="只做退出, 不登录")
    args = parser.parse_args()
    driver = start_driver(args.device, args.appium)
    try:
        print("等待应用加载...")
        dismiss_startup_dialogs(driver)
        print("已进入主界面:", wait_main_page(driver))

        logout(driver)
        if args.logout_only:
            print("=== 仅退出模式, 结束 ===")
            return

        goto_login_page(driver)
        if login(driver, args.username, args.password):
            verify_header(driver, args.username)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
