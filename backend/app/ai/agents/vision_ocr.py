"""
AI Tutor Platform - Vision OCR Agent
Uses GPT-4o Vision for OCR of scanned documents and diagram description.

Capabilities:
1. OCR for scanned/image-based PDFs
2. Diagram and chart description
3. Table structure extraction
4. Handwriting recognition
"""
import base64
import io
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from app.ai.agents.base import BaseAgent, AgentContext, AgentResult, AgentState
from app.core.config import settings


@dataclass
class VisionOCRResult:
    """Result from vision OCR processing."""
    text: str
    page_number: int
    has_diagrams: bool
    diagram_descriptions: List[str]
    tables: List[Dict[str, Any]]
    confidence: float


@dataclass
class ImageAnalysisResult:
    """Result from analyzing a single image."""
    description: str
    extracted_text: str
    image_type: str  # diagram, chart, table, photo, handwriting
    educational_content: str


class VisionOCRAgent(BaseAgent):
    """
    Vision OCR Agent using GPT-4o for multimodal document processing.
    
    Handles:
    - Scanned PDF pages (image-based, no selectable text)
    - Diagrams and charts with educational descriptions
    - Tables with structured extraction
    - Handwritten content
    """
    
    name = "VisionOCRAgent"
    description = "GPT-4o powered OCR and visual content description"
    version = "1.0.0"
    
    # GPT-4o vision model
    VISION_MODEL = "gpt-4o"
    
    # Prompts
    OCR_PROMPT = """You are an OCR system. Extract ALL text from this image exactly as it appears.
Preserve formatting, paragraphs, and structure as much as possible.
If there are tables, represent them with | separators.
If there is handwriting, do your best to transcribe it.

Return ONLY the extracted text, no commentary."""

    DIAGRAM_PROMPT = """You are an educational content analyzer. This image contains a diagram, chart, or visual from educational material.

Describe this visual for a Grade {grade} student:
1. What type of visual is this? (diagram, chart, flowchart, illustration, etc.)
2. What concept does it explain?
3. Describe the key elements and their relationships
4. What is the main educational takeaway?

Be clear and educational. Use simple language appropriate for the grade level."""

    TABLE_PROMPT = """Extract the table from this image as structured data.
Return as JSON with format:
{{
  "headers": ["Column1", "Column2", ...],
  "rows": [
    ["Value1", "Value2", ...],
    ...
  ]
}}
Only return the JSON, nothing else."""

    async def plan(self, context: AgentContext) -> Dict[str, Any]:
        """Plan vision processing."""
        image_data = context.metadata.get("image_data")
        image_path = context.metadata.get("image_path")
        mode = context.metadata.get("mode", "ocr")  # ocr, diagram, table
        
        if not image_data and not image_path:
            return {"action": "error", "error": "No image_data or image_path provided"}
        
        return {
            "action": "process",
            "params": {
                "image_data": image_data,
                "image_path": image_path,
                "mode": mode,
                "grade": context.metadata.get("grade", 5),
                "page_number": context.metadata.get("page_number", 1),
            }
        }
    
    async def execute(self, context: AgentContext, plan: Dict[str, Any]) -> AgentResult:
        """Execute vision processing."""
        if plan["action"] == "error":
            return AgentResult(
                success=False,
                output=None,
                state=AgentState.ERROR,
                error=plan["error"]
            )
        
        params = plan["params"]
        mode = params["mode"]
        
        try:
            # Get image as base64
            if params.get("image_data"):
                image_base64 = params["image_data"]
            else:
                image_base64 = await self._load_image(params["image_path"])
            
            if not image_base64:
                return AgentResult(
                    success=False,
                    output=None,
                    state=AgentState.ERROR,
                    error="Failed to load image"
                )
            
            # Process based on mode
            if mode == "ocr":
                result = await self._perform_ocr(image_base64, params["page_number"])
            elif mode == "diagram":
                result = await self._describe_diagram(image_base64, params["grade"])
            elif mode == "table":
                result = await self._extract_table(image_base64)
            else:
                result = await self._perform_ocr(image_base64, params["page_number"])
            
            return AgentResult(
                success=True,
                output=result,
                state=AgentState.COMPLETED,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                state=AgentState.ERROR,
                error=str(e)
            )
    
    async def _load_image(self, image_path: str) -> Optional[str]:
        """Load image from path and convert to base64."""
        try:
            path = Path(image_path)
            if not path.exists():
                return None
            
            with open(path, "rb") as f:
                image_bytes = f.read()
            
            return base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            print(f"[VisionOCR] Failed to load image: {e}")
            return None
    
    async def _call_vision_api(
        self, 
        image_base64: str, 
        prompt: str,
        max_tokens: int = 1000,
    ) -> str:
        """Call GPT-4o Vision API."""
        import httpx
        
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # Determine image type from base64 header or default to jpeg
        if image_base64.startswith("/9j/"):
            media_type = "image/jpeg"
        elif image_base64.startswith("iVBOR"):
            media_type = "image/png"
        else:
            media_type = "image/jpeg"
        
        payload = {
            "model": self.VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_base64}",
                                "detail": "high",
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"]
    
    async def _perform_ocr(
        self, 
        image_base64: str,
        page_number: int,
    ) -> VisionOCRResult:
        """Perform OCR on an image."""
        text = await self._call_vision_api(image_base64, self.OCR_PROMPT, max_tokens=2000)
        
        return VisionOCRResult(
            text=text,
            page_number=page_number,
            has_diagrams=False,
            diagram_descriptions=[],
            tables=[],
            confidence=0.9,
        )
    
    async def _describe_diagram(
        self,
        image_base64: str,
        grade: int,
    ) -> ImageAnalysisResult:
        """Describe a diagram or chart for educational purposes."""
        prompt = self.DIAGRAM_PROMPT.format(grade=grade)
        description = await self._call_vision_api(image_base64, prompt, max_tokens=500)
        
        return ImageAnalysisResult(
            description=description,
            extracted_text="",
            image_type="diagram",
            educational_content=description,
        )
    
    async def _extract_table(self, image_base64: str) -> Dict[str, Any]:
        """Extract structured table data from image."""
        import json
        
        response = await self._call_vision_api(image_base64, self.TABLE_PROMPT, max_tokens=1000)
        
        try:
            # Try to parse as JSON
            table_data = json.loads(response)
            return table_data
        except json.JSONDecodeError:
            # Return as raw text if not valid JSON
            return {"raw_text": response}
    
    # --- Public API ---
    
    async def ocr_image(
        self,
        image_path: Optional[str] = None,
        image_data: Optional[str] = None,
        page_number: int = 1,
    ) -> VisionOCRResult:
        """
        Perform OCR on an image.
        
        Args:
            image_path: Path to image file
            image_data: Base64 encoded image data
            page_number: Page number for multi-page documents
            
        Returns:
            VisionOCRResult with extracted text
        """
        result = await self.run(
            user_input="Extract text from image",
            metadata={
                "image_path": image_path,
                "image_data": image_data,
                "mode": "ocr",
                "page_number": page_number,
            }
        )
        
        if result.success:
            return result.output
        else:
            return VisionOCRResult(
                text="",
                page_number=page_number,
                has_diagrams=False,
                diagram_descriptions=[],
                tables=[],
                confidence=0.0,
            )
    
    async def describe_visual(
        self,
        image_path: Optional[str] = None,
        image_data: Optional[str] = None,
        grade: int = 5,
    ) -> ImageAnalysisResult:
        """
        Describe a diagram or visual for educational purposes.
        
        Args:
            image_path: Path to image file
            image_data: Base64 encoded image data
            grade: Student grade level for appropriate description
            
        Returns:
            ImageAnalysisResult with educational description
        """
        result = await self.run(
            user_input="Describe this visual",
            metadata={
                "image_path": image_path,
                "image_data": image_data,
                "mode": "diagram",
                "grade": grade,
            }
        )
        
        if result.success:
            return result.output
        else:
            return ImageAnalysisResult(
                description="Unable to analyze image",
                extracted_text="",
                image_type="unknown",
                educational_content="",
            )


# Singleton instance
vision_ocr_agent = VisionOCRAgent()
