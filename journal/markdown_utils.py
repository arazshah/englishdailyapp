import os
import json
import frontmatter
from django.conf import settings
from datetime import datetime

def load_entry_from_markdown(file_path):
    """
    Load journal entry data from a markdown file.
    Returns a dictionary containing entry data or None if parsing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # For now, return minimal data
            return {
                'content': content,
                'title': file_path.split('/')[-1].replace('.md', '')
            }
    except Exception:
        return None

def get_markdown_directory():
    """Get the directory where markdown files are stored."""
    md_dir = os.path.join(settings.MEDIA_ROOT, 'markdown_entries')
    os.makedirs(md_dir, exist_ok=True)
    return md_dir

def save_entry_as_markdown(entry):
    """
    Save a journal entry as a markdown file with frontmatter containing metadata.
    
    Args:
        entry: JournalEntry object
    
    Returns:
        str: Path to the saved markdown file
    """
    md_dir = get_markdown_directory()
    
    # Create a filename based on entry ID and title
    safe_title = "".join([c if c.isalnum() else "_" for c in entry.title])
    filename = f"{entry.id}_{safe_title}.md"
    filepath = os.path.join(md_dir, filename)
    
    # Prepare frontmatter metadata
    metadata = {
        'id': entry.id,
        'title': entry.title,
        'date_posted': entry.date_posted.isoformat(),
        'author_id': entry.author.id,
        'is_polished': entry.is_polished,
        'topic': entry.topic or '',
        'export_date': datetime.now().isoformat()
    }
    
    # Add metrics data if available
    if entry.metrics_data:
        metadata['metrics'] = entry.metrics_data
    
    # Create the markdown content
    md_content = f"""---
{json.dumps(metadata, indent=2)}
---

# {entry.title}

## Original Content

{entry.content}

"""
    
    # Add polished content if available
    if entry.polished_content:
        md_content += f"""
## Polished Content

{entry.polished_content}
"""
    
    # Add evaluation if available
    if entry.evaluation:
        md_content += f"""
## Writing Evaluation

{entry.evaluation}
"""
    
    # Add diff HTML if available (as a code block to preserve HTML)
    if entry.diff_html:
        md_content += f"""
## Changes Highlighted

```html
{entry.diff_html}
```
"""
    
    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return filepath

def load_entry_from_markdown(filepath):
    """
    Load a journal entry from a markdown file.
    
    Args:
        filepath: Path to the markdown file
    
    Returns:
        dict: Entry data including content and metadata
    """
    try:
        # Parse the frontmatter and content
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        # Extract metadata
        metadata = post.metadata
        
        # Parse the content sections
        content = post.content
        
        # Split content into sections
        sections = content.split('## ')
        
        entry_data = {
            'id': metadata.get('id'),
            'title': metadata.get('title'),
            'date_posted': metadata.get('date_posted'),
            'author_id': metadata.get('author_id'),
            'is_polished': metadata.get('is_polished', False),
            'topic': metadata.get('topic', ''),
            'metrics': metadata.get('metrics', {}),
            'content': '',
            'polished_content': '',
            'evaluation': '',
            'diff_html': ''
        }
        
        # Process each section
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            section_title = lines[0].strip()
            section_content = '\n'.join(lines[1:]).strip()
            
            if 'Original Content' in section_title:
                entry_data['content'] = section_content
            elif 'Polished Content' in section_title:
                entry_data['polished_content'] = section_content
            elif 'Writing Evaluation' in section_title:
                entry_data['evaluation'] = section_content
            elif 'Changes Highlighted' in section_title:
                # Extract HTML from code block
                if '```html' in section_content and '```' in section_content:
                    html_content = section_content.split('```html')[1].split('```')[0].strip()
                    entry_data['diff_html'] = html_content
                else:
                    # Handle case where HTML isn't in a code block
                    entry_data['diff_html'] = section_content.strip()
        
        return entry_data
        
    except Exception as e:
        print(f"Error loading markdown file: {e}")
        return None