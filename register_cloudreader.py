# -*- coding: utf-8 -*-
'''
CloudReader App 注册脚本 (Appium + UiAutomator2)

账号: test00300 / 密码: 123456
流程: 启动App -> 打开侧滑菜单 -> 点击头部"玩安卓登录" -> 填写用户名密码 -> 点击"注册"

运行前提:
  1. Appium 已启动 (http://127.0.0.1:4723) 且已安装 uiautomator2 驱动
  2. 模拟器已连接 (adb devices 里能看到 emulator-5556)
  3. CloudReader 已安装 (com.example.jingbin.cloudreader)
'''

import time

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

USERNAME = "test00300"
PASSWORD = "123456"
APP_PACKAGE = "com.example.jingbin.cloudreader"
APP_ACTIVITY = ".ui.LoadingActivity"

options = UiAutomator2Options()
options.platform_name = "Android"
options.device_name = "emulator-5556"
options.app_package = APP_PACKAGE
options.app_activity = APP_ACTIVITY
options.no_reset = True
options.unicode_keyboard = True
options.reset_keyboard = True

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
wait = WebDriverWait(driver, 20)


def by_id(res_id):
    return AppiumBy.ID, f"{APP_PACKAGE}:id/{res_id}"


def click_if_exists(locator, timeout=3):
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator)).click()
        print(f"  已点击: {locator[1]}")
        return True
    except Exception:
        return False


try:
    print("等待应用加载...")
    time.sleep(2)
    click_if_exists(by_id("tv_agree"))
    click_if_exists((AppiumBy.XPATH, "//android.widget.Button[@text='取消']"))

    wait.until(EC.presence_of_element_located(by_id("iv_title_menu")))
    print("已进入主界面:", driver.current_activity)

    driver.find_element(*by_id("iv_title_menu")).click()
    print("已打开侧滑菜单")
    time.sleep(1)

    if not click_if_exists(by_id("ll_info"), timeout=5):
        raise RuntimeError("未找到侧滑菜单登录入口 ll_info")
    time.sleep(1)

    activity = driver.current_activity
    if "MyCoinActivity" in activity:
        print("当前已经是登录状态(点头部进入了积分页)，无法直接注册。")
        print("请在App里: 侧滑菜单 -> 玩安卓登录 -> 退出玩安卓，然后重新运行本脚本。")
        raise SystemExit(0)
    if "LoginActivity" not in activity:
        raise RuntimeError(f"点击登录入口后未进入登录页，当前页面: {activity}")

    wait.until(EC.presence_of_element_located(by_id("text_email")))
    print("已进入登录页:", driver.current_activity)

    username_input = driver.find_element(*by_id("text_email"))
    username_input.clear()
    username_input.send_keys(USERNAME)

    password_input = driver.find_element(*by_id("password"))
    password_input.clear()
    password_input.send_keys(PASSWORD)
    print(f"已输入用户名: {USERNAME}")

    try:
        driver.hide_keyboard()
    except Exception:
        driver.press_keycode(4)

    register_btn = wait.until(
        EC.element_to_be_clickable((AppiumBy.XPATH, "//android.widget.Button[@text='注册']"))
    )
    register_btn.click()
    print("已点击 [注册]，等待服务端返回...")

    success = False
    toast_msg = None
    for _ in range(20):
        time.sleep(1)
        try:
            toast = driver.find_element(AppiumBy.XPATH, "//android.widget.Toast")
            toast_msg = toast.text
        except Exception:
            pass
        if "LoginActivity" not in driver.current_activity:
            success = True
            break

    if success:
        print("=== 注册成功！已回到:", driver.current_activity, "===")
    else:
        print("=== 注册未成功，仍停留在登录页 ===")
        print("服务端提示:", toast_msg if toast_msg else "(未捕获到Toast，请手动截图确认)")

finally:
    driver.quit()
