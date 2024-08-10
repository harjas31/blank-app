import streamlit as st
import pandas as pd
import threading
import queue
import logging
from datetime import datetime
import os
import sys

# Placeholder imports - replace with actual scraper modules when implemented
import amazon_scraper
import flipkart_scraper
import utils

# Increase recursion limit
sys.setrecursionlimit(10000)

# Global stop_event
global_stop_event = threading.Event()

# Set up logging
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)

def setup_logging():
    log_queues = {'Amazon': queue.Queue(), 'Flipkart': queue.Queue()}
    for platform in ['Amazon', 'Flipkart']:
        logger = logging.getLogger(platform)
        logger.setLevel(logging.INFO)
        queue_handler = QueueHandler(log_queues[platform])
        queue_handler.setLevel(logging.INFO)
        logger.addHandler(queue_handler)
    return log_queues

def get_stop_event():
    global global_stop_event
    return global_stop_event

def perform_search(platforms, keywords, ranking):
    stop_event = get_stop_event()
    stop_event.clear()
    st.session_state.results = {'Amazon': {}, 'Flipkart': {}}
    st.session_state.search_threads = {}

    for platform in platforms:
        thread = threading.Thread(target=search_thread, args=(platform, keywords, ranking))
        st.session_state.search_threads[platform] = thread
        thread.start()

def search_thread(platform, keywords, ranking):
    logger = logging.getLogger(platform)
    stop_event = get_stop_event()
    try:
        scraper_module = amazon_scraper if platform == "Amazon" else flipkart_scraper
        results = {}
        total_keywords = len(keywords)
        for index, keyword in enumerate(keywords, 1):
            if stop_event.is_set():
                logger.info(f"Search stopped for {platform}")
                return
            logger.info(f"Searching for keyword: {keyword} ({index}/{total_keywords})")
            results[keyword] = scraper_module.search(keyword, ranking)
            logger.info(f"Search completed for keyword: {keyword} ({index}/{total_keywords})")
        
        st.session_state.results[platform] = results
        logger.info(f"Processing done for {platform}, your file is ready to export")
        
    except Exception as e:
        error_msg = f"Error during {platform} search: {str(e)}"
        logger.error(error_msg)
        st.error(error_msg)

def export_results(platform):
    results = st.session_state.results.get(platform, {})
    if not results:
        st.error(f"No {platform} results to export. Please perform a search first.")
        return

    df = pd.DataFrame()
    for keyword, products in results.items():
        keyword_df = pd.DataFrame(products)
        keyword_df['Keyword'] = keyword
        df = pd.concat([df, keyword_df], ignore_index=True)

    csv = df.to_csv(index=False)
    st.download_button(
        label=f"Download {platform} Results",
        data=csv,
        file_name=f"{platform}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

def main():
    st.title("CM3 Positive*")

    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = {'Amazon': {}, 'Flipkart': {}}
    if 'search_threads' not in st.session_state:
        st.session_state.search_threads = {}
    if 'log_queues' not in st.session_state:
        st.session_state.log_queues = setup_logging()

    # Sidebar for input parameters
    st.sidebar.header("Search Parameters")
    platforms = st.sidebar.multiselect("Select Platforms", ["Amazon", "Flipkart"], default=["Amazon", "Flipkart"])
    ranking = st.sidebar.number_input("Ranking", min_value=1, value=10)
    keywords = st.sidebar.text_area("Keywords (one per line)").split('\n')
    keywords = [k.strip() for k in keywords if k.strip()]

    if st.sidebar.button("Start Search"):
        if not platforms:
            st.sidebar.error("Please select at least one platform.")
        elif not keywords:
            st.sidebar.error("Please enter at least one keyword.")
        else:
            perform_search(platforms, keywords, ranking)

    # Main content area
    for platform in platforms:
        st.header(f"{platform} Results")
        log_output = st.empty()

        # Display logs
        log_messages = []
        while True:
            try:
                record = st.session_state.log_queues[platform].get_nowait()
                message = record.getMessage()
                if not any(keyword in message.lower() for keyword in ["page", "fetched", "moving"]):
                    formatted_message = f"{datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')} - {platform} - {record.levelname} - {message}"
                    log_messages.append(formatted_message)
            except queue.Empty:
                break
        
        log_output.text_area(f"Logs for {platform}", "\n".join(log_messages), height=200, key=f"logs_{platform}")

        # Export button
        if platform in st.session_state.results and st.session_state.results[platform]:
            export_results(platform)

    # Stop button
    if st.session_state.search_threads:
        if st.button("Stop Search"):
            stop_event = get_stop_event()
            stop_event.set()
            for thread in st.session_state.search_threads.values():
                thread.join()
            st.session_state.search_threads.clear()
            st.success("Search stopped.")

if __name__ == "__main__":
    main()
