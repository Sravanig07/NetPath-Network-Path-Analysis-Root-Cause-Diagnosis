import pytest
from backend.app.security.ssrf import validate_and_parse_url, is_ip_blocked, SSRFValidationError


def test_is_ip_blocked():
    # Private and loopback IPs must be blocked
    assert is_ip_blocked("127.0.0.1") is True
    assert is_ip_blocked("10.0.0.1") is True
    assert is_ip_blocked("172.16.0.1") is True
    assert is_ip_blocked("192.168.1.1") is True
    assert is_ip_blocked("169.254.169.254") is True  # Cloud metadata
    assert is_ip_blocked("::1") is True

    # Public routable IPs must not be blocked
    assert is_ip_blocked("8.8.8.8") is False
    assert is_ip_blocked("93.184.216.34") is False
    assert is_ip_blocked("1.1.1.1") is False


def test_validate_and_parse_url_valid_public():
    scheme, host, port, path = validate_and_parse_url(
        "https://example.com/test?q=1",
        allow_private_ips=False
    )
    assert scheme == "https"
    assert host == "example.com"
    assert port == 443
    assert path == "/test?q=1"


def test_validate_and_parse_url_blocks_localhost():
    with pytest.raises(SSRFValidationError):
        validate_and_parse_url("http://127.0.0.1:8000", allow_private_ips=False, allowlisted_hosts=[])

    with pytest.raises(SSRFValidationError):
        validate_and_parse_url("http://localhost:8000", allow_private_ips=False, allowlisted_hosts=[])


def test_validate_and_parse_url_blocks_private_ip():
    with pytest.raises(SSRFValidationError):
        validate_and_parse_url("http://192.168.1.100:8080", allow_private_ips=False, allowlisted_hosts=[])

    with pytest.raises(SSRFValidationError):
        validate_and_parse_url("http://169.254.169.254/latest/meta-data", allow_private_ips=False, allowlisted_hosts=[])


def test_validate_and_parse_url_rejects_non_http_schemes():
    with pytest.raises(SSRFValidationError):
        validate_and_parse_url("ftp://example.com/file.txt", allow_private_ips=False)

    with pytest.raises(SSRFValidationError):
        validate_and_parse_url("file:///etc/passwd", allow_private_ips=False)


def test_validate_and_parse_url_allows_test_lab_when_configured():
    # When explicitly allowlisted, test lab hosts are allowed
    scheme, host, port, path = validate_and_parse_url(
        "http://test-service-a:8001/slow",
        allow_private_ips=False,
        allowlisted_hosts=["test-service-a"]
    )
    assert scheme == "http"
    assert host == "test-service-a"
    assert port == 8001
    assert path == "/slow"
