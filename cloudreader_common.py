# -*- coding: utf-8 -*-
'''
CloudReader 自动化脚本公共模块 (Appium + UiAutomator2)

被这些脚本复用:
  login_cloudreader.py          登录 / 退出
  search_cloudreader.py         搜索查询
  switch_pages_cloudreader.py   页面切换

运行前提:
  1. Appium 已启动 (http://127.0.0.1:4723) 且已安装 uiautomator2 驱动
  2. 模拟器/真机已连接 (adb devices 里能看到 emulator-5556)
  3. Python 依赖: pip install Appium-Python-Client

所有资源 id 都来自 app/src/main/res/layout 下的同名布局文件。
'''

import argparse
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")   # 控制台中文输出
except Exception:
    pass

try:
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError as exc:
    raise SystemExit("缺少 Appium 依赖, 请先执行: pip install Appium-Python-Client\n原始错误: %s" % exc)


# ---------------- 常量 ----------------

APP_PACKAGE = "com.example.jingbin.cloudreader"
APP_ACTIVITY = ".ui.LoadingActivity"       # AndroidManifest 里的 MAIN / LAUNCHER
APPIUM_URL = "http://127.0.0.1:4723"
DEFAULT_DEVICE = "emulator-5556"

DEFAULT_USERNAME = "test00300"
DEFAULT_PASSWORD = "123456"

LOGIN_PLACEHOLDER = "玩安卓登录"             # nav_header_main.xml 中 tv_username 的默认文案


# ---------------- 命令行参数 ----------------

def build_parser(description):
    '''公共参数: 设备、账号、密码、Appium 地址, 脚本可继续 add_argument'''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-d", "--device", default=DEFAULT_DEVICE, help="设备名/udid, 默认 %s" % DEFAULT_DEVICE)
    parser.add_argument("-u", "--username", default=DEFAULT_USERNAME, help="玩安卓账号")
    parser.add_argument("-p", "--password", default=DEFAULT_PASSWORD, help="玩安卓密码")
    parser.add_argument("--appium", default=APPIUM_URL, help="Appium 服务地址")
    return parser


# ---------------- 驱动 ----------------

def start_driver(device_name=DEFAULT_DEVICE, appium_url=APPIUM_URL):
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = device_name
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.no_reset = True
    options.unicode_keyboard = True
    options.reset_keyboard = True
    return webdriver.Remote(appium_url, options=options)


# ---------------- 定位器 ----------------

def by_id(res_id):
    return AppiumBy.ID, "{0}:id/{1}".format(APP_PACKAGE, res_id)


def by_text(text, class_name="android.widget.TextView"):
    return AppiumBy.XPATH, "//{0}[@text='{1}']".format(class_name, text)


def by_desc(desc):
    return AppiumBy.ACCESSIBILITY_ID, desc


# ---------------- 元素操作 ----------------

def wait_visible(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))


def click_element(driver, locator, timeout=10, desc=None):
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    element.click()
    print("  已点击:", desc or locator[1])
    return element


def click_if_exists(driver, locator, timeout=3, desc=None):
    try:
        return click_element(driver, locator, timeout, desc)
    except Exception:
        return None


def click_any(driver, locators, timeout=8, desc=None):
    '''依次尝试多个定位器, 用于 content-desc 之类不确定的元素'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        for locator in locators:
            try:
                element = driver.find_element(*locator)
                if element.is_displayed():
                    element.click()
                    print("  已点击:", desc or locator[1])
                    return element
            except Exception:
                continue
        time.sleep(0.5)
    return None


def first_displayed(driver, locator):
    '''同一个 id 在多个 Fragment 中重复出现时, 取当前真正可见的那个'''
    for element in driver.find_elements(*locator):
        try:
            if element.is_displayed():
                return element
        except Exception:
            continue
    return None


def click_present(driver, locator, timeout=5, desc=None):
    '''只在元素确实可见时点击; 找不到返回 None(各版本菜单项有差异时用它跳过)'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        element = first_displayed(driver, locator)
        if element is not None:
            element.click()
            print("  已点击:", desc or locator[1])
            return element
        time.sleep(0.3)
    return None


def find_all_texts(driver, locator, limit=None):
    texts = []
    for element in driver.find_elements(*locator):
        value = (element.text or "").strip()
        if value:
            texts.append(value)
        if limit and len(texts) >= limit:
            break
    return texts


