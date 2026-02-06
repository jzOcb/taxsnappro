"""
TaxSnapPro - Document Extractor using Google Gemini API (Free Tier)
"""
import os
import base64
import json
import asyncio
import httpx
from pathlib import Path
from typing import Optional

# Rate limiting settings
# Gemini free tier: 15 RPM (requests per minute) = 1 request per 4 seconds
# Being conservative with 5 seconds to avoid hitting limits
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 10  # Initial retry delay (will exponentially backoff)
REQUEST_DELAY_SECONDS = 5  # Delay between requests to avoid rate limiting


# Prompt to extract tax document data
EXTRACTION_PROMPT = """You are a tax document parser. Analyze this tax document image and extract all relevant data.

For W-2 forms, extract:
- employer_name: Company name
- employer_ein: Employer's EIN (XX-XXXXXXX)
- wages: Box 1 - Wages, tips, other compensation
- federal_withheld: Box 2 - Federal income tax withheld
- social_security_wages: Box 3
- social_security_tax: Box 4
- medicare_wages: Box 5
- medicare_tax: Box 6
- state: State abbreviation
- state_wages: State wages
- state_tax_withheld: State tax withheld

For 1099-INT forms, extract:
- payer_name: Financial institution name
- interest_income: Box 1 - Interest income
- federal_withheld: Box 4 - Federal income tax withheld

For 1099-DIV forms (Dividend Income), extract:
- payer_name: Institution/broker name (e.g., Fidelity, Schwab, Vanguard)
- ordinary_dividends: Box 1a - Total ordinary dividends (THIS IS THE MAIN AMOUNT - look for it carefully!)
- qualified_dividends: Box 1b - Qualified dividends
- capital_gain: Box 2a - Total capital gain distributions
- federal_withheld: Box 4 - Federal income tax withheld
NOTE: On consolidated 1099s, dividend info may be labeled "1099-DIV" in a section. Look for dollar amounts next to Box 1a.

For 1099-B forms, extract:
- payer_name: Broker name
- proceeds: Total proceeds
- cost_basis: Total cost basis
- gain_loss: Net gain or loss

For 1098 forms, extract:
- lender_name: Mortgage company name
- mortgage_interest: Box 1 - Mortgage interest received
- points_paid: Box 6 - Points paid
- property_taxes: Property taxes (if shown)

For 5498-SA (HSA) forms, extract:
- trustee_name: HSA trustee/administrator name
- contribution: Box 2 - Total contributions made in tax year
- fair_market_value: Box 5 - Fair market value of account

For 1099-SA (HSA distributions), extract:
- payer_name: HSA trustee name
- distribution: Box 1 - Gross distribution
- earnings: Box 2 - Earnings on excess contributions

For 1099-NEC (Nonemployee Compensation), extract:
- payer_name: Company/person who paid you
- payer_ein: Payer's TIN (if shown)
- nonemployee_compensation: Box 1 - Nonemployee compensation (this is self-employment income)
- federal_withheld: Box 4 - Federal income tax withheld (if any)
- state_tax_withheld: Box 5 - State tax withheld (if any)

For 1099-MISC (Miscellaneous Income), extract:
- payer_name: Company/person who paid you
- rents: Box 1 - Rents received
- royalties: Box 2 - Royalties
- other_income: Box 3 - Other income
- fishing_boat_proceeds: Box 5 - Fishing boat proceeds
- medical_payments: Box 6 - Medical and health care payments
- nonemployee_compensation: Box 7 - Nonemployee compensation (pre-2020 forms, now on 1099-NEC)
- substitute_payments: Box 8 - Substitute payments in lieu of dividends
- crop_insurance: Box 9 - Crop insurance proceeds
- attorney_fees: Box 10 - Gross proceeds paid to an attorney
- federal_withheld: Box 4 - Federal income tax withheld

Respond ONLY with a valid JSON object containing:
{
  "document_type": "W-2" | "1099-INT" | "1099-DIV" | "1099-B" | "1098" | "5498-SA" | "1099-SA" | "1099-NEC" | "1099-MISC" | "OTHER",
  "confidence": 0.0-1.0,
  "extracted_data": {
    // relevant fields based on document type
  }
}

Important:
- All monetary values should be numbers (no $ or commas)
- If a field is not visible or unclear, omit it
- Set confidence lower if document is blurry or partially visible
"""


