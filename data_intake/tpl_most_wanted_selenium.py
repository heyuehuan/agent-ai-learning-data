#!/usr/bin/env python3

import csv
import re
import time
import random
import logging
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeleniumTPSScraper:
    def __init__(self, headless=False):
        self.base_url = "https://www.tps.ca"
        self.most_wanted_url = "/organizational-chart/specialized-operations-command/detective-operations/investigative-services/homicide/most-wanted/"
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Chrome WebDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def wait_for_page_load(self, timeout=30):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                page_source = self.driver.page_source.lower()
                page_title = self.driver.title.lower()
                
                cloudflare_indicators = [
                    'cloudflare',
                    'checking your browser',
                    'please wait',
                    'security check',
                    'ddos protection',
                    'just a moment'
                ]
                
                if any(indicator in page_source or indicator in page_title for indicator in cloudflare_indicators):
                    logger.info("Detected Cloudflare challenge, waiting...")
                    time.sleep(2)
                    continue
                else:
                    break
            
            time.sleep(random.uniform(2, 4))
            logger.info("Page load completed")
            return True
            
        except TimeoutException:
            logger.warning(f"Page load timeout after {timeout} seconds")
            return False
    
    def get_suspects_from_main_page(self):
        url = self.base_url + self.most_wanted_url
        logger.info(f"Navigating to: {url}")
        
        try:
            self.driver.get(url)
            self.wait_for_page_load()
            
            page_title = self.driver.title
            current_url = self.driver.current_url
            logger.info(f"Page loaded - Title: '{page_title}', URL: {current_url}")
            
            if "403" in page_title or "Forbidden" in self.driver.page_source:
                logger.error("Page access forbidden")
                return []
            
            if "404" in page_title or "Not Found" in page_title:
                logger.error("Page not found")
                return []
            
            page_source = self.driver.page_source
            if "cloudflare" in page_source.lower() or "checking your browser" in page_source.lower():
                logger.warning("Detected Cloudflare challenge - waiting longer...")
                time.sleep(10)
                page_source = self.driver.page_source
            
            with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info("Page source saved to debug_page_source.html for inspection")
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            all_links = soup.find_all('a', href=True)
            suspect_patterns = [
                r'/organizational-chart/.*/homicide/suspect/\d+/',
                r'/homicide/suspect/\d+/',
                r'suspect/\d+/',
            ]
            
            suspects = []
            seen_links = set()
            
            for pattern in suspect_patterns:
                suspect_links = soup.find_all('a', href=re.compile(pattern))
                logger.info(f"Pattern '{pattern}' found {len(suspect_links)} links")
                
                for link in suspect_links:
                    href = link.get('href')
                    if href and href not in seen_links:
                        seen_links.add(href)
                        full_url = urljoin(self.base_url, href)
                        
                        name = link.get_text(strip=True)
                        if name and name != "Photo of" and len(name) > 2:
                            suspect_id_match = re.search(r'suspect/(\d+)/', href)
                            suspect_id = suspect_id_match.group(1) if suspect_id_match else 'unknown'
                            
                            suspects.append({
                                'name': name,
                                'link': full_url,
                                'suspect_id': suspect_id
                            })
                            logger.info(f"Found suspect: {name} (ID: {suspect_id})")
                
                if suspects:
                    break
            
            if not suspects:
                logger.warning("No suspects found with standard patterns, trying manual extraction...")
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if 'suspect' in href.lower() and len(text) > 5 and text not in seen_links:
                        skip_texts = ['photo of', 'homicide most wanted', 'suspect', 'placeholder']
                        if any(skip in text.lower() for skip in skip_texts):
                            continue
                            
                        seen_links.add(text)
                        full_url = urljoin(self.base_url, href)
                        suspect_id_match = re.search(r'suspect/(\d+)/', href)
                        suspect_id = suspect_id_match.group(1) if suspect_id_match else 'unknown'
                        
                        suspects.append({
                            'name': text,
                            'link': full_url,
                            'suspect_id': suspect_id
                        })
                        logger.info(f"Manual extraction found suspect: {text} (ID: {suspect_id})")
            
            logger.info(f"Total unique suspects found: {len(suspects)}")
            return suspects
            
        except Exception as e:
            logger.error(f"Error accessing main page: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def get_suspect_details(self, suspect_info):
        logger.info(f"Getting details for: {suspect_info['name']}")
        
        try:
            self.driver.get(suspect_info['link'])
            self.wait_for_page_load()
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            details = suspect_info.copy()
            text_content = soup.get_text()
            
            patterns = {
                'case_number': r'Case #:\s*([^\n]+)',
                'division': r'(\d+)\s+Division',
                'date_of_birth': r'Date of Birth:\s*([^\n]+)',
                'age': r'Age:\s*(\d+)',
                'gender': r'Gender:\s*([MF])',
                'homicide_case': r'Homicide #:\s*([^\n]+)'
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, text_content)
                if match:
                    details[field] = match.group(1).strip()
            
            photo_img = soup.find('img', src=re.compile(r'/media/homicide/suspect/'))
            if photo_img:
                details['photo_url'] = urljoin(self.base_url, photo_img['src'])
            
            details['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            details['source'] = 'selenium_scraper'
            
            time.sleep(random.uniform(2, 5))
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting details for {suspect_info['name']}: {e}")
            return suspect_info
    
    def save_to_csv(self, suspects_data, filename='tpl_most_wanted.csv'):
        if not suspects_data:
            logger.warning("No data to save")
            return None
        
        headers = [
            'name', 'suspect_id', 'link', 'homicide_case', 'case_number', 
            'division', 'date_of_birth', 'age', 'gender', 'photo_url', 
            'scraped_at', 'source'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for suspect in suspects_data:
                row = {header: suspect.get(header, '') for header in headers}
                writer.writerow(row)
        
        logger.info(f"Saved {len(suspects_data)} suspects to {filename}")
        return filename
    
    def run(self):
        """Main execution method"""
        if not self.setup_driver():
            return []
        
        try:
            logger.info("Starting Selenium scraping of TPS Most Wanted")
            
            # Get suspects from main page
            suspects = self.get_suspects_from_main_page()
            if not suspects:
                logger.warning("No suspects found on main page")
                logger.info("Check debug_page_source.html to see what was actually loaded")
                print("\n❌ No suspects found!")
                print("Possible reasons:")
                print("  • Website structure has changed")
                print("  • Cloudflare is still blocking access")
                print("  • Page didn't load completely")
                print("  • Check debug_page_source.html for the actual page content")
                return []
            
            logger.info(f"Found {len(suspects)} suspects, getting detailed information...")
            print(f"\n✅ Found {len(suspects)} suspects on the main page!")
            
            # Get detailed information for each suspect
            detailed_suspects = []
            successful_details = 0
            
            for i, suspect in enumerate(suspects, 1):
                logger.info(f"Processing {i}/{len(suspects)}: {suspect['name']}")
                print(f"Processing {i}/{len(suspects)}: {suspect['name']}")
                
                details = self.get_suspect_details(suspect)
                detailed_suspects.append(details)
                
                # Check if we got meaningful details
                if any(details.get(key) for key in ['case_number', 'age', 'gender', 'division']):
                    successful_details += 1
            
            # Save to CSV
            filename = self.save_to_csv(detailed_suspects)
            
            print(f"\n✅ Selenium scraping completed!")
            print(f"📊 Found {len(detailed_suspects)} suspects")
            print(f"� Got detailed info for {successful_details} suspects")
            print(f"�📄 Data saved to: {filename}")
            
            if successful_details < len(suspects) / 2:
                print("\n⚠️  Many suspects missing detailed information.")
                print("This might indicate the individual suspect pages are also protected.")
            
            return detailed_suspects
            
        except Exception as e:
            logger.error(f"Unexpected error in main execution: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"\n❌ Unexpected error: {e}")
            return []
            
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='TPS Most Wanted Selenium Scraper')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--test', action='store_true', help='Test WebDriver setup only')
    
    args = parser.parse_args()
    
    if args.test:
        scraper = SeleniumTPSScraper(headless=args.headless)
        if scraper.setup_driver():
            print("✅ WebDriver setup successful!")
            scraper.driver.quit()
        else:
            print("❌ WebDriver setup failed!")
        return
    
    scraper = SeleniumTPSScraper(headless=args.headless)
    
    try:
        suspects = scraper.run()
        if suspects:
            print(f"\n📋 Sample suspect data:")
            for key, value in list(suspects[0].items())[:5]:
                print(f"  {key}: {value}")
        else:
            print("\n❌ No data was collected")
            print("The website might still be blocking access or there could be technical issues.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Error occurred: {e}")

if __name__ == "__main__":
    main()
