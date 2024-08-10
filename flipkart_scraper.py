import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from urllib.parse import urljoin

logger = logging.getLogger('Flipkart')

def search(keywords, num_products=30):
    all_data = fetch_flipkart_data(keywords, num_products)
    products = process_flipkart_data(all_data, num_products)
    if not products:
        error_msg = f"No products found for '{keywords}'"
        logger.error(error_msg)
        raise Exception(error_msg)
    return products

def fetch_flipkart_data(keyword, num_products):
    all_data = []
    url = f"https://www.flipkart.com/search?q={keyword.replace(' ', '+')}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=off&as=off"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    page = 1
    while len(all_data) * 24 < num_products:  # Assuming 24 products per page
        try:
            logger.info(f"Fetching page {page} for '{keyword}'")
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "lxml")
                all_data.append(soup)
                
                next_page = soup.find("a", class_="_9QVEpD")
                if next_page and "href" in next_page.attrs:
                    url = urljoin("https://www.flipkart.com", next_page["href"])
                    page += 1
                    time.sleep(random.uniform(2, 5))
                else:
                    logger.info(f"No more pages found for '{keyword}'")
                    break
            else:
                logger.error(f"Failed to retrieve page {page} for '{keyword}'. Status code: {response.status_code}")
                break
        except requests.RequestException as e:
            logger.error(f"An error occurred while fetching results for '{keyword}' on page {page}: {e}")
            break

    return all_data

def process_flipkart_data(all_data, num_products=30):
    products = []
    for soup in all_data:
        product_containers = soup.find_all("div", attrs={"data-id": True})
        
        for container in product_containers:
            if len(products) >= num_products:
                break

            product_id = container['data-id']
            name_elem = container.find("a", class_="wjcEIp")
            if not name_elem:
                name_elem = container.find("div", class_="KzDlHZ")
            price_elem = container.find("div", class_="Nx9bqj")
            
            name = name_elem.get_text(strip=True) if name_elem else "N/A"
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            
            products.append({
                "rank": len(products) + 1,
                "product_id": product_id,
                "title": name,
                "price": price
            })

        if len(products) >= num_products:
            break

    logger.info(f"Processed {len(products)} products")
    return products[:num_products]
