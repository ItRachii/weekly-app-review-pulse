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
    <!--
      Groww Brand Colors:
      Groww Blue:            #5367F5
      Groww Green (Logo):    #08F6B6
      Groww Green (Primary): #00D09C
      Groww Accent Blue A:   #B1D0FB
      Groww Accent Blue B:   #E5F4FD
    -->
    <style>
      body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 0; background: #f4f4f4; }}
      .wrapper {{ background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(83,103,245,0.08); }}
      .header {{ background: linear-gradient(135deg, #5367F5, #00D09C); color: #ffffff; padding: 30px 25px; text-align: center; }}
      .header h2 {{ margin: 0 0 4px 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }}
      .header p {{ margin: 0; font-size: 14px; opacity: 0.9; }}
      .content {{ padding: 30px; }}
      .section-title {{ color: #5367F5; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #00D09C; padding-bottom: 8px; margin: 28px 0 16px 0; }}
      .theme-item {{ margin: 12px 0; padding: 16px; background: #E5F4FD; border-left: 4px solid #5367F5; border-radius: 6px; }}
      .theme-label {{ font-weight: 700; color: #5367F5; font-size: 15px; }}
      .theme-count {{ color: #00D09C; font-weight: 600; font-size: 13px; }}
      .theme-summary {{ color: #333; font-size: 14px; margin-top: 6px; }}
      .quote {{ font-style: italic; color: #5367F5; background: #E5F4FD; padding: 12px 16px; border-left: 3px solid #08F6B6; border-radius: 4px; margin: 10px 0; display: block; font-size: 14px; }}
      .action-list {{ padding-left: 20px; margin: 0; }}
      .action-item {{ margin: 10px 0; color: #333; font-size: 14px; }}
      .action-item::marker {{ color: #00D09C; }}
      .footer {{ padding: 20px 30px; font-size: 11px; color: #B1D0FB; text-align: center; border-top: 1px solid #E5F4FD; }}
      .footer a {{ color: #5367F5; text-decoration: none; }}
    </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="header">
          <h2>GROWW Pulse Report</h2>
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
              <span class="theme-label">{theme['label']}</span> <span class="theme-count">({theme['review_count']} reviews)</span>
              <div class="theme-summary">{theme['summary']}</div>
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