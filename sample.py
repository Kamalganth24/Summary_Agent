from playwright.sync_api import sync_playwright
import re

def extract_section_api(url, section):
    captured_response = []
    captured_mode = {"active" : False}


    def handle_response(response):
        if not captured_mode["active"]:
            return
        
        api_url = response.url


        if "_next/data" in api_url:           # swap "_next/data with /api/ for rest , /graphql for GraphQL.
            try:
                data = response.json()
                captured_response.append({
                    "url": api_url,
                    "data":data
                })
                print(f"Captured API for section : {section}")
                print("Url : ", api_url)

            except:
                pass  #ignore non json
        
    with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            page.on("response", handle_response)

            page.goto(url)


            try:
                page.click("button.gfg_loginModalBtn")
                page.wait_for_timeout(2000)
            except:
                print("Login button not found")



            try:

                page.wait_for_selector('input[placeholder="Username or Email"]', timeout=3000)

                page.fill('input[placeholder="Username or Email"]', "kamalhashagile@gmail.com")
                page.wait_for_timeout(20000)
                page.fill('input[type="password"]', "Kamalganth@2026")

                page.click('button:has-text("Sign In")')
                page.wait_for_timeout(30000)

            except:
                print("Login Failed ! ")



            try:
                page.wait_for_selector('a[href*="python-programming-language-tutorial"]', timeout=3000)
                page.click('a[href*="python-programming-language-tutorial"]')

                print("Navigated to python page!")

            except Exception as e:
                print(f"Python Navigation Failed: {e}")


            captured_mode["active"] = True

            try:
                page.locator(f"text={section}").first.click()
            except:
                print(f"could not Able to find the Section : {section}")
                browser.close()
                return None
    
            page.wait_for_timeout(4000)

            browser.close()

    if captured_response:
        return captured_response[0]
    else:
        print("No ApI Captured")
        return None
    

result = extract_section_api(
        url="https://www.geeksforgeeks.org/",
        section="Data Types"
    )

print(result)