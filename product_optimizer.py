"""
WooCommerce Product SEO Optimizer

This script fetches products from a WooCommerce store, optimizes their titles and descriptions
using an LLM model with image analysis, and updates the products back to the store.
"""

import os
import sys
import json
import time
import base64
import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional
from PIL import Image
from libs.woocommerce import WooCommerce

# Import configuration
try:
    from config import (
        SITE_URL,
        CONSUMER_KEY,
        CONSUMER_SECRET,
        PRODUCTS_PER_PAGE,
        LLM_URL,
        LLM_MODEL,
        IMAGE_CACHE_DIR,
        SEO_PROMPT_TEMPLATE,
    )
except ImportError:
    from config import (
        SITE_URL,
        CONSUMER_KEY,
        CONSUMER_SECRET,
        PRODUCTS_PER_PAGE,
        LLM_URL,
        LLM_MODEL,
        IMAGE_CACHE_DIR,
        SEO_PROMPT_TEMPLATE,
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("product_optimizer.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class WooCommerceProductOptimizer:
    """Optimize WooCommerce products using LLM-powered SEO analysis."""

    def __init__(self):
        """Initialize the optimizer with WooCommerce API and configuration."""
        self.woo = WooCommerce(
            url=SITE_URL,
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            version="wc/v3",
        )
        self.llm_url = LLM_URL.rstrip("/")
        self.image_cache_dir = Path(IMAGE_CACHE_DIR)
        self.image_cache_dir.mkdir(parents=True, exist_ok=True)
        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    def download_image(self, image_url: str, product_id: int, image_index: int) -> Optional[str]:
        """
        Download a product image and cache it locally. If the image is WebP, convert it to JPG.

        Args:
            image_url: URL of the image to download
            product_id: WooCommerce product ID
            image_index: Index of the image for this product

        Returns:
            Local file path if successful, None otherwise
        """
        try:
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()

            # Generate a safe filename based on product ID and image index
            filename_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            # Extract file extension from content or URL
            content_type = response.headers.get("content-type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                # Try to get extension from URL
                ext = Path(image_url).suffix.lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    ext = ".jpg"  # Default to jpg

            local_path = self.image_cache_dir / f"product_{product_id}_img_{image_index}_{filename_hash}{ext}"

            # Save the image
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Convert WebP to JPG if necessary for LLM compatibility
            if ext == ".webp":
                try:
                    with Image.open(local_path) as img:
                        rgb_img = img.convert("RGB")
                        jpg_path = local_path.with_suffix(".jpg")
                        rgb_img.save(jpg_path, "JPEG")
                    logger.info(f"Converted WebP to JPG: {jpg_path}")
                    # Remove the original webp file to save space and avoid confusion
                    local_path.unlink()
                    return str(jpg_path)
                except Exception as conv_e:
                    logger.error(f"Failed to convert WebP to JPG for {local_path}: {conv_e}")
                    # Fallback to original path, though LLM might fail later
            
            logger.info(f"Image cached: {local_path}")
            return str(local_path)

        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return None

    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        Encode a local image file to base64 string.

        Args:
            image_path: Path to the local image file

        Returns:
            Base64 encoded string if successful, None otherwise
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
                base64_string = base64.b64encode(image_data).decode("utf-8")
                return base64_string
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return None

    def fetch_products(self, page: int = 1) -> tuple[list[dict], int]:
        """
        Fetch a batch of products from WooCommerce.

        Args:
            page: Page number to fetch (1-indexed)

        Returns:
            Tuple of (list of products, total count)
        """
        try:
            params = {
                "per_page": PRODUCTS_PER_PAGE,
                "page": page,
                "status": "publish",
            }

            logger.info(f"Fetching products page {page}...")
            products = self.woo.get("products", params=params)

            if isinstance(products, dict) and "code" in products:
                logger.error(f"WooCommerce API error: {products.get('message', 'Unknown error')}")
                return [], 0

            total_pages = int(self.woo.headers.get("X-WP-TotalPages", 0))
            total_count = int(self.woo.headers.get("X-WP-Total", 0))

            logger.info(f"Fetched {len(products)} products (total: {total_count}, pages: {total_pages})")
            return products, total_count

        except Exception as e:
            logger.error(f"Failed to fetch products: {e}")
            return [], 0

    def get_total_pages(self, total_count: int) -> int:
        """
        Calculate total pages needed to fetch all products.

        Args:
            total_count: Total number of products

        Returns:
            Total number of pages
        """
        if total_count == 0:
            return 0
        return (total_count + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE

    def prepare_product_images(self, product: dict) -> list[str]:
        """
        Download and cache all product images.

        Args:
            product: Product dictionary from WooCommerce

        Returns:
            List of local image file paths
        """
        image_paths = []
        product_id = product.get("id", 0)

        # Get featured image
        featured_image = product.get("images", [{}])[0] if product.get("images") else None
        if featured_image and featured_image.get("src"):
            local_path = self.download_image(
                featured_image["src"], product_id, 0
            )
            if local_path:
                image_paths.append(local_path)

        # Get gallery images
        gallery_images = product.get("gallery_images", [])
        for idx, gallery_img in enumerate(gallery_images, start=1):
            if gallery_img.get("src"):
                local_path = self.download_image(
                    gallery_img["src"], product_id, idx
                )
                if local_path:
                    image_paths.append(local_path)

        return image_paths

    def call_llm_for_seo(self, product: dict, image_paths: list[str]) -> Optional[dict]:
        """
        Call LLM API to optimize product title and description using images and text.

        Args:
            product: Product dictionary from WooCommerce
            image_paths: List of local image file paths

        Returns:
            Dictionary with optimized title, description, and keywords if successful, None otherwise
        """
        title = product.get("name", "")
        description = product.get("description", "")
        category = product.get("categories", [{}])[0].get("name", "") if product.get("categories") else ""
        tags = ", ".join([tag.get("name", "") for tag in product.get("tags", [])]) if product.get("tags") else ""

        # Prepare the prompt
        prompt = SEO_PROMPT_TEMPLATE.format(
            title=title,
            description=description,
            category=category,
        )

        # Build the LLM request payload
        messages = []

        # Add images if available
        if image_paths:
            image_parts = []
            for img_path in image_paths:
                base64_img = self.encode_image_to_base64(img_path)
                if base64_img:
                    # Determine MIME type from file extension
                    ext = Path(img_path).suffix.lower()
                    mime_type = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".webp": "image/webp",
                        ".gif": "image/gif",
                    }.get(ext, "image/jpeg")

                    image_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_img}",
                        },
                    })

            # Add text part
            image_parts.append({
                "type": "text",
                "text": f"""Please analyze this product and optimize its title and description for SEO.

Current Title: {title}
Current Description: {description}
Category: {category}
Tags: {tags}

Requirements:
- Title: Max 60 characters, include main keywords, compelling and click-worthy
- Description: Detailed, keyword-rich, engaging, use proper HTML formatting
- Return JSON format with: optimized_title, optimized_description, seo_keywords

Please return ONLY valid JSON, no markdown formatting, no extra text."""
            })

            messages.append({
                "role": "user",
                "content": image_parts,
            })
        else:
            # Text-only fallback
            messages.append({
                "role": "user",
                "content": prompt,
            })

        # Build the API request
        api_payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            logger.info(f"Calling LLM API at {self.llm_url}/v1/chat/completions")
            response = requests.post(
                f"{self.llm_url}/v1/chat/completions",
                json=api_payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse the JSON response from LLM
            optimized_data = self._parse_llm_response(content)
            return optimized_data

        except Exception as e:
            logger.error(f"Failed to call LLM API: {e}")
            return None

    def _parse_llm_response(self, content: str) -> Optional[dict]:
        """
        Parse the LLM response to extract optimized product data.

        Args:
            content: Raw response content from LLM

        Returns:
            Dictionary with optimized data if successful, None otherwise
        """
        try:
            # Try to extract JSON from the response
            # LLM might wrap JSON in markdown code blocks
            if "```" in content:
                # Extract JSON from code blocks
                start = content.find("```")
                end = content.rfind("```")
                if start != -1 and end != -1:
                    content = content[start + 3:end].strip()

            # Find JSON object in the content
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)

            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.error(f"Raw response: {content[:500]}")
            return None

    def update_product(self, product_id: int, optimized_data: dict) -> bool:
        """
        Update a product in WooCommerce with optimized data.

        Args:
            product_id: WooCommerce product ID
            optimized_data: Dictionary with optimized_title, optimized_description, seo_keywords

        Returns:
            True if update was successful, False otherwise
        """
        try:
            update_payload = {
                "id": product_id,
                "name": optimized_data.get("optimized_title", ""),
                "description": optimized_data.get("optimized_description", ""),
            }

            # Add SEO keywords as tags if available
            if optimized_data.get("seo_keywords"):
                # Fetch all existing tags once to avoid repeated API calls
                try:
                    tags_response = self.woo.get("products/tags")
                    existing_tags = tags_response.get("tags", []) if isinstance(tags_response, dict) else []
                except Exception as e:
                    logger.error(f"Failed to fetch existing tags: {e}")
                    existing_tags = []

                tag_ids = []

                for keyword in optimized_data["seo_keywords"]:
                    # Check if tag already exists (case-insensitive)
                    found_tag = next((tag for tag in existing_tags if tag.get("name", "").lower() == keyword.lower()), None)
                    
                    if found_tag:
                        tag_ids.append(found_tag.get("id"))
                    else:
                        # Create new tag
                        try:
                            new_tag = self.woo.post(
                                "products/tags",
                                params={"name": keyword, "slug": keyword.lower().replace(" ", "-")},
                            )
                            if new_tag and isinstance(new_tag, dict):
                                tag_id = new_tag.get("id")
                                tag_ids.append(tag_id)
                                # Add to existing_tags to avoid duplicates within the same product's keywords
                                existing_tags.append({"name": keyword, "id": tag_id})
                        except Exception as e:
                            logger.warning(f"Failed to create tag '{keyword}': {e}")

                if tag_ids:
                    update_payload["tag_ids"] = tag_ids

            logger.info(f"Updating product {product_id}...")
            result = self.woo.put(
                f"products/{product_id}",
                params=update_payload,
            )

            if isinstance(result, dict) and "id" in result:
                logger.info(f"Successfully updated product {product_id}")
                return True
            else:
                logger.error(f"Failed to update product {product_id}: {result}")
                return False

        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return False

    def optimize_single_product(self, product: dict) -> bool:
        """
        Optimize a single product: download images, call LLM, and update.

        Args:
            product: Product dictionary from WooCommerce

        Returns:
            True if optimization was successful, False otherwise
        """
        product_id = product.get("id", 0)
        product_name = product.get("name", "Unknown")

        logger.warning(f"Processing product: {product_name} (ID: {product_id})")

        # Step 1: Download and cache images
        logger.info(f"Downloading images for product {product_id}...")
        image_paths = self.prepare_product_images(product)
        logger.info(f"Downloaded {len(image_paths)} images for product {product_id}")

        # Step 2: Call LLM for SEO optimization
        logger.info(f"Calling LLM for SEO optimization...")
        optimized_data = self.call_llm_for_seo(product, image_paths)

        if not optimized_data:
            logger.warning(f"LLM optimization failed for product {product_id}, skipping")
            self.skipped_count += 1
            return False

        logger.info(f"LLM returned optimized data for product {product_id}")
        logger.info(f"  New Title: {optimized_data.get('optimized_title', 'N/A')[:60]}...")
        logger.info(f"  Keywords: {optimized_data.get('seo_keywords', [])}")

        # Step 3: Update product in WooCommerce
        success = self.update_product(product_id, optimized_data)

        if success:
            self.processed_count += 1
            logger.info(f"Successfully optimized product {product_id}")
        else:
            self.failed_count += 1
            logger.error(f"Failed to update product {product_id}")

        return success

    def run_optimization(self):
        """
        Main optimization loop: fetch all products, optimize them, and update.
        """
        logger.info("=" * 80)
        logger.info("WooCommerce Product SEO Optimizer - Starting")
        logger.info("=" * 80)

        page = 1
        processed_in_session = 0

        while True:
            # Fetch products for current page
            products, total_count = self.fetch_products(page)

            # If no products are returned, we've reached the end
            if not products:
                logger.info("No more products to process")
                break

            # Log total count only on the first page
            if page == 1:
                logger.info(f"Total products reported by API: {total_count}")
                logger.info(f"Products per page (batch size): {PRODUCTS_PER_PAGE}")

            # Process each product in the batch
            for product in products:
                try:
                    self.optimize_single_product(product)
                    # Small delay between products to avoid rate limiting
                    time.sleep(1)
                    processed_in_session += 1
                except Exception as e:
                    logger.error(f"Unexpected error processing product: {e}")
                    self.failed_count += 1

            # If we fetched fewer products than the page size, we've reached the last page
            if len(products) < PRODUCTS_PER_PAGE:
                logger.info("Reached the last page of products")
                break

            page += 1
            logger.warning(f"Completed page {page - 1}, moving to next page...")
            # Small delay between pages
            time.sleep(2)

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print optimization summary."""
        logger.info("=" * 80)
        logger.info("OPTIMIZATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Successfully optimized: {self.processed_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Skipped: {self.skipped_count}")
        logger.info(f"Total processed: {self.processed_count + self.failed_count + self.skipped_count}")
        logger.info("=" * 80)


def main():
    """Main entry point for the product optimizer."""
    optimizer = WooCommerceProductOptimizer()
    optimizer.run_optimization()


if __name__ == "__main__":
    main()
