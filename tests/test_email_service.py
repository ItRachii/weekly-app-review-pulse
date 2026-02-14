import pytest
from unittest.mock import patch, MagicMock
from src.email_service import EmailService

@patch("src.email_service.smtplib.SMTP")
def test_email_service_send_success(mock_smtp):
    """Verify that send_email calls SMTP correctly on success."""
    # Setup mock
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    # Mock environment variables
    with patch.dict("os.environ", {
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "test@test.com",
        "SMTP_PASSWORD": "password",
        "EMAIL_FROM": "sender@test.com"
    }):
        success = EmailService.send_email(
            to_email="receiver@test.com",
            subject="Test Subject",
            html_content="<h1>Test</h1>"
        )
        
        assert success is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "password")
        mock_server.sendmail.assert_called_once()

@patch("src.email_service.smtplib.SMTP")
def test_email_service_send_failure(mock_smtp):
    """Verify that send_email handles SMTP exceptions gracefully."""
    mock_server = MagicMock()
    mock_server.login.side_effect = Exception("Auth failed")
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    with patch.dict("os.environ", {
        "SMTP_USERNAME": "test@test.com",
        "SMTP_PASSWORD": "password"
    }):
        success = EmailService.send_email(
            to_email="receiver@test.com",
            subject="Test",
            html_content="<p>Test</p>"
        )
        assert success is False
