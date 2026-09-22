# WooCommerce Product SEO Optimizer

WooCommerce Product SEO Optimizer is a Python-based tool designed to automatically enhance the SEO of your WooCommerce store's products. It leverages Large Language Models (LLMs) with multimodal capabilities (image analysis) to generate optimized product titles and descriptions based on the actual product images and existing data.

## Features

- **Automated SEO Optimization**: Automatically fetches products from your WooCommerce store and optimizes their titles and descriptions.
- **Multimodal Analysis**: Uses LLMs to analyze product images to ensure the generated content is accurate and descriptive.
- **Image Caching**: Downloads and caches product images locally to reduce API calls and improve performance.
- **Image Format Handling**: Automatically handles various image formats, including converting WebP to JPG for better compatibility with some LLM providers.
- **WooCommerce Integration**: Seamlessly integrates with the WooCommerce REST API v3.
- **Detailed Logging**: Maintains a log file (`product_optimizer.log`) to track the optimization process and any errors.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A WooCommerce store with REST API access (Consumer Key and Consumer Secret)
- Access to an LLM API that supports image analysis (e.g., OpenAI GPT-4o, Claude 3.5 Sonnet, etc.)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/EcomDevLeon/product-optimizer.git
   cd product-optimizer
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application**:
   - Copy `config.sample.py` to `config.py`:
     ```bash
     cp config.sample.py config.py
     ```
   - Open `config.py` and fill in your WooCommerce and LLM credentials:
     - `SITE_URL`: Your WooCommerce store URL.
     - `CONSUMER_KEY`: Your WooCommerce REST API consumer key.
     - `CONSUMER_SECRET`: Your WooCommerce REST API consumer secret.
     - `LLM_URL`: The endpoint URL of your LLM provider.
     - `LLM_MODEL`: The model name to be used for optimization.
     - `IMAGE_CACHE_DIR`: Directory where product images will be cached.
     - `SEO_PROMPT_TEMPLATE`: The prompt used by the LLM to generate SEO content.

### Usage

Run the optimizer script:
```bash
python product_optimizer.py
```

The script will:
1. Fetch products from your WooCommerce store.
2. Download and cache product images.
3. Send the images and existing product data to the LLM.
4. Update the product title and description in your WooCommerce store with the optimized content.

## Project Structure

- `product_optimizer.py`: The main entry point of the application.
- `config.py`: Configuration file containing API keys and settings.
- `libs/woocommerce.py`: A wrapper for the WooCommerce REST API.
- `requirements.txt`: List of Python dependencies.
- `tmp/images/`: Default directory for cached product images.

## License

This project is licensed under the MIT License.

Developed by [EcomDevLeon](https://github.com/EcomDevLeon).
