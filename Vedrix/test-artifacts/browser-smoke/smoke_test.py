"""
Vedrix Frontend Browser Smoke Test
====================================
Tests key pages, navigation, responsiveness, and console health.

Run from project root:
    python Vedrix/test-artifacts/browser-smoke/smoke_test.py

Requires:
  - Frontend dev server running at http://localhost:5173
  - Backend dev server running at http://localhost:8000
  - pip install playwright && playwright install chromium
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5173"
ARTIFACTS_DIR = Path(__file__).parent
REPORT_PATH = ARTIFACTS_DIR / "report.json"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}

PASSED = 0
FAILED = 0
RESULTS = []
CONSOLE_LOGS = []
NETWORK_REQUESTS = []

SEP = "=" * 70


def check(label: str, ok: bool):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  [PASS] {label}")
    else:
        FAILED += 1
        print(f"  [FAIL] {label}")
    return ok


def take_screenshot(page, name: str):
    path = ARTIFACTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def capture_console(page, route: str):
    def _handler(msg):
        CONSOLE_LOGS.append({
            "type": msg.type,
            "text": msg.text,
            "url": page.url,
            "route": route,
        })
    page.on("console", _handler)


def capture_network(page, route: str):
    def _handler(request):
        failure = request.failure
        if failure is not None:
            NETWORK_REQUESTS.append({
                "url": request.url,
                "failure": failure.error_text if hasattr(failure, 'error_text') else str(failure),
                "route": route,
            })
    page.on("requestfailed", _handler)


def run_smoke_test():
    print(f"\n{SEP}")
    print("  VEDRIX FRONTEND BROWSER SMOKE TEST")
    print(f"  Started: {datetime.now().isoformat()}")
    print(SEP)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORTS["desktop"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        # TEST 1: Landing Page (Desktop)
        print("\n-- Landing Page (Desktop) --")
        page = context.new_page()
        capture_console(page, "landing")
        capture_network(page, "landing")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)

        title = page.title()
        check("Page title contains 'Vedrix'", "Vedrix" in title)
        body_text = page.locator("body").inner_text()
        check("Hero heading visible", any(t in body_text for t in ["Smarter Interviews", "AI-POWERED", "AI Interview"]))
        check("Navbar present", page.locator("nav").first.is_visible())
        screenshot = take_screenshot(page, "landing_1440x900")
        RESULTS.append({"route": "landing", "path": "/", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": title}})
        page.close()

        # TEST 2: Login Page (Desktop)
        print("\n-- Login Page (Desktop) --")
        page = context.new_page()
        capture_console(page, "login")
        capture_network(page, "login")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Login page loads without error", "Vedrix" in title)
        body = page.locator("body").inner_text().lower()
        has_login_form = any(t in body for t in ["sign in", "username", "password", "welcome back"])
        check("Login form present", has_login_form)
        username_field = page.locator('input[type="text"], input[name="username"], input[placeholder*="username" i], input[placeholder*="email" i]')
        password_field = page.locator('input[type="password"], input[name="password"]')
        check("Username field exists", username_field.count() > 0)
        check("Password field exists", password_field.count() > 0)
        screenshot = take_screenshot(page, "login_1440x900")
        RESULTS.append({"route": "login", "path": "/login", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": title, "login_form_present": has_login_form}})
        page.close()

        # TEST 3: Register Page (Desktop)
        print("\n-- Register Page (Desktop) --")
        page = context.new_page()
        capture_console(page, "register")
        capture_network(page, "register")
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Register page loads without error", "Vedrix" in title)
        body = page.locator("body").inner_text().lower()
        has_register_content = any(t in body for t in ["step 1 of 3", "how will you use", "student", "recruiter", "create an account"])
        check("Registration wizard visible", has_register_content)
        screenshot = take_screenshot(page, "register_1440x900")
        RESULTS.append({"route": "register", "path": "/register", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": title, "register_content_present": has_register_content}})
        page.close()

        # TEST 4: Interview Page (Desktop)
        print("\n-- Interview Page (Desktop) --")
        page = context.new_page()
        capture_console(page, "interview")
        capture_network(page, "interview")
        page.goto(f"{BASE_URL}/interview", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Interview page loads", "Vedrix" in title or "Interview" in title)
        body = page.locator("body").inner_text().lower()
        has_interview_content = any(t in body for t in ["validation", "microphone", "camera", "proctor", "check"])
        check("Interview/Proctor page content visible", has_interview_content)
        screenshot = take_screenshot(page, "interview_1440x900")
        RESULTS.append({"route": "interview", "path": "/interview", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": title, "interview_content": has_interview_content}})
        page.close()

        # TEST 5: Dashboard Redirect (unauthenticated)
        print("\n-- Dashboard Redirect (unauthenticated) --")
        page = context.new_page()
        capture_console(page, "dashboard_redirect")
        capture_network(page, "dashboard_redirect")
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        redirected_to_login = "/login" in page.url
        check("Redirects to login when unauthenticated", redirected_to_login)
        check("Login page shows after redirect", "Vedrix" in page.title())
        screenshot = take_screenshot(page, "dashboard_redirect_1440x900")
        RESULTS.append({"route": "dashboard_redirect", "path": "/dashboard", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": page.title(), "redirected_to": page.url}})
        page.close()

        # TEST 6: HR Dashboard Redirect (unauthenticated)
        print("\n-- HR Dashboard Redirect (unauthenticated) --")
        page = context.new_page()
        capture_console(page, "hr_redirect")
        capture_network(page, "hr_redirect")
        page.goto(f"{BASE_URL}/hr", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        redirected_to_login = "/login" in page.url
        check("HR page redirects to login", redirected_to_login)
        screenshot = take_screenshot(page, "hr_redirect_1440x900")
        RESULTS.append({"route": "hr_redirect", "path": "/hr", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": page.title(), "redirected_to": page.url}})
        page.close()

        # TEST 7: Admin Dashboard Redirect (unauthenticated)
        print("\n-- Admin Dashboard Redirect (unauthenticated) --")
        page = context.new_page()
        capture_console(page, "admin_redirect")
        capture_network(page, "admin_redirect")
        page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        redirected_to_login = "/login" in page.url
        check("Admin page redirects to login", redirected_to_login)
        screenshot = take_screenshot(page, "admin_redirect_1440x900")
        RESULTS.append({"route": "admin_redirect", "path": "/admin", "viewport": "1440x900", "mobile": False, "screenshot": screenshot, "layout": {"title": page.title(), "redirected_to": page.url}})
        page.close()

        # TEST 8: Navigation Flow (Desktop)
        print("\n-- Navigation Flow (Desktop) --")
        page = context.new_page()
        capture_console(page, "navigation")
        capture_network(page, "navigation")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        nav_links = page.locator("nav a, a[href*='login'], a[href*='register']")
        nav_hrefs = [link.get_attribute("href") for link in nav_links.all() if link.get_attribute("href")]
        has_login_link = any("/login" in (h or "") for h in nav_hrefs)
        check("Login link in navigation", has_login_link)
        target_link = None
        for h in nav_hrefs:
            if h and h != "#" and h != "/":
                target_link = h
                break
        if target_link:
            page.goto(f"{BASE_URL}{target_link}", wait_until="networkidle")
            page.wait_for_selector("body", timeout=5000)
            check(f"Navigated to {target_link} without error", "Vedrix" in page.title())
        else:
            check("Navigation link available to click", False)
        take_screenshot(page, "nav_flow_1440x900")
        page.close()

        # TEST 9: Mobile - Landing Page
        print("\n-- Mobile: Landing Page (390x844) --")
        mobile_context = browser.new_context(
            viewport=VIEWPORTS["mobile"],
            user_agent="Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
        )
        page = mobile_context.new_page()
        capture_console(page, "landing_mobile")
        capture_network(page, "landing_mobile")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Mobile landing loads", "Vedrix" in title)
        mobile_menu = page.locator('button:has(svg), button.lg\\:hidden, button:has(.lucide-menu)')
        check("Mobile menu button present", mobile_menu.count() > 0)
        screenshot = take_screenshot(page, "landing_mobile_390x844")
        RESULTS.append({"route": "landing_mobile", "path": "/", "viewport": "390x844", "mobile": True, "screenshot": screenshot, "layout": {"title": title, "mobile_menu_button": mobile_menu.count() > 0}})
        page.close()

        # TEST 10: Mobile - Login Page
        print("\n-- Mobile: Login Page (390x844) --")
        page = mobile_context.new_page()
        capture_console(page, "login_mobile")
        capture_network(page, "login_mobile")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Mobile login loads", "Vedrix" in title)
        body = page.locator("body").inner_text().lower()
        check("Mobile login form visible", "sign in" in body or "welcome back" in body)
        screenshot = take_screenshot(page, "login_mobile_390x844")
        RESULTS.append({"route": "login_mobile", "path": "/login", "viewport": "390x844", "mobile": True, "screenshot": screenshot, "layout": {"title": title}})
        page.close()

        # TEST 11: Mobile - Register Page
        print("\n-- Mobile: Register Page (390x844) --")
        page = mobile_context.new_page()
        capture_console(page, "register_mobile")
        capture_network(page, "register_mobile")
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Mobile register loads", "Vedrix" in title)
        body = page.locator("body").inner_text().lower()
        check("Mobile register wizard visible", "step 1 of 3" in body or "how will you use" in body)
        screenshot = take_screenshot(page, "register_mobile_390x844")
        RESULTS.append({"route": "register_mobile", "path": "/register", "viewport": "390x844", "mobile": True, "screenshot": screenshot, "layout": {"title": title}})
        page.close()

        # TEST 12: Mobile - Interview Page
        print("\n-- Mobile: Interview Page (390x844) --")
        page = mobile_context.new_page()
        capture_console(page, "interview_mobile")
        capture_network(page, "interview_mobile")
        page.goto(f"{BASE_URL}/interview", wait_until="networkidle")
        page.wait_for_selector("body", timeout=5000)
        title = page.title()
        check("Mobile interview loads", "Vedrix" in title)
        body = page.locator("body").inner_text().lower()
        has_desktop_message = any(t in body for t in ["desktop required", "requires desktop", "mobile", "switch to desktop"])
        screenshot = take_screenshot(page, "interview_mobile_390x844")
        RESULTS.append({"route": "interview_mobile", "path": "/interview", "viewport": "390x844", "mobile": True, "screenshot": screenshot, "layout": {"title": title, "desktop_required_message": has_desktop_message}})
        page.close()
        mobile_context.close()

        # Console & Network Health Check
        print("\n-- Console & Network Health --")
        console_errors = [
            log for log in CONSOLE_LOGS
            if log["type"] in ("error", "warning")
            and "React DevTools" not in log["text"]
            and "[vite]" not in log["text"]
        ]
        check("No console errors logged", len(console_errors) == 0)
        if console_errors:
            for err in console_errors:
                print(f"  WARN [{err['type']}] {err['text'][:100]}")

        check("No failed network requests", len(NETWORK_REQUESTS) == 0)
        if NETWORK_REQUESTS:
            for req in NETWORK_REQUESTS:
                print(f"  WARN Failed: {req['url']} - {req['failure']}")

        context.close()
        browser.close()

        # SUMMARY
        total = PASSED + FAILED
        print(f"\n{SEP}")
        print(f"  RESULTS: {PASSED}/{total} passed, {FAILED} failed")
        print(f"  Routes tested: {len(RESULTS)}")
        print(f"  Console logs captured: {len(CONSOLE_LOGS)}")
        print(f"  Network failures: {len(NETWORK_REQUESTS)}")
        print(SEP)

        report = {
            "base": BASE_URL,
            "artifacts": str(ARTIFACTS_DIR),
            "timestamp": datetime.now().isoformat(),
            "results": RESULTS,
            "console": CONSOLE_LOGS,
            "network": NETWORK_REQUESTS,
            "summary": {"passed": PASSED, "failed": FAILED, "total": total},
        }
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved to: {REPORT_PATH}")

        return PASSED, FAILED, total


if __name__ == "__main__":
    passed, failed, total = run_smoke_test()
    sys.exit(0 if failed == 0 else 1)
