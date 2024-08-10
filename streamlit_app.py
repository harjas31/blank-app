import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Amazon')

def search(keywords, num_products=30):
    try:
        all_data = fetch_amazon_data(keywords, num_products)
        products = process_amazon_data(all_data, num_products)
        if not products:
            error_msg = f"No products found for '{keywords}'"
            logger.error(error_msg)
            raise Exception(error_msg)
        return products
    except Exception as e:
        error_msg = f"Error during Amazon search: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

def fetch_amazon_data(keyword, num_products):
    all_data = []
    url = f"https://www.amazon.in/s?k={keyword.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    page = 1
    while len(all_data) * 16 < num_products:  # Assuming 16 products per page
        try:
            logger.info(f"Fetching page {page} for '{keyword}'")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            all_data.append(soup)

            next_page = soup.find("a", class_="s-pagination-next")
            if next_page and "href" in next_page.attrs:
                url = "https://www.amazon.in" + next_page["href"]
                logger.info(f"Fetched page {page}, moving to next page...")
                page += 1
                time.sleep(random.uniform(2, 5))
            else:
                logger.info(f"No more pages found for '{keyword}'")
                break
        except requests.RequestException as e:
            logger.error(f"An error occurred while fetching results for '{keyword}' on page {page}: {e}")
            break

    return all_data

def process_amazon_data(all_data, num_products=30):
    products = []
    for soup in all_data:
        search_results = soup.find_all("div", {"data-component-type": "s-search-result"})

        for result in search_results:
            if len(products) >= num_products:
                break

            asin = result.get("data-asin")
            title_element = result.find("h2", class_="a-size-mini")
            title = title_element.text.strip() if title_element else "Title not found"
            
            price_element = result.find("span", class_="a-price-whole")
            if not price_element:
                price_element = result.find("span", class_="a-color-base")
            price = price_element.text.strip() if price_element else "n.a"

            products.append({
                "rank": len(products) + 1,
                "asin": asin,
                "title": title,
                "price": price
            })

        if len(products) >= num_products:
            break

    logger.info(f"Processed {len(products)} products")
    return products[:num_products]

def main():
    st.title("Amazon Product Scraper")

    keyword = st.text_input("Enter a keyword to search on Amazon:")
    num_products = st.number_input("Number of products to fetch:", min_value=1, max_value=100, value=30)

    if st.button("Search"):
        if keyword:
            try:
                with st.spinner("Searching for products..."):
                    products = search(keyword, num_products)
                
                df = pd.DataFrame(products)
                st.write(df)

                csv = df.to_csv(index=False)
                csv_bytes = csv.encode()
                
                st.download_button(
                    label="Download CSV",
                    data=csv_bytes,
                    file_name=f"amazon_products_{keyword}.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("Please enter a keyword to search.")

if __name__ == "__main__":
    main()