async def extract_from_document(
    file_path: str,
    api_key: Optional[str] = None,
) -> dict:
    """
    Extract tax data from a document using Google Gemini API (Free Tier).
    
    Args:
        file_path: Path to PDF or image file
        api_key: Gemini API key (uses GOOGLE_API_KEY env var if not provided)
        
    Returns:
        Dict with document_type, confidence, and extracted_data
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "error": "No API key provided. Get a free key from aistudio.google.com/apikey",
            "document_type": "UNKNOWN",
            "confidence": 0.0,
            "extracted_data": {}
        }
    
    # Read and encode file
    path = Path(file_path)
    if not path.exists():
        return {
            "error": f"File not found: {file_path}",
            "document_type": "UNKNOWN",
            "confidence": 0.0,
            "extracted_data": {}
        }
    
    file_bytes = path.read_bytes()
    base64_data = base64.standard_b64encode(file_bytes).decode("utf-8")
    
    # Determine media type
    suffix = path.suffix.lower()
    media_type_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/png")
    
    # Check file size (Gemini inline limit ~20MB)
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > 20:
        return {
            "error": f"File too large ({file_size_mb:.1f}MB). Please split into smaller files (<20MB each).",
            "document_type": "UNKNOWN",
            "confidence": 0.0,
            "extracted_data": {}
        }
    
    # Call Gemini API
    # Use gemini-2.0-flash for PDF/document support
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                headers={
                    "content-type": "application/json",
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "inline_data": {
                                        "mime_type": media_type,
                                        "data": base64_data,
                                    }
                                },
                                {
                                    "text": EXTRACTION_PROMPT,
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 4096,
                    }
                },
            )
            
            if response.status_code != 200:
                error_text = response.text
                if "API_KEY_INVALID" in error_text:
                    return {
                        "error": "Invalid API key. Get a free key from aistudio.google.com/apikey",
                        "document_type": "UNKNOWN",
                        "confidence": 0.0,
                        "extracted_data": {}
                    }
                if "INVALID_ARGUMENT" in error_text and "pdf" in error_text.lower():
                    return {
                        "error": "PDF processing failed. Try converting to images (screenshot each page) or use a smaller file.",
                        "document_type": "UNKNOWN",
                        "confidence": 0.0,
                        "extracted_data": {}
                    }
                if "RESOURCE_EXHAUSTED" in error_text or response.status_code == 429:
                    # Rate limited - will be retried by caller
                    return {
                        "error": "RATE_LIMITED",
                        "document_type": "UNKNOWN",
                        "confidence": 0.0,
                        "extracted_data": {}
                    }
                return {
                    "error": f"API error: {response.status_code} - {error_text[:200]}",
                    "document_type": "UNKNOWN",
                    "confidence": 0.0,
                    "extracted_data": {}
                }
            
            result = response.json()
            
            # Extract text from Gemini response
            candidates = result.get("candidates", [])
            if not candidates:
                return {
                    "error": "No response from Gemini",
                    "document_type": "UNKNOWN",
                    "confidence": 0.0,
                    "extracted_data": {}
                }
            
            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            
            # Parse JSON from response
            # Handle case where model wraps in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            try:
                parsed = json.loads(content.strip())
                return parsed
            except json.JSONDecodeError:
                return {
                    "error": f"Failed to parse response as JSON: {content[:200]}",
                    "document_type": "UNKNOWN",
                    "confidence": 0.0,
                    "extracted_data": {}
                }
                
    except Exception as e:
        return {
            "error": f"Request failed: {str(e)}",
            "document_type": "UNKNOWN",
            "confidence": 0.0,
            "extracted_data": {}
        }


async def extract_with_retry(
    file_path: str,
    api_key: Optional[str] = None,
) -> dict:
    """
    Extract with automatic retry on rate limiting and transient errors.
    """
    last_result = None
    
    for attempt in range(MAX_RETRIES):
        result = await extract_from_document(file_path, api_key)
        last_result = result
        
        error = result.get("error", "")
        
        # Check for retryable errors
        is_rate_limited = error == "RATE_LIMITED"
        is_transient = any(x in str(error).lower() for x in [
            "rate", "quota", "limit", "429", "500", "502", "503", "504",
            "timeout", "overloaded", "capacity", "try again"
        ])
        
        if is_rate_limited or is_transient:
            if attempt < MAX_RETRIES - 1:
                # Wait and retry with exponential backoff
                wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)
                print(f"[TaxSnapPro] Rate limited, waiting {wait_time}s before retry {attempt + 2}/{MAX_RETRIES}...")
                await asyncio.sleep(wait_time)
                continue
            else:
                return {
                    "error": f"API quota exceeded after {MAX_RETRIES} retries. Please wait a minute and try again.",
                    "document_type": "UNKNOWN",
                    "confidence": 0.0,
                    "extracted_data": {}
                }
        
        # Non-retryable error or success
        return result
    
    return last_result or {
        "error": "Max retries exceeded",
        "document_type": "UNKNOWN",
        "confidence": 0.0,
        "extracted_data": {}
    }


def convert_to_w2(extracted_data: dict) -> dict:
    """Convert extracted data to W-2 format for state."""
    return {
        "employer_name": extracted_data.get("employer_name", "Unknown Employer"),
        "wages": float(extracted_data.get("wages", 0)),
        "federal_withheld": float(extracted_data.get("federal_withheld", 0)),
    }


def convert_to_1099(extracted_data: dict, form_type: str) -> dict:
    """Convert extracted data to 1099 format for state."""
    amount = 0.0
    
    if form_type == "1099-INT":
        # Try multiple field names that LLM might use
        amount = float(extracted_data.get("interest_income", 0) or 
                      extracted_data.get("interest", 0) or
                      extracted_data.get("box_1", 0) or
                      extracted_data.get("taxable_interest", 0) or 0)
    elif form_type == "1099-DIV":
        # Try multiple field names that LLM might use
        amount = float(extracted_data.get("ordinary_dividends", 0) or 
                      extracted_data.get("total_ordinary_dividends", 0) or
                      extracted_data.get("dividends", 0) or
                      extracted_data.get("box_1a", 0) or
                      extracted_data.get("total_dividends", 0) or 0)
    elif form_type == "1099-B":
        # Try multiple field names
        amount = float(extracted_data.get("gain_loss", 0) or 
                      extracted_data.get("net_gain_loss", 0) or
                      extracted_data.get("proceeds", 0) or
                      extracted_data.get("total_proceeds", 0) or 0)
    
    return {
        "payer_name": extracted_data.get("payer_name", extracted_data.get("lender_name", extracted_data.get("institution", "Unknown Payer"))),
        "amount": amount,
        "form_type": form_type,
        "raw_data": extracted_data,  # Keep raw for debugging
    }


def convert_to_business_income(extracted_data: dict, source_type: str) -> dict:
    """
    Convert 1099-NEC or 1099-MISC to Schedule C business income.
    
    1099-NEC Box 1 = Self-employment income (goes to Schedule C)
    1099-MISC Box 7 (pre-2020) = Same as 1099-NEC
    """
    gross_income = 0.0
    payer_name = extracted_data.get("payer_name", "Unknown Client")
    
    if source_type == "1099-NEC":
        gross_income = float(extracted_data.get("nonemployee_compensation", 0))
    elif source_type == "1099-MISC":
        # Box 7 was nonemployee comp before 2020, now rarely used
        gross_income = float(extracted_data.get("nonemployee_compensation", 0))
    
    return {
        "name": f"Self-Employment ({payer_name})",
        "gross_income": gross_income,
        "expenses": 0.0,  # User can edit to add expenses
        "net_profit": gross_income,
        "source_form": source_type,
        "payer_name": payer_name,
        "federal_withheld": float(extracted_data.get("federal_withheld", 0)),
    }


def convert_1099_misc_to_other_income(extracted_data: dict) -> list:
    """
    Convert 1099-MISC non-self-employment boxes to other income entries.
    
    Returns a list of income entries for: rents, royalties, other income, etc.
    """
    entries = []
    payer = extracted_data.get("payer_name", "Unknown Payer")
    
    # Box 1 - Rents (goes to Schedule E if rental property, otherwise other income)
    rents = float(extracted_data.get("rents", 0))
    if rents > 0:
        entries.append({
            "description": f"Rental Income - {payer} (1099-MISC Box 1)",
            "amount": rents,
            "category": "rental",
        })
    
    # Box 2 - Royalties (goes to Schedule E)
    royalties = float(extracted_data.get("royalties", 0))
    if royalties > 0:
        entries.append({
            "description": f"Royalties - {payer} (1099-MISC Box 2)",
            "amount": royalties,
            "category": "royalty",
        })
    
    # Box 3 - Other income (taxable, goes to Schedule 1 Line 8)
    other = float(extracted_data.get("other_income", 0))
    if other > 0:
        entries.append({
            "description": f"Other Income - {payer} (1099-MISC Box 3)",
            "amount": other,
            "category": "other",
        })
    
    # Box 10 - Attorney fees (gross proceeds)
    attorney = float(extracted_data.get("attorney_fees", 0))
    if attorney > 0:
        entries.append({
            "description": f"Attorney Fees - {payer} (1099-MISC Box 10)",
            "amount": attorney,
            "category": "other",
        })
    
    return entries
