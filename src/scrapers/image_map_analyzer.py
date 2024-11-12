import logging
from typing import Dict, List
from openai import OpenAI
import fitz  # PyMuPDF for PDF image extraction
import os
from PIL import Image
import io

class ImageMapAnalyzer:
    """Analyzes images and maps from documents"""
    
    def __init__(self, openai_api_key: str = None):
        self.logger = logging.getLogger(__name__)
        self.openai_api_key = openai_api_key
        
        # Initialize OpenAI client for GPT-4 Vision
        try:
            self.client = OpenAI(api_key=openai_api_key)
            self.logger.info("OpenAI client initialized for image analysis")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise Exception("Failed to initialize OpenAI client")

    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract images from PDF"""
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Save image temporarily
                        image_path = f"temp_image_{page_num}_{img_index}.png"
                        with open(image_path, "wb") as image_file:
                            image_file.write(image_bytes)
                        
                        images.append({
                            'page': page_num + 1,
                            'path': image_path,
                            'size': len(image_bytes)
                        })
                        
                    except Exception as e:
                        self.logger.error(f"Error extracting image {img_index} from page {page_num}: {str(e)}")
                        
            return images
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return []

    def analyze_image(self, image_path: str, context: str = None) -> Dict:
        """Analyze an image using GPT-4 Vision"""
        try:
            # Prepare image
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                
            prompt = f"""
            Analyze this image from a municipal development document.
            {f'Context: {context}' if context else ''}
            
            If this is a map:
            1. Identify marked development areas
            2. Note any color coding or legends
            3. Identify infrastructure and key features
            4. Note scale and orientation if present
            
            If this shows development plans:
            1. Identify the type of development
            2. Note any measurements or specifications
            3. Identify key features and facilities
            4. Note any phase indicators
            
            Format your response as detailed, structured information.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ]
            )
            
            return {
                'success': True,
                'analysis': response.choices[0].message.content,
                'image_path': image_path
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing image {image_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'image_path': image_path
            }

    def is_map(self, image_path: str) -> bool:
        """Detect if an image is likely a map"""
        try:
            # Use GPT-4 Vision to determine if image is a map
            result = self.analyze_image(image_path, "Is this a map?")
            return 'map' in result['analysis'].lower()
        except:
            return False

    def analyze_pdf_visuals(self, pdf_path: str, gemeente: str) -> Dict:
        """Complete analysis of visuals in a PDF"""
        results = {
            'maps': [],
            'development_plans': [],
            'other_images': []
        }
        
        # Extract images
        images = self.extract_images_from_pdf(pdf_path)
        
        for img in images:
            # Analyze each image
            analysis = self.analyze_image(img['path'])
            
            if analysis['success']:
                # Categorize based on content
                if self.is_map(img['path']):
                    results['maps'].append({
                        'page': img['page'],
                        'analysis': analysis['analysis']
                    })
                elif 'development' in analysis['analysis'].lower():
                    results['development_plans'].append({
                        'page': img['page'],
                        'analysis': analysis['analysis']
                    })
                else:
                    results['other_images'].append({
                        'page': img['page'],
                        'analysis': analysis['analysis']
                    })
            
            # Clean up temporary image
            os.remove(img['path'])
        
        return results

def main():
    """Test the image/map analyzer"""
    analyzer = ImageMapAnalyzer(os.getenv("OPENAI_API_KEY"))
    
    # Test with a PDF
    pdf_path = "test.pdf"
    results = analyzer.analyze_pdf_visuals(pdf_path, "Amsterdam")
    
    print(f"Found {len(results['maps'])} maps")
    print(f"Found {len(results['development_plans'])} development plans")

if __name__ == "__main__":
    main()