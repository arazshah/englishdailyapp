import openai
from django.conf import settings

# Set the API key and base URL globally
openai.api_key = settings.OPENAI_API_KEY
openai.api_base = settings.OPENAI_BASE_URL

def polish_text(text):
    """
    Polish the given text using OpenAI and detect the topic.
    
    Args:
        text (str): The journal text to polish
        
    Returns:
        tuple: (polished_text, topic)
    """
    try:
        # Polish the text
        prompt_polish = f"""
        Please polish the following journal entry. Improve grammar, clarity, and flow 
        while maintaining the original meaning and personal voice. Make it more eloquent 
        but keep it authentic:
        
        {text}
        """
        
        response_polish = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that polishes journal entries."},
                {"role": "user", "content": prompt_polish}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        polished_text = response_polish.choices[0].message.content.strip()
        
        # Detect the topic
        prompt_topic = f"""
        Based on the following text, what is the main topic?
        
        {polished_text}
        """
        
        response_topic = openai.ChatCompletion.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that detects topics."},
                {"role": "user", "content": prompt_topic}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        topic = response_topic.choices[0].message.content.strip()
        return polished_text, topic
        
    except Exception as e:
        # Log the error in production
        print(f"Error polishing text: {e}")
        return None, None 