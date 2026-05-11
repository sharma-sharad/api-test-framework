from src.api_tester.ssl_config import build_verify_option


def test_build_verify_option_defaults_to_true():
    assert build_verify_option() is True


def test_build_verify_option_can_disable_ssl_verification():
    assert build_verify_option(verify_ssl=False) is False


def test_build_verify_option_uses_custom_ca_bundle_path():
    assert build_verify_option(verify_ssl=True, ca_bundle_path=" /tmp/company-ca.pem ") == "/tmp/company-ca.pem"
