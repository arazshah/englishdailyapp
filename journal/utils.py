import openai
from django.conf import settings
import difflib
import logging
import re
from collections import Counter
import json
import os
from datetime import datetime
from io import BytesIO
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.http import HttpResponse

# Set up logging
logger = logging.getLogger(__name__)

# Set the API key and base URL globally
openai.api_key = settings.OPENAI_API_KEY
openai.api_base = settings.OPENAI_BASE_URL


def calculate_metrics(original_text, polished_text):
    """Calculate detailed metrics comparing original and polished text."""
    # Text statistics
    original_words = len(original_text.split())
    polished_words = len(polished_text.split())
    
    sentence_pattern = r'[.!?]+\s'
    original_sentences = len(re.split(sentence_pattern, original_text))
    polished_sentences = len(re.split(sentence_pattern, polished_text))
    
    # Quality metrics
    avg_sentence_length_original = round(original_words / max(original_sentences, 1), 1)
    avg_sentence_length_polished = round(polished_words / max(polished_sentences, 1), 1)
    
    # Vocabulary richness (unique words / total words)
    original_unique_words = len(set(re.findall(r'\b\w+\b', original_text.lower())))
    polished_unique_words = len(set(re.findall(r'\b\w+\b', polished_text.lower())))
    
    vocabulary_richness_original = round((original_unique_words / max(original_words, 1)) * 100, 1)
    vocabulary_richness_polished = round((polished_unique_words / max(polished_words, 1)) * 100, 1)
    
    # Change analysis
    original_lines = original_text.splitlines()
    polished_lines = polished_text.splitlines()
    
    diff = list(difflib.ndiff(original_lines, polished_lines))
    
    added_lines = len([line for line in diff if line.startswith('+ ')])
    removed_lines = len([line for line in diff if line.startswith('- ')])
    unchanged_lines = len([line for line in diff if line.startswith('  ')])
    
    total_lines = max(len(original_lines), len(polished_lines))
    change_percentage = round(((added_lines + removed_lines) / max(total_lines, 1)) * 100, 1)
    
    return {
        'text_statistics': {
            'original_words': original_words,
            'polished_words': polished_words,
            'word_count_diff': polished_words - original_words,
            'original_sentences': original_sentences,
            'polished_sentences': polished_sentences,
            'sentence_count_diff': polished_sentences - original_sentences,
        },
        'quality_metrics': {
            'avg_sentence_length_original': avg_sentence_length_original,
            'avg_sentence_length_polished': avg_sentence_length_polished,
            'vocabulary_richness_original': vocabulary_richness_original,
            'vocabulary_richness_polished': vocabulary_richness_polished,
        },
        'change_analysis': {
            'added_lines': added_lines,
            'removed_lines': removed_lines,
            'unchanged_lines': unchanged_lines,
            'change_percentage': change_percentage,
        }
    }


def polish_text(text):
    """
    Polish the given text using AI.
    
    Args:
        text: The text to polish
        
    Returns:
        dict: Dictionary containing polish data
    """
    import openai
    from django.conf import settings
    import difflib
    import re
    
    # Configure OpenAI API
    openai.api_key = settings.OPENAI_API_KEY
    
    try:
        # Create the prompt for the AI
        prompt = f"""
        Please polish the following journal entry to improve its grammar, clarity, and flow while preserving the original meaning and voice.
        
        Original Journal Entry:
        {text}
        
        Please provide the following in your response:
        1. The polished version of the text
        2. A brief evaluation of the writing
        3. The main topic of the journal entry
        4. A set of metrics (grammar, clarity, coherence, vocabulary, overall) on a scale of 0-100
        5. An estimate of the improvement percentage
        
        Format your response as a JSON object with the following keys:
        - polished_text: The polished version of the text
        - evaluation: Your evaluation of the writing
        - topic: The main topic of the journal entry
        - metrics: An object with the metrics
        """
        
        # Call the OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful writing assistant that polishes journal entries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        
        # Extract the response content
        response_content = response.choices[0].message.content
        
        # Parse the JSON response
        import json
        import re
        
        # Try to extract JSON from the response
        json_match = re.search(r'```json\n(.*?)\n```', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no JSON code block, try to parse the whole response
            json_str = response_content
        
        try:
            polish_data = json.loads(json_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a basic structure
            polish_data = {
                "polished_text": "Error parsing AI response. Please try again.",
                "evaluation": "Unable to evaluate.",
                "topic": "Unknown",
                "metrics": {
                    "grammar": 0,
                    "clarity": 0,
                    "coherence": 0,
                    "vocabulary": 0,
                    "overall": 0,
                    "improvement": 0
                }
            }
        
        # Generate diff HTML
        original_lines = text.splitlines()
        polished_lines = polish_data.get("polished_text", "").splitlines()
        
        diff = difflib.HtmlDiff().make_file(original_lines, polished_lines, "Original", "Polished", context=True)
        
        # Clean up the diff HTML to make it more readable
        diff_html = re.sub(r'<table.+?>', '<table class="diff-table">', diff)
        diff_html = re.sub(r'<td.+?>', '<td>', diff_html)
        diff_html = re.sub(r'<th.+?>', '<th>', diff_html)
        
        # Add the diff HTML to the polish data
        polish_data["diff_html"] = diff_html
        
        return polish_data
        
    except Exception as e:
        logger.error(f"Error in polish_text: {str(e)}")
        # Return a basic structure in case of error
        return {
            "polished_text": text,
            "evaluation": f"Error: {str(e)}",
            "topic": "Error",
            "metrics": {
                "grammar": 0,
                "clarity": 0,
                "coherence": 0,
                "vocabulary": 0,
                "overall": 0,
                "improvement": 0
            },
            "diff_html": "<p>Error generating diff.</p>"
        }

def save_polish_data_to_json(entry_id, polish_data):
    """
    Save the polish data to a JSON file for reference.
    
    Args:
        entry_id: The ID of the journal entry
        polish_data: Dictionary containing polish data
        
    Returns:
        str: Path to the saved JSON file
    """
    import json
    import os
    from django.conf import settings
    
    # Create directory if it doesn't exist
    polish_dir = os.path.join(settings.MEDIA_ROOT, 'polish_data')
    os.makedirs(polish_dir, exist_ok=True)
    
    # Create filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"polish_{entry_id}_{timestamp}.json"
    filepath = os.path.join(polish_dir, filename)
    
    # Save the data
    with open(filepath, 'w') as f:
        json.dump(polish_data, f, indent=4)
    
    return filepath

def load_polish_data_from_json(filepath):
    """
    Load polished data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        dict: The loaded data or None if loading fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading polish data from JSON: {e}")
        return None

def get_latest_polish_data(entry_id):
    """
    Get the latest polish data for a journal entry.
    
    Args:
        entry_id: The ID of the journal entry
        
    Returns:
        dict: The latest polish data or None if no data is found
    """
    json_dir = os.path.join(settings.MEDIA_ROOT, 'polish_data')
    if not os.path.exists(json_dir):
        return None
    
    # Find all JSON files for this entry
    files = [f for f in os.listdir(json_dir) if f.startswith(f"{entry_id}_") and f.endswith('.json')]
    
    if not files:
        return None
    
    # Sort by timestamp (which is part of the filename)
    files.sort(reverse=True)
    
    # Load the latest file
    latest_file = os.path.join(json_dir, files[0])
    return load_polish_data_from_json(latest_file)

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None
