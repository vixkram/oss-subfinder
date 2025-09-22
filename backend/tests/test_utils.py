from app import utils


def test_normalize_hostname_strips_wildcard():
    assert utils.normalize_hostname("*.Sub.Example.com") == "sub.example.com"


def test_normalize_hostname_rejects_invalid():
    assert utils.normalize_hostname("bad domain") is None


def test_iter_crtsh_names_splits_lines():
    source = "a.example.com\n*.B.example.com\n\n"
    assert list(utils.iter_crtsh_names(source)) == ["a.example.com", "B.example.com"]


def test_is_subdomain_positive_and_negative():
    assert utils.is_subdomain("a.b.example.com", "example.com")
    assert not utils.is_subdomain("example.net", "example.com")


def test_unique_everseen_preserves_order():
    items = ["a", "b", "a", "c"]
    assert utils.unique_everseen(items) == ["a", "b", "c"]


def test_sanitize_domain_requires_dot():
    assert utils.sanitize_domain("example.com") == "example.com"
    assert utils.sanitize_domain("localhost") is None
