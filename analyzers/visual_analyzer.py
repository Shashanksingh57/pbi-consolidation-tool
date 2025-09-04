# analyzers/visual_analyzer.py - GPT-4 Vision integration for dashboard analysis

import base64
import io
import json
import logging
import os
from typing import List, Dict, Any
from PIL import Image
from openai import OpenAI

from models import VisualElement, KPICard, FilterElement

logger = logging.getLogger(__name__)

class VisualAnalyzer:
    """Analyzes dashboard screenshots using GPT-4 Vision API"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.model = os.getenv("GPT_MODEL", "gpt-4o")
    
    def _encode_image(self, image: Image.Image) -> str:
        """Convert PIL image to base64 for API"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    async def analyze_dashboard_screenshot(self, image: Image.Image, page_name: str) -> List[VisualElement]:
        """
        Analyze a single dashboard screenshot and extract visual elements
        """
        try:
            logger.info(f"Analyzing dashboard page: {page_name}")
            
            # Convert image to base64
            image_base64 = self._encode_image(image)
            
            # Prepare prompt for GPT-4 Vision
            prompt = self._get_visual_analysis_prompt()
            
            # Call GPT-4 Vision API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            # Parse response
            analysis_result = response.choices[0].message.content
            logger.info(f"GPT-4 Vision response length: {len(analysis_result)} characters")
            
            # Extract structured data from response
            visual_elements = self._parse_visual_analysis(analysis_result, page_name)
            
            return visual_elements
            
        except Exception as e:
            logger.error(f"Error in visual analysis: {str(e)}")
            # Return empty list on error - don't fail the whole process
            return []
    
    def _get_visual_analysis_prompt(self) -> str:
        """Get the prompt for GPT-4 Vision analysis"""
        return """
        Analyze this Power BI dashboard screenshot and extract the following information in JSON format:

        Please identify and catalog all visual elements with their properties:

        1. **Charts and Visualizations**:
           - Type (bar chart, line chart, pie chart, table, matrix, card, etc.)
           - Title (if visible)
           - Position (approximate x, y coordinates and dimensions)
           - Visible data fields/columns
           - Chart-specific properties (orientation, colors, etc.)

        2. **KPI Cards**:
           - Title/label
           - Value format (currency, percentage, number)
           - Trend indicators (up/down arrows, colors)
           - Position

        3. **Filters and Slicers**:
           - Filter type (dropdown, slicer, date picker)
           - Field being filtered
           - Visible filter options (if any)

        4. **Layout and Structure**:
           - Overall layout pattern
           - Number of sections/areas
           - Color scheme
           - Header/title information

        Return the analysis as a JSON object with this structure:
        {
            "visual_elements": [
                {
                    "visual_type": "bar_chart",
                    "title": "Sales by Region",
                    "position": {"x": 100, "y": 50, "width": 400, "height": 300},
                    "data_fields": ["Region", "Sales Amount"],
                    "chart_properties": {"orientation": "vertical", "color_scheme": "blue"}
                }
            ],
            "kpi_cards": [
                {
                    "title": "Total Sales",
                    "value_format": "currency",
                    "trend_indicator": "up",
                    "position": {"x": 50, "y": 10, "width": 200, "height": 100}
                }
            ],
            "filters": [
                {
                    "filter_type": "dropdown",
                    "field_name": "Year",
                    "filter_values": ["2022", "2023", "2024"]
                }
            ],
            "layout_properties": {
                "sections_count": 4,
                "color_scheme": "blue_theme",
                "has_header": true,
                "layout_pattern": "grid"
            }
        }

        Focus on accuracy and detail. If something is unclear or not visible, indicate that in the response.
        """
    
    def _parse_visual_analysis(self, analysis_result: str, page_name: str) -> List[VisualElement]:
        """
        Parse GPT-4 Vision response and convert to VisualElement objects
        """
        try:
            # Try to extract JSON from the response
            json_start = analysis_result.find('{')
            json_end = analysis_result.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = analysis_result[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                logger.warning("No JSON found in GPT-4 Vision response")
                return []
            
            visual_elements = []
            
            # Process visual elements
            for element_data in analysis_data.get('visual_elements', []):
                try:
                    visual_element = VisualElement(
                        visual_type=element_data.get('visual_type', 'unknown'),
                        title=element_data.get('title'),
                        position=element_data.get('position', {}),
                        data_fields=element_data.get('data_fields', []),
                        chart_properties=element_data.get('chart_properties', {}),
                        page_name=page_name
                    )
                    visual_elements.append(visual_element)
                except Exception as e:
                    logger.warning(f"Error parsing visual element: {str(e)}")
                    continue
            
            # Process KPI cards as visual elements
            for kpi_data in analysis_data.get('kpi_cards', []):
                try:
                    kpi_element = VisualElement(
                        visual_type='kpi_card',
                        title=kpi_data.get('title'),
                        position=kpi_data.get('position', {}),
                        data_fields=[],
                        chart_properties={
                            'value_format': kpi_data.get('value_format'),
                            'trend_indicator': kpi_data.get('trend_indicator')
                        },
                        page_name=page_name
                    )
                    visual_elements.append(kpi_element)
                except Exception as e:
                    logger.warning(f"Error parsing KPI card: {str(e)}")
                    continue
            
            # Process filters as visual elements
            for filter_data in analysis_data.get('filters', []):
                try:
                    filter_element = VisualElement(
                        visual_type='filter',
                        title=f"Filter: {filter_data.get('field_name', 'Unknown')}",
                        position={},
                        data_fields=[filter_data.get('field_name', '')],
                        chart_properties={
                            'filter_type': filter_data.get('filter_type'),
                            'filter_values': filter_data.get('filter_values', [])
                        },
                        page_name=page_name
                    )
                    visual_elements.append(filter_element)
                except Exception as e:
                    logger.warning(f"Error parsing filter: {str(e)}")
                    continue
            
            logger.info(f"Extracted {len(visual_elements)} visual elements from {page_name}")
            return visual_elements
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from GPT-4 Vision response: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing visual analysis: {str(e)}")
            return []
    
    def analyze_multiple_pages(self, images: List[Image.Image], dashboard_name: str) -> List[VisualElement]:
        """
        Analyze multiple dashboard pages
        """
        all_elements = []
        
        for i, image in enumerate(images):
            page_name = f"{dashboard_name}_page_{i+1}"
            page_elements = self.analyze_dashboard_screenshot(image, page_name)
            all_elements.extend(page_elements)
        
        return all_elements
    
    def get_visual_summary(self, visual_elements: List[VisualElement]) -> Dict[str, Any]:
        """
        Generate a summary of visual elements for similarity comparison
        """
        visual_types = {}
        total_elements = len(visual_elements)
        
        for element in visual_elements:
            visual_type = element.visual_type
            if visual_type in visual_types:
                visual_types[visual_type] += 1
            else:
                visual_types[visual_type] = 1
        
        # Calculate proportions
        visual_proportions = {
            vtype: count / total_elements if total_elements > 0 else 0
            for vtype, count in visual_types.items()
        }
        
        return {
            'total_elements': total_elements,
            'visual_types': visual_types,
            'visual_proportions': visual_proportions,
            'unique_visual_types': len(visual_types),
            'pages': len(set(element.page_name for element in visual_elements))
        }
    
    async def analyze_multiple_images(self, image_files: List, dashboard_id: str, dashboard_name: str) -> Dict[str, Any]:
        """
        Analyze multiple dashboard screenshots (views) for a single dashboard
        """
        try:
            all_visual_elements = []
            all_kpi_cards = []
            all_filters = []
            
            for i, image_file in enumerate(image_files):
                # Read image file
                image_content = await image_file.read()
                image = Image.open(io.BytesIO(image_content))
                
                # Create view name
                view_name = f"view_{i+1}"
                
                # Analyze this view
                visual_elements = await self.analyze_dashboard_screenshot(image, view_name)
                all_visual_elements.extend(visual_elements)
                
                # Extract KPI cards and filters for this view
                kpi_cards = self._extract_kpi_cards(visual_elements, view_name)
                all_kpi_cards.extend(kpi_cards)
                
                filters = self._extract_filters(visual_elements, view_name)
                all_filters.extend(filters)
                
                logger.info(f"Analyzed {dashboard_name} - {view_name}: {len(visual_elements)} elements")
            
            # Generate consolidated summary
            summary = self._generate_consolidated_summary(
                all_visual_elements, all_kpi_cards, all_filters, len(image_files)
            )
            
            return {
                'visual_elements': all_visual_elements,
                'kpi_cards': all_kpi_cards,
                'filters': all_filters,
                'summary': summary,
                'total_views': len(image_files)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing multiple images for {dashboard_name}: {str(e)}")
            raise e
    
    def _extract_kpi_cards(self, visual_elements: List[VisualElement], page_name: str) -> List[KPICard]:
        """Extract KPI cards from visual elements"""
        kpi_cards = []
        for element in visual_elements:
            if element.visual_type.lower() in ['card', 'kpi', 'metric']:
                kpi_card = KPICard(
                    title=element.title or f"KPI Card {len(kpi_cards)+1}",
                    value_format=element.chart_properties.get('format'),
                    trend_indicator=element.chart_properties.get('trend'),
                    position=element.position
                )
                kpi_cards.append(kpi_card)
        return kpi_cards
    
    def _extract_filters(self, visual_elements: List[VisualElement], page_name: str) -> List[FilterElement]:
        """Extract filter elements from visual elements"""
        filters = []
        for element in visual_elements:
            if element.visual_type.lower() in ['slicer', 'filter', 'dropdown']:
                filter_element = FilterElement(
                    filter_type=element.visual_type,
                    field_name=element.title,
                    filter_values=element.data_fields
                )
                filters.append(filter_element)
        return filters
    
    def _generate_consolidated_summary(self, visual_elements: List[VisualElement], 
                                     kpi_cards: List[KPICard], filters: List[FilterElement],
                                     total_views: int) -> Dict[str, Any]:
        """Generate a consolidated summary of all views"""
        visual_types = {}
        for element in visual_elements:
            vtype = element.visual_type
            visual_types[vtype] = visual_types.get(vtype, 0) + 1
        
        return {
            'total_views': total_views,
            'total_visual_elements': len(visual_elements),
            'total_kpi_cards': len(kpi_cards),
            'total_filters': len(filters),
            'visual_types_distribution': visual_types,
            'most_common_visual': max(visual_types.items(), key=lambda x: x[1])[0] if visual_types else None,
            'complexity_score': self._calculate_complexity_score(visual_elements, kpi_cards, filters)
        }
    
    def _calculate_complexity_score(self, visual_elements: List[VisualElement], 
                                  kpi_cards: List[KPICard], filters: List[FilterElement]) -> float:
        """Calculate dashboard complexity score"""
        base_score = len(visual_elements) * 0.5
        kpi_score = len(kpi_cards) * 0.3
        filter_score = len(filters) * 0.2
        
        # Normalize to 0-10 scale
        total_score = (base_score + kpi_score + filter_score) / 10
        return min(total_score, 10.0)