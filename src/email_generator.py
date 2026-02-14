import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EmailGenerator:
    """
    Converts theme analysis into crisp, executive-ready HTML emails.
    """
    
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
      .header {{ background: #00d09c; color: white; padding: 25px; border-radius: 8px 8px 0 0; text-align: center; }}
      .header h2 {{ margin: 0; font-size: 24px; }}
      .content {{ border: 1px solid #e0e0e0; border-top: none; padding: 30px; border-radius: 0 0 8px 8px; background: #ffffff; }}
      .section-title {{ color: #00d09c; border-bottom: 2px solid #00d09c; padding-bottom: 5px; margin-top: 30px; font-size: 18px; text-transform: uppercase; }}
      .theme-item {{ margin: 15px 0; padding: 15px; background: #f9f9f9; border-left: 5px solid #00d09c; border-radius: 4px; }}
      .theme-label {{ font-weight: bold; color: #333; }}
      .quote {{ font-style: italic; color: #555; background: #fff; padding: 10px; border: 1px dashed #ccc; margin: 10px 0; display: block; }}
      .action-list {{ padding-left: 20px; }}
      .action-item {{ margin: 8px 0; }}
      .footer {{ margin-top: 30px; font-size: 12px; color: #888; text-align: center; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
    </head>
    <body>
      <div class="header">
        <h2>[GROWW] Pulse Report</h2>
        <p>Week of {date}</p>
      </div>
      <div class="content">
        <div class="section-title">Top Sentiment Themes</div>
        {theme_html}

        <div class="section-title">Critical User Voices</div>
        {quote_html}

        <div class="section-title">Recommended Actions</div>
        <ul class="action-list">
          {action_html}
        </ul>
      </div>
      <div class="footer">
        This is an automated weekly pulse summary. For raw data, see theme_analysis.json.<br>
        &copy; {year} GROWW Product Operations
      </div>
    </body>
    </html>
    """

    @classmethod
    def generate_html(cls, themes: List[Dict[str, Any]]) -> str:
        date_str = datetime.now().strftime("%B %d, %Y")
        year_str = datetime.now().strftime("%Y")
        
        # Build Theme HTML
        theme_items = []
        for theme in themes[:3]:
            theme_items.append(f"""
            <div class="theme-item">
              <span class="theme-label">{theme['label']}</span> ({theme['review_count']} reviews)<br>
              {theme['summary']}
            </div>
            """)
        theme_html = "\n".join(theme_items)

        # Build Quote HTML
        quotes = []
        for theme in themes[:3]:
            # Take the first quote from each top theme
            if theme.get('high_signal_quotes'):
                quotes.append(f'<span class="quote">"{theme["high_signal_quotes"][0]}"</span>')
        quote_html = "\n".join(quotes)

        # Build Action HTML
        actions = []
        for theme in themes[:3]:
            if theme.get('action_ideas'):
                actions.append(f'<li class="action-item">{theme["action_ideas"][0]}</li>')
        action_html = "\n".join(actions)

        return cls.HTML_TEMPLATE.format(
            date=date_str,
            year=year_str,
            theme_html=theme_html,
            quote_html=quote_html,
            action_html=action_html
        )
