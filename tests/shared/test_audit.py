"""
Tests for shared audit logging module.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from shared.services.audit import AuditLogger


class TestAuditLogger:
    """Test audit logger functionality."""
    
    def test_init_with_service_name(self):
        """Logger should store service name."""
        logger = AuditLogger("transcribe")
        assert logger.service == "transcribe"
    
    def test_get_username_from_remote_user_header(self):
        """Should extract username from X-Remote-User header."""
        request = MagicMock()
        request.headers = {"x-remote-user": "john.doe"}
        
        username = AuditLogger.get_username(request)
        assert username == "john.doe"
    
    def test_get_username_from_forwarded_user_header(self):
        """Should extract username from X-Forwarded-User header."""
        request = MagicMock()
        request.headers = {"x-forwarded-user": "jane.doe"}
        
        username = AuditLogger.get_username(request)
        assert username == "jane.doe"
    
    def test_get_username_anonymous_fallback(self):
        """Should return anonymous when no auth headers present."""
        request = MagicMock()
        request.headers = {}
        
        username = AuditLogger.get_username(request)
        assert username == "anonymous"
    
    def test_get_ip_address_from_forwarded_for(self):
        """Should extract IP from X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        request.client = None
        
        ip = AuditLogger.get_ip_address(request)
        assert ip == "192.168.1.100"
    
    def test_get_ip_address_from_client(self):
        """Should use client IP when no forwarded header."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        ip = AuditLogger.get_ip_address(request)
        assert ip == "127.0.0.1"
    
    def test_get_ip_address_unknown_fallback(self):
        """Should return unknown when no IP available."""
        request = MagicMock()
        request.headers = {}
        request.client = None
        
        ip = AuditLogger.get_ip_address(request)
        assert ip == "unknown"
