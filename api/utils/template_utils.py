from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime

# Initialize Jinja2 environment
template_dir = Path(__file__).parent.parent / "email_templates"
env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=select_autoescape(['html', 'xml'])
)

def get_template_env():
    """Get the Jinja2 template environment with custom filters."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'email_templates')
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Add custom filters
    def format_date(value):
        """Format a date string or datetime object."""
        if isinstance(value, str):
            # Parse ISO format string to datetime
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M')
        return value
    
    env.filters['date'] = format_date
    
    return env

def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    Render an email template with the given context.
    
    Args:
        template_name: Name of the template file (e.g., 'borrower_sign.html')
        context: Dictionary containing template variables
        
    Returns:
        str: Rendered HTML template
    """
    env = get_template_env()
    template = env.get_template(template_name)
    return template.render(**context) 