"""OAuth 1.0a (HMAC-SHA1) signing — validated against canonical vectors."""

import base64

import _common


def test_hmac_sha1_b64_known_vector():
    # Canonical HMAC-SHA1("key", "The quick brown fox jumps over the lazy dog")
    # = de7c9b85b8b78aa6bc8a7a36f70a90701c9db4d9 (hex).
    out = _common._hmac_sha1_b64("key", "The quick brown fox jumps over the lazy dog")
    assert base64.b64decode(out).hex() == "de7c9b85b8b78aa6bc8a7a36f70a90701c9db4d9"


def test_signature_base_string_twitter_example():
    # The official X/Twitter OAuth 1.0a worked example base string.
    params = {
        "status": "Hello Ladies + Gentlemen, a signed OAuth request!",
        "include_entities": "true",
        "oauth_consumer_key": "xvz1evFS4wEEPTGEFPHBog",
        "oauth_nonce": "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": "1318622958",
        "oauth_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
        "oauth_version": "1.0",
    }
    base = _common.signature_base_string(
        "POST", "https://api.twitter.com/1.1/statuses/update.json", params
    )
    expected = (
        "POST&https%3A%2F%2Fapi.twitter.com%2F1.1%2Fstatuses%2Fupdate.json"
        "&include_entities%3Dtrue%26oauth_consumer_key%3Dxvz1evFS4wEEPTGEFPHBog"
        "%26oauth_nonce%3DkYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg"
        "%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1318622958"
        "%26oauth_token%3D370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb"
        "%26oauth_version%3D1.0"
        "%26status%3DHello%2520Ladies%2520%252B%2520Gentlemen%252C%2520a%2520"
        "signed%2520OAuth%2520request%2521"
    )
    assert base == expected


def test_oauth1_header_structure_and_determinism():
    kw = dict(consumer_key="ck", consumer_secret="cs", token="tok", token_secret="ts",
              nonce="abc123", timestamp="1700000000")
    h1 = _common.oauth1_header("POST", "https://api.twitter.com/2/x", **kw)
    h2 = _common.oauth1_header("POST", "https://api.twitter.com/2/x", **kw)
    assert h1 == h2  # deterministic with fixed nonce/timestamp
    assert h1.startswith("OAuth ")
    for field in ("oauth_consumer_key", "oauth_nonce", "oauth_signature_method",
                  "oauth_timestamp", "oauth_token", "oauth_version", "oauth_signature"):
        assert field in h1
    assert 'oauth_signature_method="HMAC-SHA1"' in h1