def child_texts(driver, locator, limit=8, timeout=5):
    '''读取容器内所有子元素文本, 例如热门搜索标签'''
    try:
        container = wait_visible(driver, locator, timeout)
    except Exception:
        return []
    texts = []
    for element in container.find_elements(AppiumBy.XPATH, ".//*[@text]"):
        value = (element.text or "").strip()
        if value and value not in texts:
            texts.append(value)
        if len(texts) >= limit:
            break
    return texts


# ---------------- Activity / Toast ----------------

def wait_activity(driver, name, timeout=15):
    '''等待当前 Activity 名字包含 name, 返回真实名称; 超时返回 None'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = driver.current_activity or ""
        if name in current:
            return current
        time.sleep(0.5)
    return None


def wait_activity_gone(driver, name, timeout=15):
    '''等待离开某个 Activity, 例如登录成功后 LoginActivity 会 finish'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = driver.current_activity or ""
        if name not in current:
            return current
        time.sleep(0.5)
    return None


def toast_text(driver, timeout=10):
    '''轮询捕获 Toast 文本, 用于注册/登录失败提示'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return driver.find_element(AppiumBy.XPATH, "//android.widget.Toast").text
        except Exception:
            time.sleep(0.4)
    return None


# ---------------- 启动 / 侧滑菜单 ----------------

def dismiss_startup_dialogs(driver, timeout=5):
    '''隐私协议、更新提示、系统权限弹窗'''
    time.sleep(2)
    click_if_exists(driver, by_id("tv_agree"), timeout, "同意隐私协议")
    click_if_exists(driver, (AppiumBy.XPATH, "//android.widget.Button[@text='取消']"), 2, "取消更新弹窗")
    for text in ("仅在使用中允许", "始终允许", "允许"):
        click_if_exists(driver, by_text(text, "android.widget.Button"), 1, text)


def wait_main_page(driver, timeout=20):
    '''等待主界面(顶部标题栏左侧菜单按钮出现)
    上一次脚本可能停在别的页面(例如"我的收藏"), 这里会先自己退回去或重新拉起 App'''
    deadline = time.time() + timeout
    while time.time() < deadline:
        if first_displayed(driver, by_id("iv_title_menu")) is not None:
            return driver.current_activity
        try:
            if APP_PACKAGE not in (driver.current_package or ""):
                driver.activate_app(APP_PACKAGE)          # App 不在前台, 重新拉起
            elif "MainActivity" not in (driver.current_activity or ""):
                driver.back()                             # 停在二级页面, 退回去
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("没能回到主界面, 当前页面: %s" % driver.current_activity)


def drawer_is_open(driver):
    '''侧滑菜单关闭时头部会被移到屏幕外, 用横坐标判断是否展开'''
    element = first_displayed(driver, by_id("tv_username"))
    if element is None:
        return False
    return element.rect.get("x", -1) >= 0


def open_drawer(driver, timeout=10):
    if drawer_is_open(driver):
        return
    click_element(driver, by_id("iv_title_menu"), timeout, "打开侧滑菜单")
    time.sleep(1)


def close_drawer(driver, timeout=5):
    if not drawer_is_open(driver):
        return
    driver.press_keycode(4)          # MainActivity.onKeyDown: 菜单打开时返回键只关菜单
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not drawer_is_open(driver):
            return
        time.sleep(0.3)


def drawer_username(driver, timeout=10):
    '''打开侧滑菜单并返回头部用户名; 未登录时是 "玩安卓登录"'''
    open_drawer(driver, timeout)
    return wait_visible(driver, by_id("tv_username"), timeout).text.strip()


def is_logged_in(driver):
    return drawer_username(driver) != LOGIN_PLACEHOLDER


# ---------------- 登录页 ----------------

def fill_login_form(driver, username, password, timeout=15):
    '''登录页 activity_login.xml: text_email / password'''
    wait_visible(driver, by_id("text_email"), timeout)
    username_input = driver.find_element(*by_id("text_email"))
    username_input.clear()
    username_input.send_keys(username)

    password_input = driver.find_element(*by_id("password"))
    password_input.clear()
    password_input.send_keys(password)

    try:
        driver.hide_keyboard()
    except Exception:
        driver.press_keycode(4)
    print("  已填写账号:", username)


def click_button(driver, text, timeout=10):
    '''登录页里的 [注册] / [登陆] 按钮'''
    locator = (AppiumBy.XPATH, "//android.widget.Button[@text='{0}']".format(text))
    return click_element(driver, locator, timeout, "按钮[%s]" % text)
