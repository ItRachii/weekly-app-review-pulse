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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      /* Brand Colors */
      :root {{
        --groww-blue: #5367F5;
        --groww-green: #00D09C;
        --groww-green-bg: #E6FBF5; /* Very light green for pills */
        --groww-accent-blue: #E5F4FD;
        --text-dark: #0B0B21;
        --text-gray: #555555;
        --bg-color: #F8F9FA;
      }}
      
      body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.5; color: #0B0B21; margin: 0; padding: 0; background-color: #F8F9FA; }}
      .wrapper {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
      
      /* Mobile Optimizations */
      @media only screen and (max-width: 600px) {{
        .wrapper {{ width: 100% !important; }}
        .header {{ padding: 20px !important; }}
        .content {{ padding: 20px !important; }}
        .metric-box {{ width: 100% !important; margin-bottom: 10px !important; }}
      }}

      /* Header */
      .header {{ background: linear-gradient(135deg, #14143C, #5367F5); color: #ffffff; padding: 30px; border-bottom: 4px solid #00D09C; }}
      .header-title {{ font-size: 24px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }}
      .header-subtitle {{ font-size: 14px; opacity: 0.9; margin-top: 5px; }}

      /* Sections */
      .section {{ padding: 25px 30px; border-bottom: 1px solid #EEEEEE; }}
      .section-title {{ color: #5367F5; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 15px; display: block; }}
      
      /* Executive Snapshot */
      .snapshot-container {{ display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-top: 15px; }}
      .metric-box {{ flex: 1; min-width: 80px; background: #E5F4FD; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #B1D0FB; }}
      .metric-value {{ display: block; font-size: 20px; font-weight: 700; color: #5367F5; }}
      .metric-label {{ font-size: 11px; text-transform: uppercase; color: #555; letter-spacing: 0.5px; margin-top: 4px; display: block; }}
      .trend-up {{ color: #00D09C; font-size: 12px; font-weight: bold; }}
      .trend-down {{ color: #FF4444; font-size: 12px; font-weight: bold; }}

      /* Themes */
      .theme-card {{ background: #ffffff; border: 1px solid #EEEEEE; border-radius: 8px; padding: 16px; margin-bottom: 15px; border-left: 4px solid #5367F5; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }}
      .theme-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
      .theme-title {{ font-weight: 700; font-size: 16px; color: #0B0B21; }}
      .theme-meta {{ font-size: 12px; color: #666; font-weight: 500; }}
      .theme-badge {{ font-size: 10px; padding: 3px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; }}
      .badge-positive {{ background: #E6FBF5; color: #008F6B; }}
      .badge-negative {{ background: #FDE8E8; color: #D0021B; }}
      .badge-neutral {{ background: #F2F2F2; color: #666; }}
      .theme-body {{ font-size: 14px; color: #444; margin-bottom: 10px; line-height: 1.5; }}
      .impact-box {{ font-size: 12px; color: #5367F5; background: #F4F7FF; padding: 8px 12px; border-radius: 4px; font-weight: 500; display: inline-block; }}

      /* Quotes */
      .quote-container {{ background: #F9FAFB; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #00D09C; }}
      .quote-text {{ font-style: italic; font-size: 13px; color: #444; }}

      /* Risk Radar */
      .risk-item {{ display: flex; align-items: flex-start; margin-bottom: 12px; }}
      .risk-icon {{ color: #FF4444; font-size: 16px; margin-right: 10px; font-weight: bold; }}
      .risk-content {{ font-size: 13px; color: #333; }}

      /* Actions */
      .action-table {{ width: 100%; border-collapse: collapse; }}
      .action-row {{ border-bottom: 1px solid #F0F0F0; }}
      .action-row:last-child {{ border-bottom: none; }}
      .action-cell {{ padding: 12px 0; vertical-align: top; font-size: 13px; }}
      .priority-tag {{ background: #0B0B21; color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; }}

      /* Footer */
      .footer {{ padding: 30px; background: #F8F9FA; text-align: center; font-size: 11px; color: #888; border-top: 1px solid #EEEEEE; }}
      
    </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="header">
          <div class="header-title">Weekly Pulse</div>
          <div class="header-subtitle">{date} • Internal Executive Report</div>
        </div>

        <!-- Executive Snapshot -->
        <div class="section">
          <span class="section-title">Executive Snapshot</span>
          <div style="font-size: 16px; font-weight: 500; margin-bottom: 15px; color: #0B0B21;">
            {one_line_summary}
          </div>
          <div class="snapshot-container">
            <div class="metric-box">
              <span class="metric-value">{total_reviews}</span>
              <span class="metric-label">Reviews</span>
            </div>
            <div class="metric-box">
              <span class="metric-value">{avg_rating}</span>
              <span class="metric-label">Avg Rating</span>
            </div>
            <div class="metric-box">
              <span class="metric-value" style="color: #FF4444;">{critical_issues}</span>
              <span class="metric-label">Critical Issues</span>
            </div>
          </div>
        </div>

        <!-- Themes -->
        <div class="section">
          <span class="section-title">What Moved This Week</span>
          {themes_html}
        </div>

        <!-- Risk Radar -->
        <div class="section" style="background: #FFF5F5;">
          <span class="section-title" style="color: #D0021B; border-bottom-color: #D0021B;"><span style="font-size: 18px;">⚠</span> Product Risk Radar</span>
          {risk_radar_html}
        </div>

        <!-- User Voice -->
        <div class="section">
          <span class="section-title">User Voice (Human Signal)</span>
          {quotes_html}
        </div>

        <!-- Actions -->
        <div class="section">
          <span class="section-title">Recommended Product Actions</span>
          <table class="action-table">
            {actions_html}
          </table>
        </div>

        <div class="footer">
          <div style="font-weight: bold; color: #B1D0FB; margin-bottom: 8px;">
            Follow us yet?<br>
            Our social is a treasure box of finance content
          </div>
          <div style="margin-top: 10px; margin-bottom: 20px;">
            <!-- YouTube -->
            <a href="https://www.youtube.com/channel/UCw5TLrz3qADabwezTEcOmgQ" style="text-decoration: none; margin: 0 8px;">
              <img src="https://img.icons8.com/ios-filled/50/000000/youtube-play.png" alt="YouTube" width="24" height="24" style="vertical-align: middle;">
            </a>
            <!-- Instagram -->
            <a href="https://www.instagram.com/groww_official" style="text-decoration: none; margin: 0 8px;">
              <img src="https://img.icons8.com/ios-filled/50/000000/instagram-new.png" alt="Instagram" width="24" height="24" style="vertical-align: middle;">
            </a>
            <!-- X (Twitter) -->
            <a href="https://x.com/_groww" style="text-decoration: none; margin: 0 8px;">
              <img src="https://img.icons8.com/ios-filled/50/000000/twitter.png" alt="X" width="24" height="24" style="vertical-align: middle;">
            </a>
            <!-- Facebook -->
            <a href="https://www.facebook.com/growwapp/" style="text-decoration: none; margin: 0 8px;">
              <img src="https://img.icons8.com/ios-filled/50/000000/facebook-new.png" alt="Facebook" width="24" height="24" style="vertical-align: middle;">
            </a>
            <!-- LinkedIn -->
            <a href="https://www.linkedin.com/company/groww.in/" style="text-decoration: none; margin: 0 8px;">
              <img src="https://img.icons8.com/ios-filled/50/000000/linkedin.png" alt="LinkedIn" width="24" height="24" style="vertical-align: middle;">
            </a>
          </div>
          This is an automated weekly pulse summary. For raw data, see theme_analysis.json.<br>
          &copy; {year} GROWW Product Operations
        </div>
      </div>
    </body>
    </html>
    """

    @classmethod
    def generate_html(cls, themes: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
        date_str = datetime.now().strftime("%B %d, %Y")
        year_str = datetime.now().strftime("%Y")
        
        # 1. Executive Snapshot Logic
        summary_theme = themes[0]['label'] if themes else "No major themes"
        one_line_summary = f"User feedback dominated by <b>{summary_theme}</b> this week."

        # 2. Build Themes HTML
        theme_items = []
        for theme in themes[:3]:
            sentiment = theme.get('sentiment', 'Neutral')
            badge_class = 'badge-neutral'
            if sentiment == 'Positive': badge_class = 'badge-positive'
            elif sentiment == 'Negative': badge_class = 'badge-negative'

            theme_items.append(f"""
            <div class="theme-card">
              <div class="theme-header">
                <span class="theme-title">{theme.get('label', 'Untitled Theme')}</span>
                <span class="theme-badge {badge_class}">{sentiment}</span>
              </div>
              <div class="theme-body">
                {theme.get('summary', '')}
              </div>
              <div class="impact-box">
                💼 {theme.get('business_impact', 'Impact analysis pending')}
              </div>
            </div>
            """)
        themes_html = "\n".join(theme_items)

        # 3. Build Risk Radar HTML
        # Filter for negative themes or risks
        risk_items = []
        for theme in themes:
            if theme.get('sentiment') == 'Negative' or 'bug' in theme.get('label', '').lower() or 'crash' in theme.get('label', '').lower():
                 risk_items.append(f"""
                 <div class="risk-item">
                    <div class="risk-content">
                        <b>{theme.get('label')}</b>: {theme.get('business_impact', 'Potential churn risk')}
                    </div>
                 </div>
                 """)
        
        if not risk_items:
            risk_radar_html = "<div class='risk-content'>No critical product risks identified this week. ✅</div>"
        else:
            risk_radar_html = "\n".join(risk_items[:3])


        # 4. Build User Voice HTML
        # Collect distinct quotes
        quotes_list = []
        for theme in themes[:3]:
            if theme.get('high_signal_quotes'):
                q = theme['high_signal_quotes'][0]
                quotes_list.append(f"""
                <div class="quote-container">
                    <div class="quote-text">"{q}"</div>
                    <div style="font-size: 10px; color: #888; margin-top: 4px; text-align: right;">— Related to: {theme.get('label')}</div>
                </div>
                """)
        quotes_html = "\n".join(quotes_list)

        # 5. Build Actions HTML
        action_rows = []
        priority_map = {0: "P0", 1: "P1", 2: "P2"}
        
        idx = 0
        for theme in themes[:3]:
            if theme.get('action_ideas'):
                action = theme['action_ideas'][0]
                p_label = priority_map.get(idx, "P2")
                p_class = f"priority-{p_label.lower()}"
                
                action_rows.append(f"""
                <tr class="action-row">
                    <td class="action-cell" style="width: 40px;"><span class="priority-tag {p_class}">{p_label}</span></td>
                    <td class="action-cell"><b>{action}</b><br><span style="color: #888; font-size: 11px;">Owner: Product Ops</span></td>
                </tr>
                """)
                idx += 1
        actions_html = "\n".join(action_rows)

        return cls.HTML_TEMPLATE.format(
            date=date_str,
            year=year_str,
            one_line_summary=one_line_summary,
            total_reviews=stats.get('total_reviews', 0),
            avg_rating=f"{stats.get('avg_rating', 0.0):.1f}",
            critical_issues=stats.get('critical_issues_count', 0),
            themes_html=themes_html,
            risk_radar_html=risk_radar_html,
            quotes_html=quotes_html,
            actions_html=actions_html
        )
